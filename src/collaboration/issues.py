"""IssueProvider interface and implementations (docs/07 §7).

Provides LocalIssueStore for local-first execution and GitHubIssueProvider
for remote team synchronization via `gh` CLI or REST API.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Optional

from src.collaboration.models import Issue, IssueSeverity, IssueStatus
from src.workspace.workspace import Workspace


class IssueProvider(ABC):
    """Abstract interface for issue tracking providers."""

    @abstractmethod
    def create_issue(
        self,
        title: str,
        body: str,
        severity: IssueSeverity = IssueSeverity.HIGH,
        labels: Optional[list[str]] = None,
        task_id: Optional[str] = None,
    ) -> Issue:
        """Creates a new issue."""
        pass

    @abstractmethod
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Retrieves an issue by ID."""
        pass

    @abstractmethod
    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        """Closes an existing issue."""
        pass

    @abstractmethod
    def list_issues(self, status: Optional[IssueStatus] = None) -> list[Issue]:
        """Lists issues optionally filtered by status."""
        pass


class LocalIssueStore(IssueProvider):
    """Local-first issue store storing issues under .p2p/issues/*.json."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.issues_dir = workspace.issues_dir
        self.issues_dir.mkdir(parents=True, exist_ok=True)

    def _next_id(self) -> str:
        existing = list(self.issues_dir.glob("ISSUE-*.json"))
        max_num = 0
        for p in existing:
            try:
                num = int(p.stem.replace("ISSUE-", ""))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        return f"ISSUE-{max_num + 1:03d}"

    def create_issue(
        self,
        title: str,
        body: str,
        severity: IssueSeverity = IssueSeverity.HIGH,
        labels: Optional[list[str]] = None,
        task_id: Optional[str] = None,
    ) -> Issue:
        issue_id = self._next_id()
        issue = Issue(
            id=issue_id,
            title=title,
            body=body,
            severity=severity,
            labels=labels or ["p2p:bug", f"priority:{severity.value.lower()}"],
            status=IssueStatus.OPEN,
            task_id=task_id,
            created_at=datetime.now(timezone.utc),
        )
        issue_file = self.issues_dir / f"{issue_id}.json"
        issue_file.write_text(issue.model_dump_json(indent=2), encoding="utf-8")
        return issue

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        issue_file = self.issues_dir / f"{issue_id}.json"
        if not issue_file.exists():
            return None
        try:
            data = json.loads(issue_file.read_text(encoding="utf-8"))
            return Issue.model_validate(data)
        except Exception:
            return None

    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        issue = self.get_issue(issue_id)
        if not issue:
            return False
        issue.status = IssueStatus.CLOSED
        issue.closed_at = datetime.now(timezone.utc)
        if comment:
            issue.body += f"\n\n**Closed with resolution:**\n{comment}"
        issue_file = self.issues_dir / f"{issue_id}.json"
        issue_file.write_text(issue.model_dump_json(indent=2), encoding="utf-8")
        return True

    def list_issues(self, status: Optional[IssueStatus] = None) -> list[Issue]:
        issues = []
        for p in sorted(self.issues_dir.glob("ISSUE-*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                iss = Issue.model_validate(data)
                if status is None or iss.status == status:
                    issues.append(iss)
            except Exception:
                continue
        return issues


class GitHubIssueProvider(IssueProvider):
    """GitHub issue provider leveraging `gh` CLI with graceful fallback to LocalIssueStore."""

    def __init__(self, workspace: Workspace, fallback: Optional[LocalIssueStore] = None):
        self.workspace = workspace
        self.fallback = fallback or LocalIssueStore(workspace)
        self.has_gh = shutil.which("gh") is not None

    def create_issue(
        self,
        title: str,
        body: str,
        severity: IssueSeverity = IssueSeverity.HIGH,
        labels: Optional[list[str]] = None,
        task_id: Optional[str] = None,
    ) -> Issue:
        all_labels = labels or ["p2p:bug", f"priority:{severity.value.lower()}"]
        if not self.has_gh:
            return self.fallback.create_issue(title, body, severity, all_labels, task_id)

        try:
            label_args = []
            for lbl in all_labels:
                label_args.extend(["--label", lbl])

            cmd = ["gh", "issue", "create", "--title", title, "--body", body] + label_args
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace.root_path),
                capture_output=True,
                text=True,
                check=True,
            )
            # gh output format: https://github.com/owner/repo/issues/42
            url = res.stdout.strip()
            issue_num = url.rstrip("/").split("/")[-1]
            issue_id = f"#{issue_num}"

            issue = Issue(
                id=issue_id,
                title=title,
                body=body,
                severity=severity,
                labels=all_labels,
                status=IssueStatus.OPEN,
                task_id=task_id,
                html_url=url,
            )
            # Also mirror locally for offline cache
            local_copy = self.fallback.create_issue(title, body, severity, all_labels, task_id)
            issue.id = local_copy.id if not issue_num.isdigit() else issue_id
            return issue
        except Exception:
            # Fallback to local store
            return self.fallback.create_issue(title, body, severity, all_labels, task_id)

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        return self.fallback.get_issue(issue_id)

    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        if self.has_gh and issue_id.startswith("#"):
            try:
                clean_num = issue_id.lstrip("#")
                cmd = ["gh", "issue", "close", clean_num]
                if comment:
                    cmd.extend(["--comment", comment])
                subprocess.run(cmd, cwd=str(self.workspace.root_path), capture_output=True, check=True)
            except Exception:
                pass
        return self.fallback.close_issue(issue_id, comment)

    def list_issues(self, status: Optional[IssueStatus] = None) -> list[Issue]:
        return self.fallback.list_issues(status)
