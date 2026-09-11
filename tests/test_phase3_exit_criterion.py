"""Phase 3 exit criterion test per docs/08-roadmap.md:

"Çıkış: İki sahte task paralel worktree'de çalışıp integration'a çakışmasız
birleşiyor; kapsam dışına yazan task yakalanıp geri alınıyor; boş projede
bootstrap sonrası kapılar ERROR değil PASS/FAIL veriyor."
"""

from datetime import datetime, timezone
from pathlib import Path
import uuid

from src.models.enums import Capability, EstimatedSize, GateStatus, RiskLevel
from src.models.project import ProjectSpec
from src.models.result import AgentResult, GateResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.workspace.bootstrap import WorkspaceBootstrap
from src.workspace.git import GitManager
from src.workspace.scope import ScopeValidator
from src.workspace.workspace import Workspace


def test_phase3_exit_criterion(tmp_path: Path) -> None:
    # 1. Boş projede bootstrap çalıştırılır; kapılar ERROR değil PASS/FAIL verir
    ws = Workspace(tmp_path)
    git = GitManager(ws)
    bootstrap = WorkspaceBootstrap(ws, git)

    project_spec = ProjectSpec(
        id=uuid.uuid4(),
        name="synthetic-crm",
        prompt="Build a modular CRM backend",
        created_at=datetime.now(timezone.utc),
        p2p_version="0.1.0",
        stack={"backend": {"language": "python", "framework": "fastapi"}},
        decisions=[],
        targets=["api"],
    )

    bootstrap.scaffold(project_spec)
    bootstrap.init_git()
    bootstrap.setup_cache()

    smoke_result = bootstrap.run_smoke_check()
    assert smoke_result.status != GateStatus.ERROR
    assert smoke_result.status == GateStatus.PASS

    # 2. İki sahte task paralel worktree'de çalışıp integration'a çakışmasız birleşir
    wt1 = git.create_worktree("TASK-001")
    wt2 = git.create_worktree("TASK-002")

    contract1 = TaskContract(
        id="TASK-001",
        title="Users API endpoint",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        depends_on=[],
        intent="Create users API endpoint.",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Users endpoint exists", verified_by="test", test_ref="tests/api/test_users.py::test_get")
        ],
        inputs=[],
        allowed_paths=["backend/api/**"],
        forbidden_paths=[],
        result_path=".p2p/runs/run-1/result.json",
        acr_path=".p2p/acr/",
        gates=["unit"],
        estimated_size=EstimatedSize.S,
    )

    contract2 = TaskContract(
        id="TASK-002",
        title="Billing service",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        depends_on=[],
        intent="Create billing service logic.",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Billing calculates properly", verified_by="test", test_ref="tests/services/test_billing.py::test_calc")
        ],
        inputs=[],
        allowed_paths=["backend/services/**"],
        forbidden_paths=[],
        result_path=".p2p/runs/run-2/result.json",
        acr_path=".p2p/acr/",
        gates=["unit"],
        estimated_size=EstimatedSize.S,
    )

    # Worktree 1 implementation
    users_file = wt1 / "backend" / "api" / "users.py"
    users_file.parent.mkdir(parents=True, exist_ok=True)
    users_file.write_text("def get_users(): return []\n", encoding="utf-8")

    result1 = AgentResult(
        task_id="TASK-001",
        run_id="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        outcome="completed",
        summary="Users API implemented",
        files_changed=["backend/api/users.py"],
        criteria_addressed=["AC-1"],
    )
    gates1 = [
        GateResult(
            gate="unit",
            status=GateStatus.PASS,
            exit_code=0,
            duration_ms=50,
            log_path=".p2p/runs/run-1/gates/unit.log",
        )
    ]

    git.commit_task(wt1, contract1, result1, gates1, runtime_name="gemini", attempt=1)

    # Worktree 2 implementation
    billing_file = wt2 / "backend" / "services" / "billing.py"
    billing_file.parent.mkdir(parents=True, exist_ok=True)
    billing_file.write_text("def calculate_total(): return 100\n", encoding="utf-8")

    result2 = AgentResult(
        task_id="TASK-002",
        run_id="8fa51ec6-b31c-43f1-b92c-6a7f0525ff0b",
        outcome="completed",
        summary="Billing service implemented",
        files_changed=["backend/services/billing.py"],
        criteria_addressed=["AC-1"],
    )
    gates2 = [
        GateResult(
            gate="unit",
            status=GateStatus.PASS,
            exit_code=0,
            duration_ms=45,
            log_path=".p2p/runs/run-2/gates/unit.log",
        )
    ]

    git.commit_task(wt2, contract2, result2, gates2, runtime_name="gemini", attempt=1)

    # Deterministic merge into p2p/integration in task ID order
    git.merge_task("TASK-001")
    git.remove_worktree("TASK-001", failed=False)

    git.merge_task("TASK-002")
    git.remove_worktree("TASK-002", failed=False)

    # Verify integration has both changes cleanly merged
    assert (ws.root_path / "backend" / "api" / "users.py").exists()
    assert (ws.root_path / "backend" / "services" / "billing.py").exists()

    # 3. Kapsam dışına yazan task yakalanıp geri alınır
    wt3 = git.create_worktree("TASK-003")
    contract3 = TaskContract(
        id="TASK-003",
        title="Restricted task",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.MEDIUM,
        depends_on=[],
        intent="Touch forbidden models.",
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", statement="Models updated", verified_by="test", test_ref="tests/test_models.py::test_acc")],
        inputs=[],
        allowed_paths=["backend/api/**"],
        forbidden_paths=["backend/models/**"],
        result_path=".p2p/runs/run-3/result.json",
        acr_path=".p2p/acr/",
        gates=["unit"],
        estimated_size=EstimatedSize.S,
    )

    forbidden_model = wt3 / "backend" / "models" / "account.py"
    forbidden_model.parent.mkdir(parents=True, exist_ok=True)
    forbidden_model.write_text("class Account: pass\n", encoding="utf-8")

    validator = ScopeValidator(git)
    scope_eval = validator.validate_scope(wt3, contract3)

    assert not scope_eval.is_valid
    assert "backend/models/account.py" in scope_eval.unauthorized_files

    # Rollback unauthorized changes
    validator.rollback_unauthorized_changes(wt3)

    assert not forbidden_model.exists()
    assert len(git.get_status_porcelain(wt3)) == 0

    # Preserve failed worktree for audit
    git.remove_worktree("TASK-003", failed=True)
    assert ws.failed_worktree_path("TASK-003").exists()
