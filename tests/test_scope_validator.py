"""Unit tests for ScopeValidator."""

from pathlib import Path
import pytest

from src.models.enums import Capability, EstimatedSize, RiskLevel
from src.models.result import AgentResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.workspace.git import GitManager
from src.workspace.scope import ScopeValidator
from src.workspace.workspace import Workspace


@pytest.fixture
def scope_setup(tmp_path: Path) -> tuple[Workspace, GitManager, ScopeValidator, Path, TaskContract]:
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    git = GitManager(ws)
    git.init_repo()

    wt_path = git.create_worktree("TASK-101")

    contract = TaskContract(
        id="TASK-101",
        title="Scoped task",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        depends_on=[],
        intent="Test scoping rules.",
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", statement="valid", verified_by="test", test_ref="tests/test_api.py::test_valid")],
        inputs=[],
        allowed_paths=["backend/api/**", "backend/services/**"],
        forbidden_paths=["backend/models/**", "tests/**", ".p2p/**"],
        result_path=".p2p/runs/run-1/result.json",
        acr_path=".p2p/acr/",
        gates=["unit"],
        estimated_size=EstimatedSize.S,
    )

    validator = ScopeValidator(git)
    return ws, git, validator, wt_path, contract


def test_scope_allowed_modification(scope_setup: tuple[Workspace, GitManager, ScopeValidator, Path, TaskContract]) -> None:
    ws, git, validator, wt_path, contract = scope_setup

    target_file = wt_path / "backend" / "api" / "users.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("class Users: pass", encoding="utf-8")

    result = AgentResult(
        task_id="TASK-101",
        run_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        outcome="completed",
        summary="added users api",
        files_changed=["backend/api/users.py"],
        criteria_addressed=["AC-1"],
    )

    res = validator.validate_scope(wt_path, contract, result)
    assert res.is_valid
    assert len(res.violations) == 0


def test_scope_forbidden_modification(scope_setup: tuple[Workspace, GitManager, ScopeValidator, Path, TaskContract]) -> None:
    ws, git, validator, wt_path, contract = scope_setup

    # Write to forbidden models directory
    forbidden_file = wt_path / "backend" / "models" / "db.py"
    forbidden_file.parent.mkdir(parents=True, exist_ok=True)
    forbidden_file.write_text("class DbModel: pass", encoding="utf-8")

    result = AgentResult(
        task_id="TASK-101",
        run_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        outcome="completed",
        summary="sneaked in db model change",
        files_changed=["backend/models/db.py"],
        criteria_addressed=["AC-1"],
    )

    res = validator.validate_scope(wt_path, contract, result)
    assert not res.is_valid
    assert any("forbidden_paths" in v for v in res.violations)
    assert "backend/models/db.py" in res.unauthorized_files


def test_scope_exempt_result_and_acr_paths(scope_setup: tuple[Workspace, GitManager, ScopeValidator, Path, TaskContract]) -> None:
    ws, git, validator, wt_path, contract = scope_setup

    # Result and ACR paths are inside .p2p/** which is forbidden, but exempt
    res_path = wt_path / ".p2p" / "runs" / "run-1" / "result.json"
    res_path.parent.mkdir(parents=True, exist_ok=True)
    res_path.write_text("{}", encoding="utf-8")

    acr_file = wt_path / ".p2p" / "acr" / "ACR-001.md"
    acr_file.parent.mkdir(parents=True, exist_ok=True)
    acr_file.write_text("# ACR", encoding="utf-8")

    # Allowed file also changed
    allowed_file = wt_path / "backend" / "api" / "users.py"
    allowed_file.parent.mkdir(parents=True, exist_ok=True)
    allowed_file.write_text("class Users: pass", encoding="utf-8")

    result = AgentResult(
        task_id="TASK-101",
        run_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        outcome="completed",
        summary="added users api with acr and result",
        files_changed=["backend/api/users.py"],
        criteria_addressed=["AC-1"],
    )

    res = validator.validate_scope(wt_path, contract, result)
    assert res.is_valid
    assert len(res.violations) == 0


def test_scope_undeclared_file_violation(scope_setup: tuple[Workspace, GitManager, ScopeValidator, Path, TaskContract]) -> None:
    ws, git, validator, wt_path, contract = scope_setup

    allowed_file = wt_path / "backend" / "api" / "users.py"
    allowed_file.parent.mkdir(parents=True, exist_ok=True)
    allowed_file.write_text("class Users: pass", encoding="utf-8")

    undeclared_file = wt_path / "backend" / "services" / "email.py"
    undeclared_file.parent.mkdir(parents=True, exist_ok=True)
    undeclared_file.write_text("def send(): pass", encoding="utf-8")

    # Agent claims it only changed users.py
    result = AgentResult(
        task_id="TASK-101",
        run_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        outcome="completed",
        summary="changed users",
        files_changed=["backend/api/users.py"],
        criteria_addressed=["AC-1"],
    )

    res = validator.validate_scope(wt_path, contract, result)
    assert not res.is_valid
    assert "backend/services/email.py" in res.undeclared_files


def test_scope_rollback_unauthorized(scope_setup: tuple[Workspace, GitManager, ScopeValidator, Path, TaskContract]) -> None:
    ws, git, validator, wt_path, contract = scope_setup

    unauthorized_file = wt_path / "forbidden.txt"
    unauthorized_file.write_text("unauthorized", encoding="utf-8")

    validator.rollback_unauthorized_changes(wt_path)
    assert not unauthorized_file.exists()
    status = git.get_status_porcelain(wt_path)
    assert len(status) == 0
