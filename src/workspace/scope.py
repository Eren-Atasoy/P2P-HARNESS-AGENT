"""Scope validation for task worktrees.

Implements docs/02 §2, §3 and docs/06 §6:
- git status --porcelain verification
- allowed_paths vs forbidden_paths (forbidden always overrides allowed)
- result_path and acr_path exemptions
- Detection of undeclared file changes
- Automatic rollback of unauthorized changes
"""

from __future__ import annotations

import fnmatch
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.models.result import AgentResult
    from src.models.task import TaskContract
    from src.workspace.git import GitManager


def matches_glob(path_str: str, pattern: str) -> bool:
    """Check if a POSIX relative path matches a glob pattern, supporting **."""
    p = path_str.replace("\\", "/").lstrip("/")
    pat = pattern.replace("\\", "/").lstrip("/")

    # Handle recursive folder globs like 'backend/api/**' or '.p2p/**'
    if pat.endswith("/**"):
        base = pat[:-3]
        return p == base or p.startswith(base + "/")

    # Handle single folder globs like 'backend/*'
    if pat.endswith("/*"):
        base = pat[:-2]
        if not p.startswith(base + "/"):
            return False
        remainder = p[len(base) + 1 :]
        return "/" not in remainder

    # Exact or fnmatch / pathlib match
    return fnmatch.fnmatch(p, pat) or PurePosixPath(p).match(pat)


class ScopeValidationResult(BaseModel):
    """Result of scope validation on a worktree."""

    is_valid: bool
    violations: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    unauthorized_files: list[str] = Field(default_factory=list)
    undeclared_files: list[str] = Field(default_factory=list)


class ScopeValidator:
    """Validates files modified in a task worktree against task contract scope."""

    def __init__(self, git_manager: GitManager) -> None:
        self.git_manager = git_manager

    def validate_scope(
        self,
        worktree_path: Path,
        contract: TaskContract,
        agent_result: AgentResult | None = None,
    ) -> ScopeValidationResult:
        """Validate worktree modifications against contract and agent result."""
        status_items = self.git_manager.get_status_porcelain(worktree_path)
        modified_files = [path for _, path in status_items]

        violations: list[str] = []
        unauthorized_files: list[str] = []
        undeclared_files: list[str] = []

        # Exempt paths: result_path and acr_path (docs/02 §2)
        exempt_targets: list[str] = []
        if contract.result_path:
            exempt_targets.append(contract.result_path.replace("\\", "/").lstrip("/"))
        if contract.acr_path:
            exempt_targets.append(contract.acr_path.replace("\\", "/").lstrip("/"))

        def is_exempt(p: str) -> bool:
            for ex in exempt_targets:
                clean_ex = ex.rstrip("/")
                if p == clean_ex or p.startswith(clean_ex + "/"):
                    return True
                if matches_glob(p, ex) or matches_glob(p, f"{clean_ex}/**"):
                    return True
            return False

        for file_path in modified_files:
            posix_path = file_path.replace("\\", "/").lstrip("/")

            # Skip directory entries if any appear
            if posix_path.endswith("/"):
                continue

            # Check if exempted (result_path / acr_path)
            if is_exempt(posix_path):
                continue

            # 1. Check forbidden paths (forbidden overrides allowed per docs/02 §2)
            is_forbidden = any(
                matches_glob(posix_path, pattern) for pattern in contract.forbidden_paths
            )
            if is_forbidden:
                violations.append(
                    f"File '{posix_path}' matches forbidden_paths rule."
                )
                unauthorized_files.append(posix_path)
                continue

            # 2. Check allowed paths
            is_allowed = any(
                matches_glob(posix_path, pattern) for pattern in contract.allowed_paths
            )
            if not is_allowed:
                violations.append(
                    f"File '{posix_path}' is outside allowed_paths."
                )
                unauthorized_files.append(posix_path)

        # 3. Check declared files vs git status (docs/02 §3)
        if agent_result is not None:
            declared_set = {
                p.replace("\\", "/").lstrip("/") for p in agent_result.files_changed
            }
            # Compare non-exempt modified files
            non_exempt_modified = [
                f.replace("\\", "/").lstrip("/")
                for f in modified_files
                if not f.endswith("/") and not is_exempt(f.replace("\\", "/").lstrip("/"))
            ]

            for actual_file in non_exempt_modified:
                if actual_file not in declared_set:
                    violations.append(
                        f"Undeclared modification: '{actual_file}' changed in git but omitted from files_changed."
                    )
                    undeclared_files.append(actual_file)

        is_valid = len(violations) == 0
        return ScopeValidationResult(
            is_valid=is_valid,
            violations=violations,
            files_modified=modified_files,
            unauthorized_files=unauthorized_files,
            undeclared_files=undeclared_files,
        )

    def rollback_unauthorized_changes(self, worktree_path: Path) -> None:
        """Discard unauthorized changes and restore worktree to HEAD."""
        self.git_manager.reset_hard(worktree_path)
