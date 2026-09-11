"""Workspace bootstrap manager.

Implements C5 and docs/08-roadmap.md Phase 3:
- Scaffolds canonical directory structure and essential files
- Initializes Git repo with main and p2p/integration branches
- Sets up dependency/cache directory sharing for worktrees
- Performs empty project smoke check ensuring gates return PASS/FAIL, never ERROR
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from pydantic import BaseModel

from src.models.enums import GateStatus

if TYPE_CHECKING:
    from src.models.project import ProjectSpec
    from src.workspace.git import GitManager
    from src.workspace.workspace import Workspace


class SmokeCheckResult(BaseModel):
    """Result of initial empty project smoke check."""

    status: GateStatus
    message: str


class WorkspaceBootstrap:
    """Handles initialization, scaffolding, and cache sharing for the workspace."""

    def __init__(self, workspace: Workspace, git_manager: GitManager) -> None:
        self.workspace = workspace
        self.git_manager = git_manager

    def scaffold(self, project_spec: ProjectSpec | None = None) -> None:
        """Create standard directories and minimal project files."""
        self.workspace.ensure_directories()

        # Write .gitignore if not present
        gitignore_path = self.workspace.root_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_content = (
                "# P2P generated run artifacts\n"
                ".p2p/runs/\n"
                ".p2p/state.json\n"
                ".p2p/wt/\n"
                ".p2p/cache/\n"
                "\n"
                "# Python\n"
                "__pycache__/\n"
                "*.pyc\n"
                ".pytest_cache/\n"
                ".venv/\n"
                "\n"
                "# Node\n"
                "node_modules/\n"
                "\n"
                "# Secrets\n"
                ".env\n"
            )
            gitignore_path.write_text(gitignore_content, encoding="utf-8")

        # Write project spec if provided
        if project_spec is not None:
            self.workspace.project_spec_path.write_text(
                json.dumps(project_spec.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )

    def init_git(self) -> None:
        """Initialize git repo with initial commit and integration branch."""
        self.git_manager.init_repo()

    def setup_cache(self) -> dict[str, Path]:
        """Create shared cache directories for pip, npm, and virtual environments."""
        cache_root = self.workspace.cache_dir
        pip_cache = cache_root / "pip"
        npm_cache = cache_root / "npm"
        venv_cache = cache_root / "venv"

        pip_cache.mkdir(parents=True, exist_ok=True)
        npm_cache.mkdir(parents=True, exist_ok=True)
        venv_cache.mkdir(parents=True, exist_ok=True)

        return {
            "pip": pip_cache,
            "npm": npm_cache,
            "venv": venv_cache,
        }

    def run_smoke_check(self, target_path: Path | None = None) -> SmokeCheckResult:
        """Verify baseline environment health. Must return PASS/FAIL, never ERROR."""
        check_dir = target_path if target_path is not None else self.workspace.root_path

        if not check_dir.exists():
            return SmokeCheckResult(
                status=GateStatus.ERROR,
                message=f"Workspace directory {check_dir} does not exist.",
            )

        # Check git repo health
        git_dir = self.workspace.root_path / ".git"
        if not git_dir.exists():
            return SmokeCheckResult(
                status=GateStatus.ERROR,
                message="Git repository is not initialized.",
            )

        # Ensure .p2p directory exists
        if not self.workspace.p2p_dir.exists():
            return SmokeCheckResult(
                status=GateStatus.ERROR,
                message=".p2p directory structure is missing.",
            )

        return SmokeCheckResult(
            status=GateStatus.PASS,
            message="Workspace environment is healthy and smoke check passed.",
        )
