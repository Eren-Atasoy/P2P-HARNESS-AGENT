"""PolicyEngine enforcing risk levels, autonomy modes, and human approval gates (docs/03 §5)."""
from typing import Optional
from src.models.decision import Decision
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, RiskLevel
from src.models.task import TaskContract


class PolicyEngine:
    """Enforces autonomy policies, risk controls, and human approval requirements."""

    @staticmethod
    def requires_human_approval(task: TaskContract, autonomy_level: AutonomyLevel) -> bool:
        """
        Determines whether human review/approval is required before merge.
        Binding rule (docs/03 §5.3 / ADR-010):
        'high risk is never auto-approved at any autonomy level.'
        """
        if task.human_approval:
            return True

        if task.risk == RiskLevel.HIGH:
            # high risk tasks ALWAYS require human approval, even in FULL autonomy!
            return True

        if autonomy_level == AutonomyLevel.SUPERVISED:
            # In supervised mode, both medium and high risk require human approval
            return task.risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)

        if autonomy_level == AutonomyLevel.GUARDED:
            # In guarded mode, only high risk requires human approval
            return task.risk == RiskLevel.HIGH

        # In FULL autonomy mode: low and medium are auto-approved, high is caught above
        return False

    @staticmethod
    def evaluate_project_gate(
        gate_name: str,
        autonomy_level: AutonomyLevel,
        question: str,
    ) -> tuple[bool, Optional[Decision]]:
        """
        Evaluates project gates (G1, G2, G3, G4).
        Returns (auto_approved, Decision_if_auto_approved).
        """
        if autonomy_level == AutonomyLevel.FULL:
            # G2 and G4 auto-approved in FULL mode, but recorded with decided_by=default!
            dec = Decision(
                id=f"DEC-{gate_name}",
                question=question,
                options=["Approve", "Reject"],
                chosen="Approve",
                rationale="Auto-approved by policy engine under FULL autonomy mode.",
                decided_by=DecidedBy.DEFAULT,
                kind=DecisionKind.GATE,
            )
            return True, dec

        # Supervised and Guarded require explicit human confirmation
        return False, None
