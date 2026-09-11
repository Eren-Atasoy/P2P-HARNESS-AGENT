"""Unit tests for LocalIssueStore and GitHubIssueProvider (Faz 6.5)."""
import pytest
from src.collaboration.issues import GitHubIssueProvider, LocalIssueStore
from src.collaboration.models import Issue, IssueSeverity, IssueStatus
from src.workspace.workspace import Workspace


def test_local_issue_store_crud(tmp_path):
    ws = Workspace(tmp_path)
    store = LocalIssueStore(ws)

    # 1. Create Issue
    issue_1 = store.create_issue(
        title="Token rotation missing in auth service",
        body="Tokens never expire and cannot be refreshed.",
        severity=IssueSeverity.HIGH,
        task_id="AUTH-001",
    )

    assert issue_1.id == "ISSUE-001"
    assert issue_1.status == IssueStatus.OPEN
    assert issue_1.severity == IssueSeverity.HIGH
    assert issue_1.task_id == "AUTH-001"
    assert "p2p:bug" in issue_1.labels
    assert "priority:high" in issue_1.labels

    # 2. Verify file on disk
    issue_file = ws.issues_dir / "ISSUE-001.json"
    assert issue_file.exists()

    # 3. Create second issue (monotonic ID)
    issue_2 = store.create_issue(
        title="SQL injection vulnerability in search endpoint",
        body="Raw string formatting used in query.",
        severity=IssueSeverity.CRITICAL,
    )
    assert issue_2.id == "ISSUE-002"

    # 4. Get and List
    fetched = store.get_issue("ISSUE-001")
    assert fetched is not None
    assert fetched.title == issue_1.title

    all_issues = store.list_issues()
    assert len(all_issues) == 2

    # 5. Close Issue
    closed = store.close_issue("ISSUE-001", comment="Fixed in commit 123456")
    assert closed is True

    open_issues = store.list_issues(status=IssueStatus.OPEN)
    assert len(open_issues) == 1
    assert open_issues[0].id == "ISSUE-002"

    closed_issues = store.list_issues(status=IssueStatus.CLOSED)
    assert len(closed_issues) == 1
    assert "Fixed in commit 123456" in closed_issues[0].body


def test_github_issue_provider_fallback(tmp_path):
    ws = Workspace(tmp_path)
    # Testing graceful fallback when gh is simulated as not present or offline
    provider = GitHubIssueProvider(ws)
    provider.has_gh = False

    issue = provider.create_issue(
        title="Test issue for fallback",
        body="Testing fallback to local issue store",
        severity=IssueSeverity.MEDIUM,
    )
    assert issue.id.startswith("ISSUE-")
    assert issue.status == IssueStatus.OPEN

    fetched = provider.get_issue(issue.id)
    assert fetched is not None
    assert fetched.id == issue.id

    assert provider.close_issue(issue.id) is True
    assert provider.get_issue(issue.id).status == IssueStatus.CLOSED
