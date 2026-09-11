"""Workspace management for Prompt2Product.

Per docs/01 §6 and §9:
- No module assumes os.getcwd() or absolute local paths; every path comes from Workspace.
- All paths are relative to workspace root using POSIX separators (/).
- Path traversal outside workspace root is strictly prohibited.
"""

from pathlib import Path, PurePosixPath


class PathTraversalError(Exception):
    """Raised when a path resolves outside the workspace root."""


class Workspace:
    """Represents a project workspace and provides canonical directory paths."""

    def __init__(self, root_path: Path | str) -> None:
        self._root_path = Path(root_path).resolve()

    @property
    def root_path(self) -> Path:
        """Absolute canonical path to workspace root."""
        return self._root_path

    # Standard .p2p metadata paths per docs/01 §6
    @property
    def p2p_dir(self) -> Path:
        return self._root_path / ".p2p"

    @property
    def project_spec_path(self) -> Path:
        return self.p2p_dir / "project.json"

    @property
    def routing_spec_path(self) -> Path:
        return self.p2p_dir / "routing.yaml"

    @property
    def events_path(self) -> Path:
        return self.p2p_dir / "events.jsonl"

    @property
    def state_path(self) -> Path:
        return self.p2p_dir / "state.json"

    @property
    def tasks_dir(self) -> Path:
        return self.p2p_dir / "tasks"

    @property
    def runs_dir(self) -> Path:
        return self.p2p_dir / "runs"

    @property
    def reviews_dir(self) -> Path:
        return self.p2p_dir / "reviews"

    @property
    def acr_dir(self) -> Path:
        return self.p2p_dir / "acr"

    @property
    def p2p_docs_dir(self) -> Path:
        return self.p2p_dir / "docs"

    @property
    def worktrees_dir(self) -> Path:
        return self.p2p_dir / "wt"

    @property
    def failed_worktrees_dir(self) -> Path:
        return self.p2p_dir / "wt" / "failed"

    @property
    def cache_dir(self) -> Path:
        return self.p2p_dir / "cache"

    # Standard generated project directories per docs/01 §6
    @property
    def backend_dir(self) -> Path:
        return self._root_path / "backend"

    @property
    def frontend_dir(self) -> Path:
        return self._root_path / "frontend"

    @property
    def tests_dir(self) -> Path:
        return self._root_path / "tests"

    @property
    def infra_dir(self) -> Path:
        return self._root_path / "infra"

    @property
    def github_workflows_dir(self) -> Path:
        return self._root_path / ".github" / "workflows"

    def resolve_path(self, rel_path: str | Path) -> Path:
        """Resolve a relative path against workspace root, preventing traversal."""
        path_obj = Path(rel_path)
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            resolved = (self._root_path / path_obj).resolve()

        try:
            resolved.relative_to(self._root_path)
        except ValueError as err:
            raise PathTraversalError(
                f"Path '{rel_path}' resolves outside workspace root: {resolved}"
            ) from err

        return resolved

    def relative_posix_path(self, target: Path | str) -> str:
        """Convert a path to a POSIX string relative to workspace root."""
        resolved = Path(target).resolve()
        rel = resolved.relative_to(self._root_path)
        return PurePosixPath(rel).as_posix()

    def run_dir(self, run_id: str) -> Path:
        """Path to a specific run directory."""
        return self.runs_dir / run_id

    def task_contract_path(self, task_id: str) -> Path:
        """Path to a task contract file."""
        return self.tasks_dir / f"{task_id}.json"

    def worktree_path(self, task_id: str) -> Path:
        """Path to a task's worktree."""
        return self.worktrees_dir / task_id

    def failed_worktree_path(self, task_id: str) -> Path:
        """Path to preserve a failed task's worktree."""
        return self.failed_worktrees_dir / task_id

    def ensure_directories(self) -> None:
        """Create standard workspace directories if they do not exist."""
        dirs = [
            self.p2p_dir,
            self.tasks_dir,
            self.runs_dir,
            self.reviews_dir,
            self.acr_dir,
            self.p2p_docs_dir,
            self.worktrees_dir,
            self.failed_worktrees_dir,
            self.cache_dir,
            self.backend_dir,
            self.frontend_dir,
            self.tests_dir,
            self.infra_dir,
            self.github_workflows_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
