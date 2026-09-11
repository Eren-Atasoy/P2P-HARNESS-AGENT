"""Unit tests for PythonCliBlueprint scaffolding and testing."""
from pathlib import Path
from src.blueprints.python_cli import PythonCliBlueprint
from src.models.enums import TargetType
from src.models.project import ProjectSpec
from src.workspace.workspace import Workspace


def test_python_cli_blueprint_generation(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    spec = ProjectSpec(
        name="log-analyzer",
        prompt="Fast log analyzer CLI tool",
        targets=[TargetType.CLI],
    )

    blueprint = PythonCliBlueprint()
    assert blueprint.name == "python_cli"
    assert TargetType.CLI in blueprint.targets

    scaffold_files = blueprint.generate_scaffold(ws, spec)
    infra_files = blueprint.generate_infra(ws, spec)
    test_files = blueprint.generate_tests(ws, spec)

    assert len(scaffold_files) > 0
    assert len(infra_files) > 0
    assert len(test_files) > 0

    # Verify critical files created
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / "src" / "cli" / "main.py").exists()
    assert (tmp_path / "src" / "core" / "engine.py").exists()
    assert (tmp_path / "Dockerfile").exists()
    assert (tmp_path / "tests" / "test_cli.py").exists()

    # Check content of pyproject.toml
    pyproject_text = (tmp_path / "pyproject.toml").read_text()
    assert "log-analyzer" in pyproject_text
    assert "typer" in pyproject_text
    assert "rich" in pyproject_text

    # Check content of CLI entrypoint
    main_py_text = (tmp_path / "src" / "cli" / "main.py").read_text()
    assert "def run" in main_py_text
    assert "def version" in main_py_text
    assert "def status" in main_py_text
