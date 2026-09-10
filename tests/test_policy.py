"""Tests for PolicyEngine risk rules and autonomy mode gates."""
import pytest
from src.models import (
    AcceptanceCriterion,
    AutonomyLevel,
    Capability,
    DecidedBy,
    EstimatedSize,
    RiskLevel,
    TaskContract,
    VerifiedBy,
)
from src.orchestration.policy import PolicyEngine


def make_task_with_risk(risk: RiskLevel) -> TaskContract:
    return TaskContract(
        id="TSK-001",
        title="Test task",
        capabilities=[Capability.BACKEND],
        risk=risk,
        intent="Intent",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Verified",
                verified_by=VerifiedBy.TEST,
                test_ref="tests/test_a.py::test_x",
            )
        ],
        inputs=["docs/01"],
        allowed_paths=["src/**"],
        forbidden_paths=[],
        gates=["lint"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )


def test_high_risk_never_auto_approves_even_in_full_autonomy():
    # Binding rule ADR-010 / docs/03 §5.3
    task_high = make_task_with_risk(RiskLevel.HIGH)

    assert PolicyEngine.requires_human_approval(task_high, AutonomyLevel.SUPERVISED) is True
    assert PolicyEngine.requires_human_approval(task_high, AutonomyLevel.GUARDED) is True
    assert PolicyEngine.requires_human_approval(task_high, AutonomyLevel.FULL) is True


def test_low_risk_auto_approves_in_guarded_and_full():
    task_low = make_task_with_risk(RiskLevel.LOW)

    assert PolicyEngine.requires_human_approval(task_low, AutonomyLevel.SUPERVISED) is False
    assert PolicyEngine.requires_human_approval(task_low, AutonomyLevel.GUARDED) is False
    assert PolicyEngine.requires_human_approval(task_low, AutonomyLevel.FULL) is False


def test_medium_risk_requires_approval_only_in_supervised():
    task_med = make_task_with_risk(RiskLevel.MEDIUM)

    assert PolicyEngine.requires_human_approval(task_med, AutonomyLevel.SUPERVISED) is True
    assert PolicyEngine.requires_human_approval(task_med, AutonomyLevel.GUARDED) is False
    assert PolicyEngine.requires_human_approval(task_med, AutonomyLevel.FULL) is False


def test_project_gate_auto_approval_logs_decision_with_decided_by_default():
    auto_appr, dec = PolicyEngine.evaluate_project_gate("G2", AutonomyLevel.FULL, "Architecture approval?")
    assert auto_appr is True
    assert dec is not None
    assert dec.decided_by == DecidedBy.DEFAULT
