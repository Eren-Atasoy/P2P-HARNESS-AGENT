"""Deterministic MockRuntime for models-free testing and verification (docs/08 Faz 1)."""
from pathlib import Path
from typing import Callable, Optional

from src.models.enums import TaskOutcome
from src.models.result import AgentResult
from src.models.task import TaskContract
from src.runtime.base import HealthStatus, RuntimeAdapter, RuntimeDoctorResult, RuntimeFeatures


class MockRuntime(RuntimeAdapter):
    """Deterministic, token-free synthetic runtime for testing and state machines."""

    def __init__(
        self,
        default_outcome: TaskOutcome = TaskOutcome.COMPLETED,
        files_to_create: Optional[dict[str, str]] = None,
        custom_handler: Optional[Callable[[TaskContract, Path], AgentResult]] = None,
    ):
        self.default_outcome = default_outcome
        self.files_to_create = files_to_create or {}
        self.custom_handler = custom_handler
        self.invocations: list[tuple[TaskContract, Path]] = []

    def execute(self, contract: TaskContract, workspace: Path, run_id: Optional[str] = None) -> AgentResult:
        self.invocations.append((contract, workspace))

        if self.custom_handler:
            return self.custom_handler(contract, workspace)

        created_files = []
        for rel_path, content in self.files_to_create.items():
            full_path = workspace / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            created_files.append(rel_path.replace("\\", "/"))

        # Default simulated success
        return AgentResult(
            task_id=contract.id,
            run_id=run_id or "mock-run-001",
            outcome=self.default_outcome,
            summary=f"Mock execution of {contract.id}: {contract.title}",
            files_changed=created_files,
            criteria_addressed=[ac.id for ac in contract.acceptance_criteria],
            assumptions=["Simulated mock execution, no model called"],
            acr=None,
            failure_reason=None if self.default_outcome == TaskOutcome.COMPLETED else "Simulated mock failure",
        )

    def features(self) -> RuntimeFeatures:
        return RuntimeFeatures(
            can_stream=False,
            can_cancel=True,
            can_pause=True,
            can_resume=True,
            supports_structured_output=True,
            supports_subagents=True,
            supports_mcp=True,
            can_execute=True,
        )

    def health(self) -> HealthStatus:
        return HealthStatus.OK

    def doctor(self, connection_id: str = "mock-connection") -> RuntimeDoctorResult:
        return RuntimeDoctorResult(
            connection_id=connection_id,
            available=True,
            authenticated=True,
            can_read=True,
            can_write=True,
            can_execute=True,
            supports_structured_output=True,
            supports_cancellation=True,
            version="mock-1.0.0",
            latency_ms=1.5,
        )
