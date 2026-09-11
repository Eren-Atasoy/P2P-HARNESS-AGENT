"""Official Exit Criterion Test for Faz 7: Milestone 2 (AUTONOMOUS PRODUCT GENERATION VERIFIED).

Per docs/08-roadmap.md §Faz 7:
'Çıkış kriteri (Milestone 2: AUTONOMOUS PRODUCT GENERATION VERIFIED):
p2p new "..." sonrası ürün çalışıyor; tüm kapılar yeşil;
.p2p/ silindiğinde proje normal repo olarak çalışmaya devam ediyor.
Tek bir prompttan production-ready ürün üretimi ilk kez bu aşamada kanıtlanır.'
"""
from pathlib import Path
import shutil
import subprocess
import sys
from typer.testing import CliRunner

from src.cli.main import app
from src.workspace.workspace import Workspace

runner = CliRunner()


def test_phase7_official_exit_criterion(tmp_path: Path):
    """
    Proves Milestone 2:
    1. Single prompt generates complete FastAPI product with Docker infra.
    2. Tests pass cleanly out of the box.
    3. Invariance: .p2p/ directory is completely removed; project continues to work
       independently as a normal repository without any P2P coupling.
    """
    workspace_dir = tmp_path / "appointment_api"
    prompt = "kimlik doğrulamalı randevu API'si"

    # Step 1: Run 'p2p new'
    result = runner.invoke(
        app,
        ["new", prompt, "--workspace", str(workspace_dir), "--autonomy", "guarded", "--approve"],
    )
    assert result.exit_code == 0, f"CLI execution failed: {result.stdout}"
    assert "Planning chain completed successfully!" in result.stdout

    ws = Workspace(workspace_dir)

    # Step 2: Verify Product Artifacts
    main_py = ws.backend_dir / "app" / "main.py"
    auth_py = ws.backend_dir / "app" / "auth.py"
    dockerfile = ws.infra_dir / "Dockerfile"
    compose_yml = ws.infra_dir / "docker-compose.yml"
    generated_test = ws.tests_dir / "test_generated_api.py"

    assert main_py.exists(), "backend/app/main.py must exist"
    assert auth_py.exists(), "backend/app/auth.py must exist"
    assert dockerfile.exists(), "infra/Dockerfile must exist"
    assert compose_yml.exists(), "infra/docker-compose.yml must exist"
    assert generated_test.exists(), "tests/test_generated_api.py must exist"

    # Verify Dockerfile is non-root (docs/06 §6)
    dockerfile_content = dockerfile.read_text(encoding="utf-8")
    assert "USER appuser" in dockerfile_content
    assert "EXPOSE 8000" in dockerfile_content

    # Step 3: Run the generated functional tests using subprocess
    test_run = subprocess.run(
        [sys.executable, "-m", "pytest", str(generated_test)],
        cwd=str(workspace_dir),
        capture_output=True,
        text=True,
    )
    assert test_run.returncode == 0, f"Generated tests failed:\n{test_run.stdout}\n{test_run.stderr}"
    assert "passed" in test_run.stdout

    # Step 4: Cardinal Rule Invariance Check (docs/01 §6)
    # Delete .p2p directory completely
    shutil.rmtree(ws.p2p_dir)
    assert not ws.p2p_dir.exists(), ".p2p directory should be deleted"

    # Re-run generated tests: Must still pass with zero coupling to .p2p
    test_run_standalone = subprocess.run(
        [sys.executable, "-m", "pytest", str(generated_test)],
        cwd=str(workspace_dir),
        capture_output=True,
        text=True,
    )
    assert test_run_standalone.returncode == 0, f"Standalone test failed after .p2p deletion:\n{test_run_standalone.stdout}"
    assert "passed" in test_run_standalone.stdout
