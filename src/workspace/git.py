"""Git and Worktree manager for Prompt2Product.

Implements ADR-006 and docs/07-git-ci.md:
- Deterministic branch model: main, p2p/integration, p2p/task/<id>
- Worktree lifecycle: add, commit, merge, remove, and preserve failed worktrees
- Strict audit commit format (Acceptance criteria, Gates, Runtime, Attempt)
- Merge conflict detection and non-ff merge order
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.result import AgentResult, GateResult
    from src.models.task import TaskContract
    from src.workspace.workspace import Workspace


class GitError(Exception):
    """Base exception for git operations."""


class MergeConflictError(GitError):
    """Raised when a merge conflict occurs."""


class GitManager:
    """Manages git repository, worktrees, branches, and merges."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def _run_git(
        self,
        args: list[str],
        cwd: Path | str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Execute a git command with timeout and safe environment."""
        target_cwd = Path(cwd) if cwd is not None else self.workspace.root_path
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["PYTHONIOENCODING"] = "utf-8"
        env["LC_ALL"] = "C.UTF-8"

        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(target_cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=60,
                check=False,
            )
        except Exception as err:
            raise GitError(f"Failed to execute git {' '.join(args)}: {err}") from err

        if check and result.returncode != 0:
            cmd_str = " ".join(args)
            err_msg = (result.stderr or result.stdout or "").strip()
            raise GitError(f"Git command failed (code {result.returncode}): git {cmd_str}\n{err_msg}")

        return result

    def init_repo(
        self,
        user_name: str = "Prompt2Product",
        user_email: str = "p2p@local",
        initial_branch: str = "main",
    ) -> None:
        """Initialize git repo, configure identity, and setup integration branch."""
        self._run_git(["init", "-b", initial_branch])
        self._run_git(["config", "user.name", user_name])
        self._run_git(["config", "user.email", user_email])

        # Create default .gitignore ignoring worktrees, runs, and cache per docs/01 §5
        gitignore_path = self.workspace.root_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(
                ".p2p/wt/\n.p2p/runs/\n.p2p/state.json\n.p2p/cache/\n",
                encoding="utf-8",
            )
        self._run_git(["add", ".gitignore"])
        self._run_git(["commit", "-m", "chore: initial project root with gitignore"])

        # Create and checkout p2p/integration branch
        self._run_git(["branch", "p2p/integration"])
        self._run_git(["checkout", "p2p/integration"])

    def create_worktree(
        self,
        task_id: str,
        base_branch: str = "p2p/integration",
    ) -> Path:
        """Create an isolated worktree for a task on branch p2p/task/<id>."""
        branch_name = f"p2p/task/{task_id}"
        wt_path = self.workspace.worktree_path(task_id)

        if wt_path.exists():
            raise GitError(f"Worktree path already exists: {wt_path}")

        wt_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_git(["worktree", "add", "-b", branch_name, str(wt_path), base_branch])
        return wt_path

    def remove_worktree(self, task_id: str, failed: bool = False) -> None:
        """Remove worktree; preserve to .p2p/wt/failed/<id> if failed."""
        wt_path = self.workspace.worktree_path(task_id)
        branch_name = f"p2p/task/{task_id}"

        if not wt_path.exists():
            return

        if failed:
            failed_path = self.workspace.failed_worktree_path(task_id)
            failed_path.parent.mkdir(parents=True, exist_ok=True)
            if failed_path.exists():
                shutil.rmtree(failed_path, ignore_errors=True)
            shutil.copytree(wt_path, failed_path)

        # Force removal of the git worktree
        self._run_git(["worktree", "remove", "--force", str(wt_path)])

        # If succeeded, delete the task branch
        if not failed:
            self._run_git(["branch", "-D", branch_name], check=False)

    def get_status_porcelain(self, worktree_path: Path) -> list[tuple[str, str]]:
        """Return list of (status_code, relative_file_path) in worktree."""
        proc = self._run_git(["status", "--porcelain", "-uall"], cwd=worktree_path)
        items: list[tuple[str, str]] = []
        for line in proc.stdout.splitlines():
            line = line.rstrip()
            if not line:
                continue
            status = line[:2].strip()
            path_str = line[3:].strip()
            # Handle quoted paths or renames
            if " -> " in path_str:
                path_str = path_str.split(" -> ")[-1]
            path_str = path_str.strip('"')
            items.append((status, path_str))
        return items

    def reset_hard(self, worktree_path: Path) -> None:
        """Hard reset and clean untracked files in worktree."""
        self._run_git(["reset", "--hard", "HEAD"], cwd=worktree_path)
        self._run_git(["clean", "-fd"], cwd=worktree_path)

    def commit_task(
        self,
        worktree_path: Path,
        task: TaskContract,
        result: AgentResult,
        gates: list[GateResult] | None = None,
        runtime_name: str = "agent",
        attempt: int = 1,
    ) -> str:
        """Generate audit commit for task per docs/07 §3."""
        # Stage changes
        self._run_git(["add", "."], cwd=worktree_path)

        # Build commit message
        # Format: <type>(<task-id>): <summary>
        prefix = task.id.split("-")[0].lower()
        if prefix not in {"feat", "fix", "docs", "test", "chore", "refactor"}:
            prefix = "feat"

        summary = result.summary.strip().split("\n")[0] if result.summary else task.title
        first_line = f"{prefix}({task.id}): {summary}"

        # Intent 1-3 sentences
        intent_line = task.intent.strip()

        # Acceptance criteria
        ac_lines: list[str] = ["Acceptance:"]
        addressed_set = set(result.criteria_addressed)
        for ac in task.acceptance_criteria:
            status_mark = "✓" if ac.id in addressed_set else "✗"
            ref_info = f" {ac.test_ref}" if ac.test_ref else f" {ac.statement}"
            ac_lines.append(f"  - {ac.id} {status_mark}{ref_info}")

        # Gates
        gates_str = ""
        if gates:
            gate_parts = [f"{g.gate} {'✓' if g.status.value == 'PASS' else '✗'}" for g in gates]
            gates_str = f"Gates: {' '.join(gate_parts)}"
        else:
            gates_str = "Gates: unverified"

        runtime_line = f"Runtime: {runtime_name}  Attempt: {attempt}"

        commit_msg = f"{first_line}\n\n{intent_line}\n\n" + "\n".join(ac_lines) + f"\n\n{gates_str}\n{runtime_line}"

        # Write commit message to temporary file to avoid shell encoding loss on Windows
        msg_file = worktree_path / ".git_commit_msg.tmp"
        try:
            msg_file.write_text(commit_msg, encoding="utf-8")
            self._run_git(["commit", "-F", str(msg_file)], cwd=worktree_path)
        finally:
            if msg_file.exists():
                msg_file.unlink(missing_ok=True)

        proc = self._run_git(["rev-parse", "HEAD"], cwd=worktree_path)
        return proc.stdout.strip()

    def merge_task(
        self,
        task_id: str,
        target_branch: str = "p2p/integration",
    ) -> str:
        """Merge task branch into target_branch with --no-ff."""
        branch_name = f"p2p/task/{task_id}"

        # Checkout integration branch in main workspace
        self._run_git(["checkout", target_branch])

        merge_msg = f"merge({task_id}): merge {branch_name} into {target_branch}"
        merge_proc = self._run_git(
            ["merge", "--no-ff", branch_name, "-m", merge_msg],
            check=False,
        )

        if merge_proc.returncode != 0:
            # Abort merge to keep integration clean
            self._run_git(["merge", "--abort"], check=False)
            raise MergeConflictError(
                f"Merge conflict detected when merging {branch_name} into {target_branch}:\n{merge_proc.stderr or merge_proc.stdout}"
            )

        proc = self._run_git(["rev-parse", "HEAD"])
        return proc.stdout.strip()

    def revert_merge(
        self,
        commit_hash: str,
        target_branch: str = "p2p/integration",
    ) -> str:
        """Revert a merge commit preserving history (git revert -m 1)."""
        self._run_git(["checkout", target_branch])
        self._run_git(["revert", "-m", "1", commit_hash, "--no-edit"])
        proc = self._run_git(["rev-parse", "HEAD"])
        return proc.stdout.strip()
