"""Tests for OrchestratorEngine (docs/03 §7)."""
from pathlib import Path

import pytest

from src.events.store import EventStore
from src.models.connection import Connection
from src.models.enums import AutonomyLevel, Capability, ConnectionKind, CostTier, EventType, GateStatus, RiskLevel, RuntimeType, TaskStatus, VerifiedBy, EstimatedSize
from src.models.result import GateResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.engine import LoopExitReason, OrchestratorEngine
from src.orchestration.graph import TaskGraph
from src.orchestration.router import CapabilityRouter
from src.runtime.mock import MockRuntime
from src.verification.config import GatesConfig
from src.verification.runner import GateRunner
from src.workspace.workspace import Workspace


@pytest.fixture
def mock_router() -> CapabilityRouter:
    router = CapabilityRouter()
    conn = Connection(
        id="mock-conn",
        kind=ConnectionKind.LOCAL,
        runtime=RuntimeType.MOCK,
        credential_ref="env:MOCK_KEY",
        cost_tier=CostTier.FREE,
        capabilities=[Capability.BACKEND, Capability.FRONTEND, Capability.TEST],
        limits={"concurrency": 2, "timeout_seconds": 60},
    )
    router.add_connection(conn)
    return router


def test_orchestrator_engine_completed_flow(tmp_path: Path, mock_router: CapabilityRouter):
    workspace = Workspace(tmp_path)
    (tmp_path / ".p2p").mkdir(parents=True, exist_ok=True)
    event_store = EventStore(tmp_path / ".p2p" / "events.jsonl")

    t1 = TaskContract(
        id="TASK-001",
        title="Init Core",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Initialize core backend",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Init file exists", verified_by=VerifiedBy.TEST, test_ref="tests/test_core.py::test_init")
        ],
        inputs=["docs/01"],
        allowed_paths=["core.py"],
        forbidden_paths=[],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )
    t2 = TaskContract(
        id="TASK-002",
        title="Init Service",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        depends_on=["TASK-001"],
        intent="Initialize service layer",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-2", statement="Service exists", verified_by=VerifiedBy.TEST, test_ref="tests/test_svc.py::test_svc")
        ],
        inputs=["docs/01"],
        allowed_paths=["service.py"],
        forbidden_paths=[],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )

    graph = TaskGraph()
    graph.add_task(t1)
    graph.add_task(t2)

    runtime = MockRuntime(files_to_create={"core.py": "# core", "service.py": "# service"})

    # Setup mock GateRunner that passes
    gate_runner = GateRunner(workspace, GatesConfig.default_gates())
    gate_runner.run_gates = lambda gate_names, target_dir=None, run_id=None, fail_fast=True: [
        GateResult(gate="unit", status=GateStatus.PASS, exit_code=0, duration_ms=10, log_path="unit.log")
    ]

    engine = OrchestratorEngine(
        workspace=workspace,
        graph=graph,
        router=mock_router,
        runtime=runtime,
        event_store=event_store,
        gate_runner=gate_runner,
        autonomy_level=AutonomyLevel.FULL,
        enable_git=False,
    )

    loop_res = engine.run_loop()

    assert loop_res.exit_reason == LoopExitReason.COMPLETED
    assert engine.task_states["TASK-001"] == TaskStatus.MERGED
    assert engine.task_states["TASK-002"] == TaskStatus.MERGED
    assert loop_res.events_count > 0

    events = event_store.read_all()
    event_types = [e.type for e in events]
    assert EventType.RUN_STARTED in event_types
    assert EventType.RUN_FINISHED in event_types
    assert EventType.MERGE_COMPLETED in event_types


def test_orchestrator_engine_steer(tmp_path: Path, mock_router: CapabilityRouter):
    workspace = Workspace(tmp_path)
    (tmp_path / ".p2p").mkdir(parents=True, exist_ok=True)
    event_store = EventStore(tmp_path / ".p2p" / "events.jsonl")

    t1 = TaskContract(
        id="TASK-001",
        title="Needs Steering",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Needs operator guidance",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Must work", verified_by=VerifiedBy.TEST, test_ref="tests/test_steer.py::test_fn")
        ],
        inputs=["docs/01"],
        allowed_paths=["src/**"],
        forbidden_paths=[],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )
    graph = TaskGraph()
    graph.add_task(t1)

    runtime = MockRuntime()
    engine = OrchestratorEngine(
        workspace=workspace,
        graph=graph,
        router=mock_router,
        runtime=runtime,
        event_store=event_store,
        enable_git=False,
    )

    # Force escalate
    engine.task_states["TASK-001"] = TaskStatus.ESCALATED

    # Steer
    steered = engine.steer("TASK-001", "Use SQLite instead of Postgres")
    assert steered is True
    assert engine.task_states["TASK-001"] == TaskStatus.READY
    assert "SQLite" in engine.human_guidance["TASK-001"]

    events = event_store.read_all()
    event_types = [e.type for e in events]
    assert EventType.HUMAN_STEERED in event_types
    assert EventType.DECISION_RECORDED in event_types
