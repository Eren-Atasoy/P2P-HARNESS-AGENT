"""Tests for TaskStateMachine transitions and ProgressTracker."""
import pytest
from src.models.enums import TaskStatus
from src.orchestration.state_machine import (
    InvalidTransitionError,
    ProgressTracker,
    TaskStateMachine,
)


def test_valid_transitions():
    sm = TaskStateMachine()
    sm.validate_transition(TaskStatus.PENDING, TaskStatus.READY)
    sm.validate_transition(TaskStatus.READY, TaskStatus.RUNNING)
    sm.validate_transition(TaskStatus.RUNNING, TaskStatus.GATED)
    sm.validate_transition(TaskStatus.GATED, TaskStatus.APPROVED)
    sm.validate_transition(TaskStatus.APPROVED, TaskStatus.MERGED)


def test_invalid_transition_raises():
    sm = TaskStateMachine()
    # Cannot jump from PENDING directly to MERGED!
    with pytest.raises(InvalidTransitionError):
        sm.validate_transition(TaskStatus.PENDING, TaskStatus.MERGED)

    # Cannot jump from RUNNING directly to MERGED (must pass GATED verification!)
    with pytest.raises(InvalidTransitionError):
        sm.validate_transition(TaskStatus.RUNNING, TaskStatus.MERGED)


def test_progress_tracker_detects_identical_consecutive_failures():
    tracker = ProgressTracker()
    task_id = "API-001"

    # First failure
    stuck = tracker.record_and_check_stuck(task_id, "SyntaxError on line 42")
    assert stuck is False

    # Second failure with different error -> not stuck
    stuck = tracker.record_and_check_stuck(task_id, "TypeError on line 12")
    assert stuck is False

    # Third failure with exact same error as second -> STUCK!
    stuck = tracker.record_and_check_stuck(task_id, "TypeError on line 12")
    assert stuck is True
