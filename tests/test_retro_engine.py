"""Unit tests for RetroEngine and p2p retro CLI (Faz 8)."""
from pathlib import Path
from typer.testing import CliRunner

from src.cli.main import app
from src.events.store import EventStore
from src.models.enums import EventType
from src.models.event import Event
from src.orchestration.retro import RetroEngine
from src.workspace.workspace import Workspace

runner = CliRunner()


def test_retro_engine_pattern_detection(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    store = EventStore(ws.events_path)

    # 1. Simulate 3 identical gate failures across different tasks
    store.append(event_type=EventType.GATE_FINISHED, task_id="TASK-001", payload={"gate": "unit", "status": "FAIL", "failures": "AssertionError: 401 != 200"})
    store.append(event_type=EventType.GATE_FINISHED, task_id="TASK-002", payload={"gate": "unit", "status": "FAIL", "failures": "AssertionError: 401 != 200"})
    store.append(event_type=EventType.GATE_FINISHED, task_id="TASK-003", payload={"gate": "unit", "status": "FAIL", "failures": "AssertionError: 401 != 200"})

    # 2. Simulate 3 review findings with same category
    store.append(event_type=EventType.REVIEW_FINISHED, task_id="TASK-001", payload={"findings": [{"category": "security"}]})
    store.append(event_type=EventType.REVIEW_FINISHED, task_id="TASK-002", payload={"findings": [{"category": "security"}]})
    store.append(event_type=EventType.REVIEW_FINISHED, task_id="TASK-003", payload={"findings": [{"category": "security"}]})

    # 3. Simulate 2 consecutive escalations on same capability
    store.append(event_type=EventType.ESCALATED, task_id="TASK-004", payload={"capability": "browser"})
    store.append(event_type=EventType.ESCALATED, task_id="TASK-005", payload={"capability": "browser"})

    # 4. Simulate 2 ACR events
    store.append(event_type=EventType.ACR_OPENED, task_id="TASK-006", payload={"acr_id": "ACR-001"})
    store.append(event_type=EventType.ACR_OPENED, task_id="TASK-007", payload={"acr_id": "ACR-002"})

    events = store.read_all()
    engine = RetroEngine(ws, store)
    recommendations = engine.analyze_events(events)

    assert len(recommendations) == 4
    kinds = [r.kind for r in recommendations]
    assert "GATE" in kinds
    assert "RULE" in kinds
    assert "ROUTER" in kinds
    assert "DOCS" in kinds

    # Test apply recommendation
    rec_gate = [r for r in recommendations if r.kind == "GATE"][0]
    applied = engine.apply_recommendation(rec_gate)
    assert applied is True

    # Verify event recorded
    updated_events = store.read_all()
    retro_events = [e for e in updated_events if e.type == EventType.RETRO_APPLIED]
    assert len(retro_events) == 1
    assert retro_events[0].payload["rec_id"] == rec_gate.id


def test_retro_cli(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    store = EventStore(ws.events_path)

    for i in range(3):
        store.append(event_type=EventType.GATE_FINISHED, task_id=f"TASK-00{i}", payload={"gate": "lint", "status": "FAIL", "failures": "E501 line too long"})

    # CLI retro list
    res_list = runner.invoke(app, ["retro", "--workspace", str(tmp_path)])
    assert res_list.exit_code == 0
    assert "REC-001" in res_list.stdout
    assert "GATE" in res_list.stdout

    # CLI retro apply
    res_apply = runner.invoke(app, ["retro", "--workspace", str(tmp_path), "--apply", "REC-001"])
    assert res_apply.exit_code == 0
    assert "Successfully applied REC-001" in res_apply.stdout
