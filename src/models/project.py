"""ProjectSpec model corresponding to .p2p/project.json."""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import TargetType


class ProjectSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(description="Kebab-case project name")
    prompt: str = Field(description="Original user prompt without modification")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    p2p_version: str = Field(default="0.1.0", description="Generating P2P semver")
    stack: dict[str, Any] = Field(default_factory=dict, description="Chosen technology stack")
    decisions: list[dict[str, Any]] = Field(default_factory=list, description="Recorded human/default decisions")
    targets: list[TargetType] = Field(default_factory=lambda: [TargetType.WEB, TargetType.API])
