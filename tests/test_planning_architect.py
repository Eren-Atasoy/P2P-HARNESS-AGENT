"""Unit tests for ArchitecturePlanner (Faz 6)."""
from uuid import uuid4
import pytest
from src.events.store import EventStore
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, EventType, TargetType
from src.models.project import ProjectSpec
from src.planning.architect import ArchitecturePlanner
from src.workspace.workspace import Workspace


@pytest.fixture
def sample_spec():
    return ProjectSpec(
        id=uuid4(),
        name="todo-api",
        prompt="Basit bir yapılacaklar API'si",
        stack={"backend": "fastapi", "database": "sqlite", "test": "pytest"},
        targets=[TargetType.API],
    )


def test_architect_generates_docs_and_adr(tmp_path, sample_spec):
    ws = Workspace(tmp_path)
    store = EventStore(ws.events_path)
    planner = ArchitecturePlanner(ws, store)

    arch_content, adr_paths, g2_passed, decision = planner.plan_architecture(
        sample_spec,
        autonomy_level=AutonomyLevel.FULL,
    )

    # 1. Verify architecture.md content & path
    arch_file = ws.p2p_docs_dir / "architecture.md"
    assert arch_file.exists()
    assert "System Architecture: todo-api" in arch_content
    assert "## 2. Component Boundaries" in arch_content
    assert "## 4. API Endpoints" in arch_content

    # 2. Verify ADR
    assert len(adr_paths) >= 1
    assert adr_paths[0].exists()
    assert "ADR-001" in adr_paths[0].name

    # 3. Verify G2 Gate in FULL autonomy: auto-approved with decided_by=default (ADR-010 / docs/03 §5.3)
    assert g2_passed is True
    assert decision is not None
    assert decision.id == "DEC-G2"
    assert decision.decided_by == DecidedBy.DEFAULT
    assert decision.kind == DecisionKind.GATE

    # 4. Verify EventStore
    events = store.read_all()
    assert any(e.type == EventType.DECISION_RECORDED for e in events)


def test_architect_g2_guarded_and_explicit_approval(tmp_path, sample_spec):
    ws = Workspace(tmp_path)
    planner = ArchitecturePlanner(ws)

    # In guarded mode without explicit approval, G2 halts for human confirmation
    _, _, g2_passed, dec = planner.plan_architecture(
        sample_spec,
        autonomy_level=AutonomyLevel.GUARDED,
        approved_by_user=False,
    )
    assert g2_passed is False
    assert dec is None

    # With explicit approval
    _, _, g2_passed_approved, dec_approved = planner.plan_architecture(
        sample_spec,
        autonomy_level=AutonomyLevel.GUARDED,
        approved_by_user=True,
    )
    assert g2_passed_approved is True
    assert dec_approved is not None
    assert dec_approved.decided_by == DecidedBy.HUMAN
