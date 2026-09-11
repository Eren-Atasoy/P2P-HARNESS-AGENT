"""Unit tests for LocalPRStore and GitHubPRProvider (Faz 6.5)."""
import pytest
from src.collaboration.models import PRStatus, PRType
from src.collaboration.pull_requests import GitHubPRProvider, LocalPRStore
from src.models.enums import Capability, EstimatedSize, RiskLevel, VerifiedBy
from src.models.task import AcceptanceCriterion, TaskContract
from src.workspace.workspace import Workspace


@pytest.fixture
def sample_task():
    return TaskContract(
        id="API-001",
        title="Mount user profile endpoints",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.MEDIUM,
        depends_on=[],
        intent="Provide endpoints to view and update user profile information.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="GET /users/me returns current user profile.",
                verified_by=VerifiedBy.GATE,
                gate_ref="pytest",
            )
        ],
        inputs=[".p2p/docs/architecture.md"],
        allowed_paths=["backend/app/**"],
        forbidden_paths=[".p2p/**"],
        gates=["pytest"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/runs/{run_id}/result.json",
        acr_path=".p2p/acr/ACR-API-001.md",
    )


def test_local_pr_store_task_and_release_pr(tmp_path, sample_task):
    ws = Workspace(tmp_path)
    store = LocalPRStore(ws)

    # 1. Create Task PR
    task_pr = store.create_task_pr(
        task=sample_task,
        head_branch="p2p/task/API-001",
        base_branch="p2p/integration",
        issue_id="#42",
        gate_summary="pytest: PASS, lint: PASS",
    )

    assert task_pr.number == 1
    assert "feat(API-001): Mount user profile endpoints (Fixes #42)" in task_pr.title
    assert "AC-1" in task_pr.body
    assert "pytest: PASS" in task_pr.body
    assert task_pr.status == PRStatus.OPEN
    assert task_pr.pr_type == PRType.TASK

    # Verify file on disk
    pr_file = ws.prs_dir / "PR-001.json"
    assert pr_file.exists()

    # 2. Create Release PR
    rel_pr = store.create_release_pr(
        project_name="todo-platform",
        head_branch="p2p/integration",
        base_branch="main",
        summary="All 4 tasks completed and verified.",
    )
    assert rel_pr.number == 2
    assert rel_pr.pr_type == PRType.RELEASE
    assert "release: todo-platform" in rel_pr.title
    assert "p2p/integration" in rel_pr.head_branch
    assert "main" in rel_pr.base_branch

    # 3. Merge Task PR
    merged = store.merge_pr(task_pr.number)
    assert merged is True

    prs = store.list_prs(status=PRStatus.MERGED)
    assert len(prs) == 1
    assert prs[0].number == 1
    assert prs[0].merged_at is not None


def test_github_pr_provider_fallback(tmp_path, sample_task):
    ws = Workspace(tmp_path)
    provider = GitHubPRProvider(ws)
    provider.has_gh = False

    pr = provider.create_task_pr(
        task=sample_task,
        head_branch="p2p/task/API-001",
    )
    assert pr.number == 1
    assert pr.status == PRStatus.OPEN
    assert provider.merge_pr(pr.number) is True
