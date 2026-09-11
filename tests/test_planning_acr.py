"""Unit tests for Architecture Change Request (ACR) Manager (Faz 6)."""
from uuid import uuid4
import pytest
from src.events.store import EventStore
from src.models.enums import Capability, EstimatedSize, EventType, RiskLevel, TargetType, VerifiedBy
from src.models.project import ProjectSpec
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.graph import TaskGraph
from src.planning.acr import ACRManager
from src.planning.architect import ArchitecturePlanner
from src.workspace.workspace import Workspace


@pytest.fixture
def workspace_with_arch(tmp_path):
    ws = Workspace(tmp_path)
    store = EventStore(ws.events_path)
    spec = ProjectSpec(
        id=uuid4(),
        name="test-acr-project",
        prompt="ACR test project",
        stack={"backend": "fastapi"},
        targets=[TargetType.API],
    )
    planner = ArchitecturePlanner(ws, store)
    planner.plan_architecture(spec)
    return ws, store


def test_acr_open_and_parse(workspace_with_arch):
    ws, store = workspace_with_arch
    manager = ACRManager(ws, store)

    acr_file = manager.open_acr(
        task_id="API-001",
        acr_id="ACR-001",
        title="Schema cannot support tags relationship",
        observation="The Item schema in models.py lacks many-to-many relationship with Tag entity.",
        proposed_change="Introduce Tag model and ItemTag association table in architecture.",
        workaround_possible=False,
    )

    assert acr_file.exists()
    parsed = manager.parse_acr(acr_file)
    assert parsed["acr_id"] == "ACR-001"
    assert parsed["task_id"] == "API-001"
    assert "Schema cannot support tags" in parsed["title"]
    assert parsed["workaround_possible"] is False

    events = store.read_all()
    assert any(e.type == EventType.ACR_OPENED for e in events)


def test_acr_accept_amends_architecture_and_updates_graph(workspace_with_arch):
    ws, store = workspace_with_arch
    manager = ACRManager(ws, store)

    # Setup initial graph with API-001
    graph = TaskGraph()
    task = TaskContract(
        id="API-001",
        title="Implement API",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.MEDIUM,
        depends_on=[],
        intent="Implement API",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="API works",
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
    graph.add_task(task)

    acr_file = manager.open_acr(
        task_id="API-001",
        acr_id="ACR-002",
        title="Missing Tag Schema",
        observation="Tag entity needed.",
        proposed_change="Add Tag entity to models.",
    )

    verdict, new_task = manager.resolve_acr(
        acr_path=acr_file,
        verdict="ACCEPTED",
        rationale="Approved by architect Claude.",
        task_graph=graph,
    )

    assert verdict == "ACCEPTED"
    assert new_task is not None
    assert new_task.id.startswith("AMEND-")
    assert new_task.id in graph.tasks

    # Verify original task now depends on the new amendment task (docs/03 §4)
    assert new_task.id in task.depends_on
    assert "ACCEPTED" in task.notes

    # Verify graph is still a valid DAG
    graph.validate()

    # Verify architecture document was amended
    arch_content = (ws.p2p_docs_dir / "architecture.md").read_text(encoding="utf-8")
    assert "Architecture Amendment (ACR-002)" in arch_content

    # Verify ACR_RESOLVED event
    events = store.read_all()
    resolved_events = [e for e in events if e.type == EventType.ACR_RESOLVED]
    assert len(resolved_events) == 1
    assert resolved_events[0].payload["verdict"] == "ACCEPTED"


def test_acr_reject_and_defer(workspace_with_arch):
    ws, store = workspace_with_arch
    manager = ACRManager(ws, store)

    graph = TaskGraph()
    task = TaskContract(
        id="CORE-001",
        title="Implement Core",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.MEDIUM,
        depends_on=[],
        intent="Implement Core",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Core works",
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
        acr_path=".p2p/acr/ACR-CORE-001.md",
    )
    graph.add_task(task)

    # 1. Test REJECT
    acr_rej = manager.open_acr("CORE-001", "ACR-003", "Reject test", "Obs", "Change")
    v_rej, _ = manager.resolve_acr(acr_rej, "REJECTED", "Out of current scope", task_graph=graph)
    assert v_rej == "REJECTED"
    assert "REJECTED" in task.notes

    # 2. Test DEFERRED
    acr_def = manager.open_acr("CORE-001", "ACR-004", "Defer test", "Obs", "Change", workaround_possible=True)
    v_def, _ = manager.resolve_acr(acr_def, "DEFERRED", "Postpone to next milestone", task_graph=graph)
    assert v_def == "DEFERRED"
    assert "DEFERRED" in task.notes
    assert (ws.p2p_docs_dir / "tech_debt.md").exists()
