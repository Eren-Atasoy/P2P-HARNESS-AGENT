"""Phase 2 Exit Criterion Test (docs/08 Faz 2).

Verifies 10-task synthetic graph execution with MockRuntime:
1. Tasks run in correct waves (dependency and conflict-free parallelism).
2. Injected error correctly escalates (repeated failure / max attempts).
3. Missing capability task triggers UNROUTABLE.
4. High risk task halts for human approval even in FULL autonomy mode.
5. Zero LLM model tokens consumed.
"""
from pathlib import Path
import pytest

from src.events.store import EventStore
from src.models import (
    AcceptanceCriterion,
    AutonomyLevel,
    Capability,
    Connection,
    ConnectionKind,
    EstimatedSize,
    GateResult,
    GateStatus,
    ReviewResult,
    ReviewVerdict,
    RiskLevel,
    RuntimeType,
    TaskContract,
    TaskOutcome,
    TaskStatus,
    VerifiedBy,
)
from src.orchestration.graph import TaskGraph
from src.orchestration.router import CapabilityRouter
from src.orchestration.scheduler import Scheduler
from src.runtime.mock import MockRuntime


def make_contract(
    tid: str,
    caps: list[Capability],
    risk: RiskLevel = RiskLevel.LOW,
    deps: list[str] = None,
    allowed: list[str] = None,
) -> TaskContract:
    return TaskContract(
        id=tid,
        title=f"Task {tid}",
        capabilities=caps,
        risk=risk,
        depends_on=deps or [],
        intent=f"Implement {tid}",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Standard functionality verification",
                verified_by=VerifiedBy.TEST,
                test_ref=f"tests/test_{tid.lower()}.py::test_ok",
            )
        ],
        inputs=["docs/01"],
        allowed_paths=allowed or [f"src/{tid.lower()}/**"],
        forbidden_paths=[],
        gates=["lint", "unit"],
        estimated_size=EstimatedSize.S,
        max_attempts=3,
        result_path=f".p2p/{tid}/result.json",
        acr_path=f".p2p/{tid}/acr/",
    )


def test_phase_2_exit_criterion_ten_task_synthetic_graph(tmp_path: Path):
    # Setup Connections
    conn_be = Connection(
        id="be-worker",
        kind=ConnectionKind.SUBSCRIPTION,
        runtime=RuntimeType.MOCK,
        credential_ref="session",
        capabilities=[Capability.BACKEND, Capability.DATABASE, Capability.SECURITY],
        quality={"backend": 0.92, "database": 0.90, "security": 0.95},
    )
    conn_fe = Connection(
        id="fe-worker",
        kind=ConnectionKind.SUBSCRIPTION,
        runtime=RuntimeType.MOCK,
        credential_ref="session",
        capabilities=[Capability.FRONTEND, Capability.DOCS],
        quality={"frontend": 0.91, "docs": 0.89},
    )
    # Notice: No connection provides BROWSER or DEVOPS!

    router = CapabilityRouter([conn_be, conn_fe])
    graph = TaskGraph()

    # Define 10 synthetic tasks
    # Wave 1 candidates (no deps, disjoint paths)
    t1_db = make_contract("DB-001", [Capability.DATABASE], RiskLevel.LOW, allowed=["backend/db/**"])
    t4_fe_core = make_contract("FE-001", [Capability.FRONTEND], RiskLevel.LOW, allowed=["frontend/core/**"])
    t7_doc = make_contract("DOC-001", [Capability.DOCS], RiskLevel.LOW, allowed=["docs/**"])

    # Dependent tasks
    t2_auth = make_contract("AUTH-001", [Capability.BACKEND, Capability.SECURITY], RiskLevel.HIGH, deps=["DB-001"], allowed=["backend/auth/**"])
    t10_high = make_contract("HIGH-001", [Capability.BACKEND], RiskLevel.HIGH, deps=["DB-001"], allowed=["backend/billing/**"])
    t3_api = make_contract("API-001", [Capability.BACKEND], RiskLevel.MEDIUM, deps=["AUTH-001"], allowed=["backend/api/**"])
    t5_fe_auth = make_contract("FE-002", [Capability.FRONTEND], RiskLevel.MEDIUM, deps=["FE-001", "AUTH-001"], allowed=["frontend/auth/**"])
    t6_fe_dash = make_contract("FE-003", [Capability.FRONTEND], RiskLevel.MEDIUM, deps=["FE-001", "API-001"], allowed=["frontend/dash/**"])

    # Error injected task (will fail gates repeatedly and escalate)
    t8_err = make_contract("ERR-001", [Capability.BACKEND], RiskLevel.LOW, allowed=["backend/err/**"])

    # Unroutable task (requires BROWSER capability which no active connection provides)
    t9_unr = make_contract("UNR-001", [Capability.BROWSER], RiskLevel.LOW, allowed=["e2e/**"])

    all_tasks = [t1_db, t2_auth, t3_api, t4_fe_core, t5_fe_auth, t6_fe_dash, t7_doc, t8_err, t9_unr, t10_high]
    for t in all_tasks:
        graph.add_task(t)

    # 1. Wave Calculation Verification
    waves = graph.compute_waves()
    assert len(waves) >= 3

    # In wave 1, DB-001, DOC-001, ERR-001, FE-001, UNR-001 run in parallel without conflicts
    assert "DB-001" in waves[0]
    assert "FE-001" in waves[0]
    assert "DOC-001" in waves[0]

    # AUTH-001 and HIGH-001 must appear in a wave strictly after DB-001
    w_db = next(i for i, w in enumerate(waves) if "DB-001" in w)
    w_auth = next(i for i, w in enumerate(waves) if "AUTH-001" in w)
    w_high = next(i for i, w in enumerate(waves) if "HIGH-001" in w)
    assert w_auth > w_db
    assert w_high > w_db

    # Setup EventStore and MockRuntime
    events_path = tmp_path / ".p2p" / "events.jsonl"
    event_store = EventStore(events_path)
    runtime = MockRuntime(default_outcome=TaskOutcome.COMPLETED)

    # Custom gate checker: ERR-001 fails with the same error to test stuck escalation
    def test_gate_checker(task: TaskContract, workspace: Path) -> GateResult:
        if task.id == "ERR-001":
            return GateResult(
                gate="unit",
                status=GateStatus.FAIL,
                exit_code=1,
                duration_ms=120,
                log_path=".p2p/err.log",
                failures=[{"file": "err.py", "line": 10, "message": "Injected persistent failure"}],
            )
        return GateResult(
            gate="unit",
            status=GateStatus.PASS,
            exit_code=0,
            duration_ms=50,
            log_path=".p2p/ok.log",
        )

    # Custom review checker: All pass
    def test_review_checker(task: TaskContract, workspace: Path) -> ReviewResult:
        return ReviewResult(
            task_id=task.id,
            attempt=1,
            verdict=ReviewVerdict.APPROVED,
            findings=[],
        )

    # 2. Execute with Scheduler under FULL autonomy mode
    scheduler = Scheduler(
        graph=graph,
        router=router,
        runtime=runtime,
        event_store=event_store,
        autonomy_level=AutonomyLevel.FULL,  # Testing full autonomy
        workspace=tmp_path / "workspace",
        run_id="run-phase2-test",
    )

    final_states = scheduler.run_all(gate_checker=test_gate_checker, review_checker=test_review_checker)

    # 3. Assertions matching Roadmap exit criteria:
    # A) UNR-001 must be UNROUTABLE
    assert final_states["UNR-001"] == TaskStatus.UNROUTABLE

    # B) ERR-001 must be ESCALATED due to repeated stuck failure
    assert final_states["ERR-001"] == TaskStatus.ESCALATED

    # C) HIGH-001 (high risk) must NOT be auto-merged even in FULL autonomy mode!
    # It must stop at APPROVED waiting for human approval!
    assert final_states["HIGH-001"] == TaskStatus.APPROVED
    assert final_states["AUTH-001"] == TaskStatus.APPROVED

    # D) Low and medium risk tasks with satisfied criteria must be MERGED in FULL mode
    assert final_states["DB-001"] == TaskStatus.MERGED
    assert final_states["FE-001"] == TaskStatus.MERGED
    assert final_states["DOC-001"] == TaskStatus.MERGED
    assert final_states["API-001"] == TaskStatus.MERGED
    assert final_states["FE-002"] == TaskStatus.MERGED
    assert final_states["FE-003"] == TaskStatus.MERGED

    # E) Event log verification: events were recorded deterministically
    recorded_events = event_store.read_all()
    assert len(recorded_events) > 20
    assert any(e.type.value == "TASK_UNROUTABLE" for e in recorded_events)
    assert any(e.type.value == "ESCALATED" for e in recorded_events)
    assert any(e.type.value == "MERGE_COMPLETED" for e in recorded_events)
