"""Unit tests for Workspace and canonical path handling."""

from pathlib import Path
import pytest

from src.workspace.workspace import PathTraversalError, Workspace


def test_workspace_canonical_paths(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    assert ws.root_path == tmp_path.resolve()
    assert ws.p2p_dir == tmp_path / ".p2p"
    assert ws.tasks_dir == tmp_path / ".p2p" / "tasks"
    assert ws.runs_dir == tmp_path / ".p2p" / "runs"
    assert ws.backend_dir == tmp_path / "backend"
    assert ws.frontend_dir == tmp_path / "frontend"


def test_workspace_resolve_path_safe(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    resolved = ws.resolve_path("backend/api/main.py")
    assert resolved == tmp_path / "backend" / "api" / "main.py"


def test_workspace_path_traversal_prevention(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(PathTraversalError):
        ws.resolve_path("../outside.txt")

    with pytest.raises(PathTraversalError):
        ws.resolve_path("../../etc/passwd")


def test_workspace_relative_posix_path(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    target = tmp_path / "backend" / "api" / "endpoints.py"
    posix_str = ws.relative_posix_path(target)
    assert posix_str == "backend/api/endpoints.py"
    assert "\\" not in posix_str


def test_workspace_ensure_directories(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    assert ws.p2p_dir.is_dir()
    assert ws.tasks_dir.is_dir()
    assert ws.runs_dir.is_dir()
    assert ws.worktrees_dir.is_dir()
    assert ws.backend_dir.is_dir()
    assert ws.frontend_dir.is_dir()
    assert ws.tests_dir.is_dir()
