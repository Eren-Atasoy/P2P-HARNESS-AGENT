"""Base RuntimeAdapter abstract contract from docs/04 §4."""
from abc import ABC, abstractmethod
from pathlib import Path

from src.models.result import AgentResult
from src.models.task import TaskContract


class RuntimeAdapter(ABC):
    """Abstract base class for running an agent execution against a TaskContract."""

    @abstractmethod
    def execute(self, contract: TaskContract, workspace: Path) -> AgentResult:
        """Executes a task within the given workspace and returns the AgentResult."""
        pass
