"""AgentResult, GateResult, and ReviewResult models corresponding to docs/02 §3, §4, §5."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import FindingSeverity, GateStatus, ReviewVerdict, TaskOutcome


class AgentResult(BaseModel):
    # Rule C4 (docs/02 §3): extra="ignore" so extra fields don't invalidate a task result
    model_config = ConfigDict(extra="ignore")

    task_id: str
    run_id: str
    outcome: TaskOutcome
    summary: str = Field(description="Summary of work performed (<= 5 lines recommended)")
    files_changed: list[str] = Field(default_factory=list)
    criteria_addressed: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    acr: Optional[str] = None
    failure_reason: Optional[str] = None


class GateFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: Optional[str] = None
    line: Optional[int] = None
    rule: Optional[str] = None
    message: str


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate: str
    status: GateStatus
    exit_code: int
    duration_ms: int
    log_path: str
    failures: list[GateFailure] = Field(default_factory=list)


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: FindingSeverity
    file: str
    line: Optional[int] = None
    issue: str
    suggestion: str


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    attempt: int
    verdict: ReviewVerdict
    findings: list[ReviewFinding] = Field(default_factory=list)
    architecture_compliance: bool = True

    @staticmethod
    def calculate_verdict(findings: list[ReviewFinding]) -> ReviewVerdict:
        """Determines review verdict deterministically per docs/02 §5 rules."""
        sevs = {f.severity for f in findings}
        if FindingSeverity.CRITICAL in sevs:
            return ReviewVerdict.REJECTED
        if FindingSeverity.HIGH in sevs:
            return ReviewVerdict.CHANGES_REQUESTED
        return ReviewVerdict.APPROVED
