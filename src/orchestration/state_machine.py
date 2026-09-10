"""Task state machine transitions and progress tracking (docs/03 §1 & §3)."""
import hashlib
from typing import Any, Optional
from src.models.enums import TaskStatus


class InvalidTransitionError(Exception):
    """Raised when attempting an unauthorized state transition."""
    pass


# Valid direct transitions map
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.READY, TaskStatus.ESCALATED, TaskStatus.PAUSED, TaskStatus.UNROUTABLE},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.ESCALATED, TaskStatus.UNROUTABLE},
    TaskStatus.RUNNING: {
        TaskStatus.GATED,       # VERIFYING
        TaskStatus.BLOCKED,     # ACR
        TaskStatus.FAILED,
        TaskStatus.PAUSED,
        TaskStatus.ESCALATED,
    },
    TaskStatus.GATED: {
        TaskStatus.APPROVED,    # Passed gates & review
        TaskStatus.FIXING,       # Failed gates, retry attempt
        TaskStatus.ESCALATED,   # ERROR in gates or max attempts reached
        TaskStatus.PAUSED,
    },
    TaskStatus.FIXING: {
        TaskStatus.READY,       # Ready for fix round
        TaskStatus.ESCALATED,
        TaskStatus.PAUSED,
    },
    TaskStatus.APPROVED: {
        TaskStatus.MERGED,      # Merged into integration
        TaskStatus.ESCALATED,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.READY,       # ACR resolved
        TaskStatus.ESCALATED,
    },
    TaskStatus.PAUSED: {
        TaskStatus.READY,       # Quota resumed or rerouted
        TaskStatus.ESCALATED,
    },
    TaskStatus.FAILED: {
        TaskStatus.ESCALATED,
    },
    TaskStatus.UNROUTABLE: {
        TaskStatus.ESCALATED,
    },
    TaskStatus.ESCALATED: {
        TaskStatus.READY,       # Human steered/fixed
    },
    TaskStatus.MERGED: set(),   # Terminal state (DONE)
}


class ProgressTracker:
    """Detects repeated identical failures across consecutive attempts (docs/03 §3.2)."""

    def __init__(self):
        self._last_failure_hashes: dict[str, str] = {}

    @staticmethod
    def hash_failure(failure_payload: Any) -> str:
        s = str(failure_payload).strip().encode("utf-8")
        return hashlib.sha256(s).hexdigest()

    def record_and_check_stuck(self, task_id: str, failure_payload: Any) -> bool:
        """
        Records failure and returns True if this is the exact same failure
        as the immediately preceding attempt (indicating no progress).
        """
        curr_hash = self.hash_failure(failure_payload)
        prev_hash = self._last_failure_hashes.get(task_id)
        self._last_failure_hashes[task_id] = curr_hash

        if prev_hash is not None and prev_hash == curr_hash:
            return True  # Identical consecutive failure -> stuck!

        return False

    def clear(self, task_id: str):
        self._last_failure_hashes.pop(task_id, None)


class TaskStateMachine:
    """Manages and validates task state transitions."""

    def __init__(self):
        self.tracker = ProgressTracker()

    @staticmethod
    def validate_transition(from_status: TaskStatus, to_status: TaskStatus):
        if to_status == from_status:
            return
        allowed = VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition from {from_status.value} to {to_status.value}. Allowed: {[s.value for s in allowed]}"
            )
