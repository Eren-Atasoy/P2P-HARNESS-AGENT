"""Decision model corresponding to docs/02 §6."""
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import DecidedBy, DecisionKind


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="e.g. DEC-001")
    question: str
    options: list[str] = Field(default_factory=list)
    chosen: str
    rationale: str
    decided_by: DecidedBy = Field(default=DecidedBy.HUMAN)
    kind: DecisionKind = Field(default=DecisionKind.AMBIGUITY)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
