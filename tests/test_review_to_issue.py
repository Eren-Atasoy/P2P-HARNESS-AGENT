"""Unit tests for ReviewToIssueAdapter (Faz 6.5)."""
from uuid import uuid4
import pytest
from src.collaboration.adapter import ReviewToIssueAdapter
from src.collaboration.issues import LocalIssueStore
from src.collaboration.models import IssueSeverity, IssueStatus, PRStatus
from src.collaboration.pull_requests import LocalPRStore
from src.models.enums import Capability, EstimatedSize, FindingSeverity, ReviewVerdict, RiskLevel, VerifiedBy
from src.models.result import ReviewFinding, ReviewResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.workspace.workspace import Workspace


@pytest.fixture
def sample_task():
    return TaskContract(
        id="AUTH-001",
        title="Implement authentication service",
        capabilities=[Capability.BACKEND, Capability.SECURITY],
        risk=RiskLevel.HIGH,
        depends_on=[],
        intent="Provide JWT authentication and token management.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Auth service issues valid JWT tokens.",
                verified_by=VerifiedBy.GATE,
                gate_ref="pytest",
            )
        ],
        inputs=[".p2p/docs/architecture.md"],
        allowed_paths=["backend/app/auth.py"],
        forbidden_paths=[".p2p/**"],
        gates=["pytest"],
        estimated_size=EstimatedSize.M,
        result_path=".p2p/runs/{run_id}/result.json",
        acr_path=".p2p/acr/ACR-AUTH-001.md",
    )


def test_review_findings_to_issue_and_repair_task(tmp_path, sample_task):
    ws = Workspace(tmp_path)
    issue_store = LocalIssueStore(ws)
    pr_store = LocalPRStore(ws)
    adapter = ReviewToIssueAdapter(issue_store, pr_store)

    # Simulate Claude review with 1 HIGH finding, 1 CRITICAL finding, and 1 LOW finding
    review_result = ReviewResult(
        task_id="AUTH-001",
        attempt=1,
        verdict=ReviewVerdict.CHANGES_REQUESTED,
        findings=[
            ReviewFinding(
                severity=FindingSeverity.HIGH,
                title="Security Flaw",
                issue="Refresh token rotation is missing",
                suggestion="Implement refresh token rotation on token renewal",
                file="backend/app/auth.py",
                line=84,
            ),
            ReviewFinding(
                severity=FindingSeverity.CRITICAL,
                title="Vulnerability",
                issue="Hardcoded JWT secret key detected in source",
                suggestion="Read JWT secret key from environment variable",
                file="backend/app/auth.py",
                line=12,
            ),
            ReviewFinding(
                severity=FindingSeverity.LOW,
                title="Style",
                issue="Missing docstring on helper function",
                suggestion="Add docstring to helper",
                file="backend/app/auth.py",
                line=120,
            ),
        ],
        architecture_compliance=False,
    )

    pairs = adapter.process_review_findings(review_result, sample_task)

    # Only CRITICAL and HIGH findings become issues (2 items)
    assert len(pairs) == 2

    issue_high, task_high = pairs[0]
    assert issue_high.severity == IssueSeverity.HIGH
    assert "Refresh token rotation" in issue_high.title
    assert task_high.id.startswith("FIX-")
    assert sample_task.id in task_high.depends_on
    assert f"Linked to {issue_high.id}" in task_high.notes

    issue_crit, task_crit = pairs[1]
    assert issue_crit.severity == IssueSeverity.CRITICAL
    assert "Hardcoded JWT secret" in issue_crit.title
    assert task_crit.risk == RiskLevel.HIGH


def test_close_issue_on_merge_lifecycle(tmp_path, sample_task):
    ws = Workspace(tmp_path)
    issue_store = LocalIssueStore(ws)
    pr_store = LocalPRStore(ws)
    adapter = ReviewToIssueAdapter(issue_store, pr_store)

    # 1. Create issue
    issue = issue_store.create_issue(
        title="Fix SQL syntax error in repository",
        body="Missing comma in table schema.",
        severity=IssueSeverity.HIGH,
        task_id=sample_task.id,
    )
    assert issue.status == IssueStatus.OPEN

    # 2. Create Task PR
    pr = pr_store.create_task_pr(sample_task, head_branch="p2p/task/AUTH-001", issue_id=issue.id)
    assert pr.status == PRStatus.OPEN

    # 3. Simulate Repair completion and merge
    closed = adapter.close_issue_on_merge(sample_task, pr_number=pr.number, issue_id=issue.id)
    assert closed is True

    # 4. Verify issue closed and PR merged
    updated_issue = issue_store.get_issue(issue.id)
    assert updated_issue.status == IssueStatus.CLOSED
    assert "Resolved and verified" in updated_issue.body

    updated_pr = pr_store.list_prs(status=PRStatus.MERGED)[0]
    assert updated_pr.number == pr.number
