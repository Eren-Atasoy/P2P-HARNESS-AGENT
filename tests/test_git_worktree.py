"""Unit tests for GitManager and worktree operations."""

from pathlib import Path
import pytest

from src.models.enums import Capability, EstimatedSize, GateStatus, RiskLevel
from src.models.result import AgentResult, GateResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.workspace.git import GitManager, MergeConflictError
from src.workspace.workspace import Workspace


@pytest.fixture
def git_workspace(tmp_path: Path) -> tuple[Workspace, GitManager]:
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    git = GitManager(ws)
    git.init_repo()
    return ws, git


def test_git_init_and_branches(git_workspace: tuple[Workspace, GitManager]) -> None:
    ws, git = git_workspace
    # Check current branch is p2p/integration
    proc = git._run_git(["branch", "--show-current"])
    assert proc.stdout.strip() == "p2p/integration"

    # Both branches exist
    proc = git._run_git(["branch", "--list"])
    branches = [b.strip().replace("* ", "") for b in proc.stdout.splitlines()]
    assert "main" in branches
    assert "p2p/integration" in branches


def test_create_and_remove_worktree_success(git_workspace: tuple[Workspace, GitManager]) -> None:
    ws, git = git_workspace
    wt_path = git.create_worktree("TASK-001")
    assert wt_path.exists()
    assert (wt_path / ".git").exists()

    # Verify branch name in worktree
    proc = git._run_git(["branch", "--show-current"], cwd=wt_path)
    assert proc.stdout.strip() == "p2p/task/TASK-001"

    # Remove on success
    git.remove_worktree("TASK-001", failed=False)
    assert not wt_path.exists()


def test_remove_worktree_failed_preservation(git_workspace: tuple[Workspace, GitManager]) -> None:
    ws, git = git_workspace
    wt_path = git.create_worktree("TASK-FAIL")
    test_file = wt_path / "failed_debug.txt"
    test_file.write_text("debug details", encoding="utf-8")

    git.remove_worktree("TASK-FAIL", failed=True)
    assert not wt_path.exists()

    failed_saved = ws.failed_worktree_path("TASK-FAIL")
    assert failed_saved.exists()
    assert (failed_saved / "failed_debug.txt").read_text(encoding="utf-8") == "debug details"


def test_commit_task_format(git_workspace: tuple[Workspace, GitManager]) -> None:
    ws, git = git_workspace
    wt_path = git.create_worktree("API-001")

    # Add a file in worktree
    (wt_path / "endpoint.py").write_text("def hello(): return 200", encoding="utf-8")

    contract = TaskContract(
        id="API-001",
        title="Implement endpoint",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        depends_on=[],
        intent="Provide hello world endpoint for clients.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Endpoint returns 200",
                verified_by="test",
                test_ref="tests/test_endpoint.py::test_hello",
            )
        ],
        inputs=[],
        allowed_paths=["endpoint.py"],
        forbidden_paths=[],
        result_path=".p2p/runs/run1/result.json",
        acr_path=".p2p/acr/",
        gates=["unit"],
        estimated_size=EstimatedSize.S,
    )

    agent_result = AgentResult(
        task_id="API-001",
        run_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        outcome="completed",
        summary="Implemented hello endpoint",
        files_changed=["endpoint.py"],
        criteria_addressed=["AC-1"],
    )

    gate_results = [
        GateResult(
            gate="unit",
            status=GateStatus.PASS,
            exit_code=0,
            duration_ms=100,
            log_path=".p2p/runs/run1/gates/unit.log",
        )
    ]

    commit_hash = git.commit_task(
        wt_path,
        contract,
        agent_result,
        gate_results,
        runtime_name="gemini",
        attempt=1,
    )
    assert commit_hash

    # Inspect commit message format
    log_proc = git._run_git(["log", "-n", "1", "--pretty=format:%B"], cwd=wt_path)
    commit_body = log_proc.stdout
    assert "feat(API-001): Implemented hello endpoint" in commit_body
    assert "Provide hello world endpoint for clients." in commit_body
    assert "Acceptance:" in commit_body
    assert "AC-1 ✓" in commit_body
    assert "Gates: unit ✓" in commit_body
    assert "Runtime: gemini  Attempt: 1" in commit_body


def test_merge_task_and_conflict_detection(git_workspace: tuple[Workspace, GitManager]) -> None:
    ws, git = git_workspace

    # Task A modifies shared.txt
    wt_a = git.create_worktree("TASK-A")
    (wt_a / "shared.txt").write_text("Content from A\n", encoding="utf-8")
    git._run_git(["add", "."], cwd=wt_a)
    git._run_git(["commit", "-m", "feat(TASK-A): change shared"], cwd=wt_a)

    # Task B modifies shared.txt differently
    wt_b = git.create_worktree("TASK-B")
    (wt_b / "shared.txt").write_text("Conflicting content from B\n", encoding="utf-8")
    git._run_git(["add", "."], cwd=wt_b)
    git._run_git(["commit", "-m", "feat(TASK-B): change shared conflicting"], cwd=wt_b)

    # Merge Task A into integration
    merge_hash_a = git.merge_task("TASK-A")
    assert merge_hash_a
    git.remove_worktree("TASK-A")

    # Merge Task B should fail with MergeConflictError
    with pytest.raises(MergeConflictError):
        git.merge_task("TASK-B")

    # Integration branch should be cleanly aborted
    status_proc = git._run_git(["status", "--porcelain"])
    assert status_proc.stdout.strip() == ""
    git.remove_worktree("TASK-B")
