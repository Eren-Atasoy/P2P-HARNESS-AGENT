"""Derived state models projected from event stream (.p2p/state.json)."""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.models.decision import Decision
from src.models.enums import AutonomyLevel, GateStatus, RiskLevel, TaskStatus


class TaskSummaryState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    attempts: int = 0
    risk: RiskLevel = RiskLevel.LOW
    gate_status: dict[str, GateStatus] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    acr: Optional[str] = None


class State(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: Optional[str] = None
    project_name: Optional[str] = None
    status: str = "IDLE"
    autonomy_level: AutonomyLevel = AutonomyLevel.GUARDED
    tasks: dict[str, TaskSummaryState] = Field(default_factory=dict)
    decisions: list[Decision] = Field(default_factory=list)
    last_seq: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
