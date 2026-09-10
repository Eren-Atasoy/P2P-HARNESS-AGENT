"""Connection model corresponding to docs/04 §2."""
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import AutomationPolicy, Capability, ConnectionKind, CostTier, HealthStatus, RuntimeType


class Connection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique connection identifier, e.g. claude-pro-local")
    kind: ConnectionKind
    runtime: RuntimeType
    credential_ref: str = Field(description="Pointer, never the actual secret (docs/04 §2, docs/06 §4)")
    capabilities: list[Capability] = Field(default_factory=list)
    quality: dict[str, float] = Field(default_factory=dict, description="Score 0.0-1.0 per capability")
    limits: dict[str, Any] = Field(default_factory=dict, description="concurrency, daily_runs, rpm, etc.")
    cost_tier: CostTier = Field(default=CostTier.FREE)
    automation_policy: AutomationPolicy = Field(default=AutomationPolicy.UNKNOWN)
    health: HealthStatus = Field(default=HealthStatus.OK)
