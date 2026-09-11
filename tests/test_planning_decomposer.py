"""Unit tests for TaskDecomposer (Faz 6)."""
from uuid import uuid4
import pytest
from src.events.store import EventStore
from src.models.enums import AutonomyLevel, EstimatedSize, EventType, RiskLevel, TargetType
from src.models.project import ProjectSpec
from src.planning.decomposer import TaskDecomposer
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


def test_derive_risk_rules():
    # High risk rules (docs/03 §5.1: auth, token, secrets, destructive migrations)
    assert TaskDecomposer.derive_risk("Implement JWT auth", "Issue tokens", ["app/auth.py"]) == RiskLevel.HIGH
    assert TaskDecomposer.derive_risk("Database migration drop column", "Run migration", ["db/migrations"]) == RiskLevel.HIGH
    assert TaskDecomposer.derive_risk("Manage API secrets", "Save credentials", ["config.py"]) == RiskLevel.HIGH

    # Medium risk rules (business logic, endpoints, models, schemas)
    assert TaskDecomposer.derive_risk("Create Item model", "Define Pydantic schema", ["app/models.py"]) == RiskLevel.MEDIUM
    assert TaskDecomposer.derive_risk("Implement CRUD", "Database queries", ["app/crud.py"]) == RiskLevel.MEDIUM
    assert TaskDecomposer.derive_risk("Mount API endpoints", "Handle HTTP requests", ["app/main.py"]) == RiskLevel.MEDIUM

    # Low risk rules (docs, formatting, styling)
    assert TaskDecomposer.derive_risk("Write README", "Project documentation", ["README.md"]) == RiskLevel.LOW
    assert TaskDecomposer.derive_risk("Format code", "Run linter", ["app/**"]) == RiskLevel.LOW


def test_decomposer_generates_valid_dag_and_tasks(tmp_path, sample_spec):
    ws = Workspace(tmp_path)
    store = EventStore(ws.events_path)
    decomposer = TaskDecomposer(ws, store)

    graph, g3_passed, g3_decision = decomposer.decompose(
        sample_spec,
        autonomy_level=AutonomyLevel.GUARDED,
    )

    # 1. Verify G3 Gate passed in guarded mode
    assert g3_passed is True
    assert g3_decision is not None
    assert g3_decision.id == "DEC-G3"

    # 2. Verify graph validity and wave computation
    assert len(graph.tasks) >= 3
    graph.validate()  # No cycle, no missing dependencies
    waves = graph.compute_waves()
    assert len(waves) >= 2  # Sequential dependencies produce multiple waves

    # 3. Check every task adheres to contract invariants
    for tid, task in graph.tasks.items():
        # Task file exists on disk
        task_file = ws.tasks_dir / f"{tid}.json"
        assert task_file.exists()

        # Invariant: Size must be S or M, never L (ADR/spec invariant)
        assert task.estimated_size in (EstimatedSize.S, EstimatedSize.M)
        assert task.estimated_size != EstimatedSize.L

        # Invariant: At least 1 acceptance criterion
        assert len(task.acceptance_criteria) >= 1

        # Invariant: Strict path scopes
        assert len(task.allowed_paths) >= 1
        assert ".p2p/**" in task.forbidden_paths or ".p2p/**" in str(task.forbidden_paths)

    # 4. Verify EventStore contains TASK_CREATED events
    events = store.read_all()
    created_events = [e for e in events if e.type == EventType.TASK_CREATED]
    assert len(created_events) == len(graph.tasks)
