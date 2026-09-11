"""Unit tests for WorkspaceBootstrap."""

from datetime import datetime, timezone
from pathlib import Path
import uuid

from src.models.enums import GateStatus
from src.models.project import ProjectSpec
from src.workspace.bootstrap import WorkspaceBootstrap
from src.workspace.git import GitManager
from src.workspace.workspace import Workspace


def test_bootstrap_scaffold_and_git(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    git = GitManager(ws)
    bootstrap = WorkspaceBootstrap(ws, git)

    spec = ProjectSpec(
        id=uuid.uuid4(),
        name="test-product",
        prompt="Build a fast api product",
        created_at=datetime.now(timezone.utc),
        p2p_version="0.1.0",
        stack={"backend": {"language": "python", "framework": "fastapi"}},
        decisions=[],
        targets=["api"],
    )

    bootstrap.scaffold(spec)
    assert (tmp_path / ".gitignore").exists()
    assert ws.project_spec_path.exists()

    caches = bootstrap.setup_cache()
    assert caches["pip"].is_dir()
    assert caches["npm"].is_dir()
    assert caches["venv"].is_dir()

    bootstrap.init_git()
    assert (tmp_path / ".git").is_dir()


def test_bootstrap_smoke_check(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    git = GitManager(ws)
    bootstrap = WorkspaceBootstrap(ws, git)

    # Before init, smoke check reports ERROR
    smoke_pre = bootstrap.run_smoke_check()
    assert smoke_pre.status == GateStatus.ERROR

    # After scaffold and git init, smoke check passes
    bootstrap.scaffold()
    bootstrap.init_git()

    smoke_post = bootstrap.run_smoke_check()
    assert smoke_post.status == GateStatus.PASS
