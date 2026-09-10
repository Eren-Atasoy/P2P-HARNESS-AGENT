"""Event model corresponding to .p2p/events.jsonl and docs/02 §7."""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import EventType


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int = Field(ge=1, description="Monotonically increasing integer sequence number")
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp")
    type: EventType
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
