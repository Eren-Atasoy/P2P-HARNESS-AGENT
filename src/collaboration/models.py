"""Data models for collaboration, issues, and PR management (docs/07 §7)."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PRStatus(str, Enum):
    OPEN = "OPEN"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


class PRType(str, Enum):
    TASK = "TASK"
    RELEASE = "RELEASE"


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Issue identifier e.g. ISSUE-001 or #42")
    title: str
    body: str
    severity: IssueSeverity = Field(default=IssueSeverity.HIGH)
    labels: list[str] = Field(default_factory=list)
    status: IssueStatus = Field(default=IssueStatus.OPEN)
    task_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = Field(default=None)
    html_url: Optional[str] = Field(default=None)


class PullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="Pull request number")
    title: str
    body: str
    head_branch: str
    base_branch: str
    status: PRStatus = Field(default=PRStatus.OPEN)
    pr_type: PRType = Field(default=PRType.TASK)
    task_id: Optional[str] = Field(default=None)
    issue_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    merged_at: Optional[datetime] = Field(default=None)
    html_url: Optional[str] = Field(default=None)
