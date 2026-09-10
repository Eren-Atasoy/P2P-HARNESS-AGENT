"""Boundary and validation tests for all Pydantic core models."""
import pytest
from pydantic import ValidationError

from src.models import (
    AcceptanceCriterion,
    AgentResult,
    AutonomyLevel,
    Capability,
    Connection,
    ConnectionKind,
    Decision,
    DecisionKind,
    EstimatedSize,
    Event,
    EventType,
    FindingSeverity,
    GateFailure,
    GateResult,
    GateStatus,
    ProjectSpec,
    ReviewFinding,
    ReviewResult,
    ReviewVerdict,
    RiskLevel,
    RuntimeType,
    TaskContract,
    TaskOutcome,
    VerifiedBy,
)


def test_project_spec_valid():
    spec = ProjectSpec(
        name="test-project",
        prompt="Build a verified api",
        stack={"backend": {"language": "python"}},
    )
    assert spec.name == "test-project"
    assert "backend" in spec.stack


def test_project_spec_extra_forbidden():
    with pytest.raises(ValidationError):
        ProjectSpec(
            name="test-project",
            prompt="Build a verified api",
            bogus_field="not allowed",
        )


def test_task_contract_valid():
    contract = TaskContract(
        id="API-001",
        title="Implement appointments CRUD",
        capabilities=[Capability.BACKEND, Capability.SECURITY],
        risk=RiskLevel.HIGH,
        intent="Appointment CRUD with tenant ownership verification.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="POST /appointments returns 201 with id",
                verified_by=VerifiedBy.TEST,
                test_ref="tests/api/test_appointments.py::test_create",
            )
        ],
        inputs=[".p2p/docs/api-contract.md"],
        allowed_paths=["backend/api/**"],
        forbidden_paths=["backend/models/**", "tests/**"],
        gates=["lint", "unit"],
        estimated_size=EstimatedSize.M,
        result_path=".p2p/runs/run-1/result.json",
        acr_path=".p2p/acr/",
    )
    assert contract.id == "API-001"
    assert contract.risk == RiskLevel.HIGH


def test_task_contract_manual_ac_requires_human_approval():
    # Rule docs/02 §2.1: verified_by=manual requires human_approval=True
    with pytest.raises(ValidationError, match="human_approval=True"):
        TaskContract(
            id="UI-001",
            title="Design landing visual layout",
            capabilities=[Capability.UI],
            risk=RiskLevel.LOW,
            intent="Layout visual polish.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="AC-1",
                    statement="Visual aesthetic matches brand design",
                    verified_by=VerifiedBy.MANUAL,
                )
            ],
            inputs=["docs/12"],
            allowed_paths=["frontend/**"],
            forbidden_paths=["backend/**"],
            gates=["lint"],
            estimated_size=EstimatedSize.S,
            human_approval=False,  # Should fail!
            result_path=".p2p/result.json",
            acr_path=".p2p/acr/",
        )


def test_agent_result_ignores_extra_fields():
    # Rule C4 / docs/02 §3: extra fields from LLM are ignored, not breaking
    res = AgentResult.model_validate({
        "task_id": "API-001",
        "run_id": "run-1",
        "outcome": "completed",
        "summary": "Completed CRUD API endpoints",
        "files_changed": ["backend/api/app.py"],
        "criteria_addressed": ["AC-1"],
        "assumptions": ["Default page size is 20"],
        "hallucinated_model_field": "some random data",
    })
    assert res.task_id == "API-001"
    assert res.outcome == TaskOutcome.COMPLETED
    assert not hasattr(res, "hallucinated_model_field")


def test_review_result_verdict_calculation():
    crit = ReviewFinding(
        severity=FindingSeverity.CRITICAL,
        file="src/auth.py",
        issue="Hardcoded API secret",
        suggestion="Use env var",
    )
    high = ReviewFinding(
        severity=FindingSeverity.HIGH,
        file="src/db.py",
        issue="Missing index",
        suggestion="Add index on user_id",
    )
    low = ReviewFinding(
        severity=FindingSeverity.LOW,
        file="src/utils.py",
        issue="Missing docstring",
        suggestion="Add docstring",
    )

    assert ReviewResult.calculate_verdict([crit, high, low]) == ReviewVerdict.REJECTED
    assert ReviewResult.calculate_verdict([high, low]) == ReviewVerdict.CHANGES_REQUESTED
    assert ReviewResult.calculate_verdict([low]) == ReviewVerdict.APPROVED
    assert ReviewResult.calculate_verdict([]) == ReviewVerdict.APPROVED


def test_connection_model_valid():
    conn = Connection(
        id="claude-pro-local",
        kind=ConnectionKind.SUBSCRIPTION,
        runtime=RuntimeType.CLAUDE_CODE,
        credential_ref="session",
        capabilities=[Capability.ARCHITECTURE, Capability.REVIEW],
        quality={"architecture": 0.95, "review": 0.92},
    )
    assert conn.id == "claude-pro-local"
    assert conn.runtime == RuntimeType.CLAUDE_CODE
