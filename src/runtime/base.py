"""Base RuntimeAdapter abstract contract from docs/04 §4."""
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from src.models.result import AgentResult
from src.models.task import TaskContract


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


class RuntimeFeatures(BaseModel):
    """Declared capabilities of a runtime adapter (docs/04 §4)."""
    can_stream: bool = False
    can_cancel: bool = True
    can_pause: bool = False
    can_resume: bool = False
    supports_structured_output: bool = True
    supports_subagents: bool = False
    supports_mcp: bool = False
    can_execute: bool = True


class RuntimeDoctorResult(BaseModel):
    """Health check and capability verification proof (docs/04 §4 RuntimeDoctor)."""
    connection_id: str
    available: bool
    authenticated: bool
    can_read: bool = True
    can_write: bool = True
    can_execute: bool = True
    supports_structured_output: bool = True
    supports_cancellation: bool = True
    version: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class RuntimeAdapter(ABC):
    """Abstract base class for running an agent execution against a TaskContract."""

    @abstractmethod
    def execute(self, contract: TaskContract, workspace: Path, run_id: Optional[str] = None) -> AgentResult:
        """Executes a task within the given workspace and returns the AgentResult."""
        pass

    def features(self) -> RuntimeFeatures:
        """Returns the features supported by this runtime."""
        return RuntimeFeatures()

    def health(self) -> HealthStatus:
        """Returns the current connection health."""
        return HealthStatus.OK

    def doctor(self, connection_id: str = "default") -> RuntimeDoctorResult:
        """Runs diagnostics and returns proof of operational health."""
        return RuntimeDoctorResult(
            connection_id=connection_id,
            available=True,
            authenticated=True,
        )
