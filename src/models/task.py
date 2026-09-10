"""TaskContract and AcceptanceCriterion models corresponding to .p2p/tasks/<id>.json."""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.enums import Capability, EstimatedSize, RiskLevel, VerifiedBy


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="e.g. AC-1")
    statement: str = Field(description="Observable behavior requirement")
    verified_by: VerifiedBy = Field(description="test | gate | manual")
    test_ref: Optional[str] = Field(default=None, description="test_file::test_name if verified_by=test")
    gate_ref: Optional[str] = Field(default=None, description="gate name if verified_by=gate")

    @model_validator(mode="after")
    def validate_refs(self) -> "AcceptanceCriterion":
        if self.verified_by == VerifiedBy.TEST and not self.test_ref:
            raise ValueError("test_ref is required when verified_by='test'")
        if self.verified_by == VerifiedBy.GATE and not self.gate_ref:
            raise ValueError("gate_ref is required when verified_by='gate'")
        return self


class TaskContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Z0-9_]+-[0-9]{3}$", description="e.g. API-001 or FE-001")
    title: str = Field(description="Single line imperative command")
    capabilities: list[Capability] = Field(min_length=1, description="All required capabilities")
    risk: RiskLevel = Field(description="low | medium | high")
    depends_on: list[str] = Field(default_factory=list, description="List of prerequisite task IDs")
    intent: str = Field(description="2-5 sentences: what and why, without implementation details")
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1, description="At least one criterion")
    inputs: list[str] = Field(description="Files and specifications the agent must read")
    allowed_paths: list[str] = Field(description="POSIX globs the agent may modify")
    forbidden_paths: list[str] = Field(description="POSIX globs strictly forbidden (overrides allowed)")
    gates: list[str] = Field(description="Quality gates to execute upon completion")
    estimated_size: EstimatedSize = Field(description="S | M | L (L must be split)")
    max_attempts: int = Field(default=3, ge=1, le=10)
    human_approval: bool = Field(default=False)
    result_path: str = Field(description="Path where AgentResult must be written")
    acr_path: str = Field(description="Path where Architecture Change Request must be written if needed")
    notes: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_manual_approval_and_rules(self) -> "TaskContract":
        has_manual = any(ac.verified_by == VerifiedBy.MANUAL for ac in self.acceptance_criteria)
        if has_manual and not self.human_approval:
            raise ValueError("Task with verified_by='manual' acceptance criterion must have human_approval=True (docs/02 §2.1)")
        return self
