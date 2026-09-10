"""Tests for State projection from event replay and Phase 1 Exit Criterion (docs/08 Faz 1)."""
from pathlib import Path
import pytest

from src.events.projector import StateManager, project_state
from src.events.store import EventStore
from src.models.enums import AutonomyLevel, EventType, GateStatus, RiskLevel, TaskStatus


def test_phase_1_exit_criterion_five_events_and_replay_idempotence(tmp_path: Path):
    """
    Phase 1 Exit Criterion:
    'Elle yazilmis 5 olaydan dogru state.json turetiliyor; surec oldurulup
    yeniden baslatildiginda ayni state cikiyor. Testler gercek model cagirmir.'
    """
    events_file = tmp_path / ".p2p" / "events.jsonl"
    state_file = tmp_path / ".p2p" / "state.json"

    store = EventStore(events_file)

    # 1. PROJECT_CREATED
    store.append(
        event_type=EventType.PROJECT_CREATED,
        payload={"name": "appointment-saas", "targets": ["web", "api"]},
    )

    # 2. RUN_STARTED
    store.append(
        event_type=EventType.RUN_STARTED,
        payload={"autonomy_level": "guarded"},
        run_id="run-001",
    )

    # 3. TASK_CREATED
    store.append(
        event_type=EventType.TASK_CREATED,
        payload={"risk": "high", "title": "Create appointments endpoint"},
        task_id="API-001",
        run_id="run-001",
    )

    # 4. TASK_STATE_CHANGED
    store.append(
        event_type=EventType.TASK_STATE_CHANGED,
        payload={"to": "RUNNING", "assigned_to": "gemini-local", "attempts": 1},
        task_id="API-001",
        run_id="run-001",
    )

    # 5. GATE_FINISHED
    store.append(
        event_type=EventType.GATE_FINISHED,
        payload={"gate": "unit", "status": "PASS", "exit_code": 0},
        task_id="API-001",
        run_id="run-001",
    )

    # Step A: Project state from the 5 events
    events = store.read_all()
    assert len(events) == 5

    state1 = project_state(events)

    # Assertions on derived state
    assert state1.project_name == "appointment-saas"
    assert state1.run_id == "run-001"
    assert state1.status == "RUNNING"
    assert state1.autonomy_level == AutonomyLevel.GUARDED
    assert "API-001" in state1.tasks

    task_state = state1.tasks["API-001"]
    assert task_state.id == "API-001"
    assert task_state.status == TaskStatus.RUNNING
    assert task_state.assigned_to == "gemini-local"
    assert task_state.risk == RiskLevel.HIGH
    assert task_state.attempts == 1
    assert task_state.gate_status.get("unit") == GateStatus.PASS
    assert state1.last_seq == 5

    # Step B: Save state to disk
    manager = StateManager(state_file)
    manager.save(state1)

    assert state_file.exists()

    # Step C: Simulate process kill and restart:
    # Completely fresh read of events from disk and state recreation
    fresh_store = EventStore(events_file)
    replayed_events = fresh_store.read_all()
    state2 = project_state(replayed_events)

    # Load previously saved state from disk
    loaded_state = manager.load()

    # Verify 100% equivalence
    assert state2.model_dump() == state1.model_dump()
    assert loaded_state.model_dump() == state1.model_dump()
