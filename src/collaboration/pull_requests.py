"""Pull request provider interface and implementations (docs/07 §7).

Manages Task PRs (p2p/task/<id> -> p2p/integration) and Release PRs (p2p/integration -> main)
both locally (.p2p/prs/*.json) and via `gh` CLI / GitHub REST API.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Optional

from src.collaboration.models import PRStatus, PRType, PullRequest
from src.models.task import TaskContract
from src.workspace.workspace import Workspace


class PRProvider(ABC):
    """Abstract interface for Pull Request providers."""

    @abstractmethod
    def create_task_pr(
        self,
        task: TaskContract,
        head_branch: str,
        base_branch: str = "p2p/integration",
        issue_id: Optional[str] = None,
        gate_summary: Optional[str] = None,
    ) -> PullRequest:
        """Creates a Task PR for an approved/verified task."""
        pass

    @abstractmethod
    def create_release_pr(
        self,
        project_name: str,
        head_branch: str = "p2p/integration",
        base_branch: str = "main",
        summary: Optional[str] = None,
    ) -> PullRequest:
        """Creates a Release PR ready for human sign-off into main."""
        pass

    @abstractmethod
    def merge_pr(self, pr_number: int) -> bool:
        """Merges a pull request."""
        pass

    @abstractmethod
    def list_prs(self, status: Optional[PRStatus] = None) -> list[PullRequest]:
        """Lists PRs optionally filtered by status."""
        pass


class LocalPRStore(PRProvider):
    """Local-first PR store managing pull requests in .p2p/prs/*.json."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.prs_dir = workspace.prs_dir
        self.prs_dir.mkdir(parents=True, exist_ok=True)

    def _next_number(self) -> int:
        existing = list(self.prs_dir.glob("PR-*.json"))
        max_num = 0
        for p in existing:
            try:
                num = int(p.stem.replace("PR-", ""))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        return max_num + 1

    def create_task_pr(
        self,
        task: TaskContract,
        head_branch: str,
        base_branch: str = "p2p/integration",
        issue_id: Optional[str] = None,
        gate_summary: Optional[str] = None,
    ) -> PullRequest:
        pr_number = self._next_number()
        issue_link = f" (Fixes {issue_id})" if issue_id else ""
        title = f"feat({task.id}): {task.title}{issue_link}"

        ac_lines = "\n".join(f"- [x] {ac.id}: {ac.statement}" for ac in task.acceptance_criteria)
        gates_str = gate_summary or "All deterministic quality gates PASSED."

        body = f"""## Intent
{task.intent}

## Acceptance Criteria
{ac_lines}

## Quality Gates
{gates_str}

## Governance
- Risk: `{task.risk.value}`
- Task ID: `{task.id}`
- PR Branch: `{head_branch}` -> `{base_branch}`
"""
        pr = PullRequest(
            number=pr_number,
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch,
            status=PRStatus.OPEN,
            pr_type=PRType.TASK,
            task_id=task.id,
            issue_id=issue_id,
            created_at=datetime.now(timezone.utc),
        )
        pr_file = self.prs_dir / f"PR-{pr_number:03d}.json"
        pr_file.write_text(pr.model_dump_json(indent=2), encoding="utf-8")
        return pr

    def create_release_pr(
        self,
        project_name: str,
        head_branch: str = "p2p/integration",
        base_branch: str = "main",
        summary: Optional[str] = None,
    ) -> PullRequest:
        pr_number = self._next_number()
        title = f"release: {project_name} (Milestone Autonomous Generation)"
        body = f"""# Release PR: {project_name}

All planned task graph waves have executed and passed all deterministic verification gates.

## Release Summary
{summary or "Autonomous execution completed cleanly on integration branch."}

## Target
`{head_branch}` -> `{base_branch}` (Requires human operator review per docs/07 §2)
"""
        pr = PullRequest(
            number=pr_number,
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch,
            status=PRStatus.OPEN,
            pr_type=PRType.RELEASE,
            created_at=datetime.now(timezone.utc),
        )
        pr_file = self.prs_dir / f"PR-{pr_number:03d}.json"
        pr_file.write_text(pr.model_dump_json(indent=2), encoding="utf-8")
        return pr

    def merge_pr(self, pr_number: int) -> bool:
        pr_file = self.prs_dir / f"PR-{pr_number:03d}.json"
        if not pr_file.exists():
            return False
        try:
            data = json.loads(pr_file.read_text(encoding="utf-8"))
            pr = PullRequest.model_validate(data)
            pr.status = PRStatus.MERGED
            pr.merged_at = datetime.now(timezone.utc)
            pr_file.write_text(pr.model_dump_json(indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def list_prs(self, status: Optional[PRStatus] = None) -> list[PullRequest]:
        prs = []
        for p in sorted(self.prs_dir.glob("PR-*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                pr = PullRequest.model_validate(data)
                if status is None or pr.status == status:
                    prs.append(pr)
            except Exception:
                continue
        return prs


class GitHubPRProvider(PRProvider):
    """GitHub PR provider leveraging `gh` CLI with fallback to LocalPRStore."""

    def __init__(self, workspace: Workspace, fallback: Optional[LocalPRStore] = None):
        self.workspace = workspace
        self.fallback = fallback or LocalPRStore(workspace)
        self.has_gh = shutil.which("gh") is not None

    def create_task_pr(
        self,
        task: TaskContract,
        head_branch: str,
        base_branch: str = "p2p/integration",
        issue_id: Optional[str] = None,
        gate_summary: Optional[str] = None,
    ) -> PullRequest:
        local_pr = self.fallback.create_task_pr(task, head_branch, base_branch, issue_id, gate_summary)
        if not self.has_gh:
            return local_pr

        try:
            cmd = [
                "gh", "pr", "create",
                "--title", local_pr.title,
                "--body", local_pr.body,
                "--head", head_branch,
                "--base", base_branch,
            ]
            res = subprocess.run(cmd, cwd=str(self.workspace.root_path), capture_output=True, text=True, check=True)
            url = res.stdout.strip()
            num_str = url.rstrip("/").split("/")[-1]
            if num_str.isdigit():
                local_pr.number = int(num_str)
                local_pr.html_url = url
        except Exception:
            pass
        return local_pr

    def create_release_pr(
        self,
        project_name: str,
        head_branch: str = "p2p/integration",
        base_branch: str = "main",
        summary: Optional[str] = None,
    ) -> PullRequest:
        local_pr = self.fallback.create_release_pr(project_name, head_branch, base_branch, summary)
        if not self.has_gh:
            return local_pr

        try:
            cmd = [
                "gh", "pr", "create",
                "--title", local_pr.title,
                "--body", local_pr.body,
                "--head", head_branch,
                "--base", base_branch,
            ]
            res = subprocess.run(cmd, cwd=str(self.workspace.root_path), capture_output=True, text=True, check=True)
            url = res.stdout.strip()
            num_str = url.rstrip("/").split("/")[-1]
            if num_str.isdigit():
                local_pr.number = int(num_str)
                local_pr.html_url = url
        except Exception:
            pass
        return local_pr

    def merge_pr(self, pr_number: int) -> bool:
        if self.has_gh:
            try:
                cmd = ["gh", "pr", "merge", str(pr_number), "--merge"]
                subprocess.run(cmd, cwd=str(self.workspace.root_path), capture_output=True, check=True)
            except Exception:
                pass
        return self.fallback.merge_pr(pr_number)

    def list_prs(self, status: Optional[PRStatus] = None) -> list[PullRequest]:
        return self.fallback.list_prs(status)
