"""Official Exit Criterion Test for Faz 6.5: GitHub Work and PR Management.

Per docs/08-roadmap.md §Faz 6.5:
'Çıkış: Claude review\'ının ürettiği HIGH bulgu GitHub Issue\'suna dönüşür;
Gemini bu Issue\'dan üretilen FIX- sözleşmesini uygulayıp PR açar;
kapılardan geçip merge edildiğinde Issue otomatik kapanır.'
"""
from uuid import uuid4
from typer.testing import CliRunner

from src.cli.main import app
from src.collaboration.adapter import ReviewToIssueAdapter
from src.collaboration.issues import LocalIssueStore
from src.collaboration.models import IssueSeverity, IssueStatus, PRStatus
from src.collaboration.pull_requests import LocalPRStore
from src.models.enums import Capability, EstimatedSize, FindingSeverity, ReviewVerdict, RiskLevel, VerifiedBy
from src.models.result import ReviewFinding, ReviewResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.workspace.workspace import Workspace

runner = CliRunner()


def test_phase6_5_official_exit_criterion(tmp_path):
    """
    Proves the complete end-to-end work management lifecycle:
    1. Claude review emits a HIGH finding on an implemented task.
    2. ReviewToIssueAdapter turns finding into a tracked Issue.
    3. Adapter generates a FIX- task contract linked to the Issue.
    4. Orchestrator opens a Task PR for the fix.
    5. Quality gates pass and PR is merged.
    6. Issue is automatically closed with resolution comment.
    7. CLI commands 'p2p issues' and 'p2p pr' display synchronized state.
    """
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    issue_store = LocalIssueStore(ws)
    pr_store = LocalPRStore(ws)
    adapter = ReviewToIssueAdapter(issue_store, pr_store)

    # 1. Original task implemented by Gemini
    original_task = TaskContract(
        id="AUTH-001",
        title="Implement authentication token service",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.HIGH,
        depends_on=[],
        intent="Provide JWT access tokens for API requests.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Token service issues valid tokens.",
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

    # 2. Claude reviews the task and finds a HIGH finding
    review_result = ReviewResult(
        task_id=original_task.id,
        attempt=1,
        verdict=ReviewVerdict.CHANGES_REQUESTED,
        findings=[
            ReviewFinding(
                severity=FindingSeverity.HIGH,
                title="Security Flaw",
                issue="Refresh token rotation is not implemented.",
                suggestion="Implement token rotation in auth service",
                file="backend/app/auth.py",
                line=84,
            )
        ],
        architecture_compliance=False,
    )

    # 3. Transform finding into Issue and FIX- TaskContract
    pairs = adapter.process_review_findings(review_result, original_task)
    assert len(pairs) == 1
    issue, repair_task = pairs[0]

    assert issue.severity == IssueSeverity.HIGH
    assert issue.status == IssueStatus.OPEN
    assert "Refresh token rotation" in issue.title

    assert repair_task.id.startswith("FIX-")
    assert original_task.id in repair_task.depends_on
    assert f"Linked to {issue.id}" in repair_task.notes

    # 4. Orchestrator creates Task PR for the repair task
    task_pr = pr_store.create_task_pr(
        task=repair_task,
        head_branch=f"p2p/task/{repair_task.id}",
        base_branch="p2p/integration",
        issue_id=issue.id,
        gate_summary="pytest: PASS, lint: PASS",
    )
    assert task_pr.status == PRStatus.OPEN
    assert f"Fixes {issue.id}" in task_pr.title

    # 5. Deterministic quality gates pass and task is merged
    closed = adapter.close_issue_on_merge(repair_task, pr_number=task_pr.number, issue_id=issue.id)
    assert closed is True

    # 6. Verify Issue is closed and PR is merged
    closed_issue = issue_store.get_issue(issue.id)
    assert closed_issue.status == IssueStatus.CLOSED
    assert f"PR #{task_pr.number}" in closed_issue.body

    merged_pr = pr_store.list_prs(status=PRStatus.MERGED)[0]
    assert merged_pr.number == task_pr.number
    assert merged_pr.status == PRStatus.MERGED

    # 7. Verify CLI integration reflects closed issue and merged PR
    cli_issues = runner.invoke(app, ["issues", "--workspace", str(tmp_path), "--status", "CLOSED"])
    assert cli_issues.exit_code == 0
    assert issue.id in cli_issues.stdout
    assert "CLOSED" in cli_issues.stdout

    cli_pr = runner.invoke(app, ["pr", "--workspace", str(tmp_path), "--status", "MERGED"])
    assert cli_pr.exit_code == 0
    assert f"#{task_pr.number}" in cli_pr.stdout
    assert "MERGED" in cli_pr.stdout
