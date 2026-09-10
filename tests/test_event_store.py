"""Tests for EventStore append-only persistence and sequence monotonicity."""
import json
from pathlib import Path
import pytest

from src.events.store import EventStore
from src.models.enums import EventType


def test_event_store_sequential_monotonicity(tmp_path: Path):
    events_file = tmp_path / "events.jsonl"
    store = EventStore(events_file)

    assert store.last_seq() == 0

    ev1 = store.append(
        event_type=EventType.PROJECT_CREATED,
        payload={"name": "test-app"},
    )
    assert ev1.seq == 1
    assert store.last_seq() == 1

    ev2 = store.append(
        event_type=EventType.RUN_STARTED,
        payload={"autonomy_level": "guarded"},
        run_id="run-1",
    )
    assert ev2.seq == 2
    assert store.last_seq() == 2

    ev3 = store.append(
        event_type=EventType.TASK_CREATED,
        payload={"risk": "high"},
        task_id="API-001",
        run_id="run-1",
    )
    assert ev3.seq == 3
    assert store.last_seq() == 3

    # Verify read_all retrieves all events with matching contents
    all_events = store.read_all()
    assert len(all_events) == 3
    assert [e.seq for e in all_events] == [1, 2, 3]
    assert all_events[0].type == EventType.PROJECT_CREATED
    assert all_events[1].type == EventType.RUN_STARTED
    assert all_events[2].type == EventType.TASK_CREATED


def test_event_store_reopen_persists_sequence(tmp_path: Path):
    events_file = tmp_path / "events.jsonl"
    store1 = EventStore(events_file)
    store1.append(EventType.PROJECT_CREATED, {"name": "app"})

    # Open fresh instance
    store2 = EventStore(events_file)
    assert store2.last_seq() == 1

    ev2 = store2.append(EventType.RUN_STARTED, {}, run_id="r1")
    assert ev2.seq == 2
