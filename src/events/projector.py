"""State projector: projects State from event stream replay (.p2p/state.json)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from src.models.decision import Decision
from src.models.enums import AutonomyLevel, EventType, GateStatus, RiskLevel, TaskStatus
from src.models.event import Event
from src.models.state import State, TaskSummaryState


def project_state(events: Iterable[Event], initial_state: Optional[State] = None) -> State:
    """Deterministically projects the current State by replaying the given events."""
    state = initial_state or State()

    for ev in events:
        state.last_seq = ev.seq
        state.updated_at = ev.ts

        if ev.type == EventType.PROJECT_CREATED:
            state.project_name = ev.payload.get("name")
        elif ev.type == EventType.RUN_STARTED:
            state.run_id = ev.run_id
            state.status = "RUNNING"
            if "autonomy_level" in ev.payload:
                state.autonomy_level = AutonomyLevel(ev.payload["autonomy_level"])
        elif ev.type == EventType.RUN_FINISHED:
            state.status = ev.payload.get("status", "COMPLETED")
        elif ev.type == EventType.TASK_CREATED:
            if ev.task_id:
                risk_val = ev.payload.get("risk", RiskLevel.LOW)
                risk = RiskLevel(risk_val) if isinstance(risk_val, str) else risk_val
                state.tasks[ev.task_id] = TaskSummaryState(
                    id=ev.task_id,
                    status=TaskStatus.PENDING,
                    risk=risk,
                )
        elif ev.type == EventType.TASK_STATE_CHANGED:
            if ev.task_id and ev.task_id in state.tasks:
                task = state.tasks[ev.task_id]
                to_status = ev.payload.get("to")
                if to_status:
                    task.status = TaskStatus(to_status) if isinstance(to_status, str) else to_status
                if "assigned_to" in ev.payload:
                    task.assigned_to = ev.payload["assigned_to"]
                if "attempts" in ev.payload:
                    task.attempts = int(ev.payload["attempts"])
                elif "attempt" in ev.payload:
                    task.attempts = int(ev.payload["attempt"])
        elif ev.type == EventType.GATE_FINISHED:
            if ev.task_id and ev.task_id in state.tasks:
                gate_name = ev.payload.get("gate", "unknown")
                gate_status_val = ev.payload.get("status", GateStatus.PASS)
                gate_status = GateStatus(gate_status_val) if isinstance(gate_status_val, str) else gate_status_val
                state.tasks[ev.task_id].gate_status[gate_name] = gate_status
        elif ev.type == EventType.DECISION_RECORDED:
            decision_data = ev.payload.get("decision", ev.payload)
            try:
                dec = Decision.model_validate(decision_data)
                state.decisions.append(dec)
            except Exception:
                pass
        elif ev.type == EventType.ACR_OPENED:
            if ev.task_id and ev.task_id in state.tasks:
                state.tasks[ev.task_id].acr = ev.payload.get("acr_path")
                state.tasks[ev.task_id].status = TaskStatus.BLOCKED
        elif ev.type == EventType.ESCALATED:
            if ev.task_id and ev.task_id in state.tasks:
                state.tasks[ev.task_id].status = TaskStatus.ESCALATED
        elif ev.type == EventType.MERGE_COMPLETED:
            if ev.task_id and ev.task_id in state.tasks:
                state.tasks[ev.task_id].status = TaskStatus.MERGED

    return state


class StateManager:
    """Manages writing and reading the projected state.json in workspace."""

    def __init__(self, state_path: Path):
        self.state_path = Path(state_path)

    def save(self, state: State):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        # atomic write
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        tmp_path.replace(self.state_path)

    def load(self) -> Optional[State]:
        if not self.state_path.exists():
            return None
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return State.model_validate(data)
        except Exception:
            return None
