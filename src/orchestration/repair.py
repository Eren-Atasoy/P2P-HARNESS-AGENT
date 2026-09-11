"""Failure classification, circuit breaker, and repair planning (docs/03 §3)."""
import hashlib
from enum import Enum
from typing import Optional

from src.models.enums import GateStatus
from src.models.result import AgentResult, Failure, GateResult, ReviewResult
from src.models.task import TaskContract


class FailureClass(str, Enum):
    SYNTAX = "SYNTAX"
    TEST_FAIL = "TEST_FAIL"
    CONTRACT = "CONTRACT"
    POLICY = "POLICY"
    ENV = "ENV"
    ARCH = "ARCH"
    QUOTA = "QUOTA"
    UNKNOWN = "UNKNOWN"


class RepairPlanner:
    """Classifies verification failures and decides recovery vs escalation."""

    def __init__(self):
        # Maps task_id -> last failure signature hash
        self._history: dict[str, str] = {}

    @staticmethod
    def classify_gate_failure(gate_result: GateResult) -> FailureClass:
        """Determines the operational failure class according to docs/03 §3."""
        if gate_result.status == GateStatus.ERROR:
            # Missing tool, docker failure, system timeout -> ENV
            return FailureClass.ENV

        gate_name = gate_result.gate.lower()
        if "lint" in gate_name or "typecheck" in gate_name:
            return FailureClass.SYNTAX
        if "test" in gate_name or "unit" in gate_name or "integration" in gate_name or "smoke" in gate_name or "e2e" in gate_name:
            return FailureClass.TEST_FAIL
        if "policy" in gate_name:
            return FailureClass.POLICY

        return FailureClass.UNKNOWN

    @classmethod
    def classify_failure(cls, gate_results: list[GateResult]) -> FailureClass:
        """Classifies a list of gate results, returning the highest priority failure class."""
        for gr in gate_results:
            fc = cls.classify_gate_failure(gr)
            if fc != FailureClass.UNKNOWN:
                return fc
        return FailureClass.UNKNOWN

    @staticmethod
    def compute_failure_signature(failures: list[Failure]) -> str:
        """Produces a deterministic hash of the failures to detect zero progress (docs/03 §3.2)."""
        tokens = []
        for f in failures:
            tokens.append(f"{f.file}:{f.line}:{f.rule}:{f.message.strip()}")
        tokens.sort()
        raw = "|".join(tokens)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_stuck(self, task_id: str, failures: list[Failure]) -> bool:
        """Returns True if the identical failure signature was observed in the previous attempt."""
        if not failures:
            return False
        sig = self.compute_failure_signature(failures)
        last_sig = self._history.get(task_id)
        self._history[task_id] = sig
        return last_sig is not None and last_sig == sig

    def should_enter_fix_loop(
        self,
        task: TaskContract,
        attempt: int,
        gate_results: list[GateResult],
        review: Optional[ReviewResult] = None,
    ) -> tuple[bool, FailureClass, str]:
        """Evaluates whether to retry in a fix loop or escalate to human (docs/03 §3).

        Returns: (should_retry, failure_class, reason)
        """
        # 1. Max attempts reached
        if attempt >= task.max_attempts:
            return False, FailureClass.UNKNOWN, f"Max attempts ({task.max_attempts}) exhausted"

        # 2. Check gate results
        all_failures: list[Failure] = []
        for gr in gate_results:
            f_class = self.classify_gate_failure(gr)
            if f_class == FailureClass.ENV:
                # ENV errors NEVER enter fix loop -> straight to ESCALATED
                return False, FailureClass.ENV, f"Environment/tooling error in gate '{gr.gate}'"

            if gr.failures:
                all_failures.extend(gr.failures)

        # 3. Check progress stuck (identical failure signature twice)
        if all_failures and self.is_stuck(task.id, all_failures):
            return False, FailureClass.TEST_FAIL, "Repeated identical gate failure signature (zero progress)"

        # 4. Review rejection
        if review and review.verdict.value == "rejected":
            return False, FailureClass.ARCH, "Task rejected by architectural review"

        # Ready for fix loop
        primary_class = FailureClass.TEST_FAIL if all_failures else FailureClass.UNKNOWN
        return True, primary_class, "Quality gates failed, scheduling fix attempt"
