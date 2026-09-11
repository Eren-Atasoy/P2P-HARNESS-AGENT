"""Tests for PromptCompiler (docs/03 §3.1, ADR-008)."""
from src.models.enums import Capability, EstimatedSize, FindingSeverity, ReviewVerdict, RiskLevel, TaskOutcome, VerifiedBy
from src.models.result import AgentResult, Failure, ReviewFinding, ReviewResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.prompts import PromptCompiler


def test_truncate_lines():
    lines = [f"line {i}" for i in range(200)]
    text = "\n".join(lines)
    truncated = PromptCompiler.truncate_lines(text, max_head=10, max_tail=10)
    assert "line 0" in truncated
    assert "line 9" in truncated
    assert "line 199" in truncated
    assert "TRUNCATED 180 LINES" in truncated


def test_compile_implementer_prompt():
    contract = TaskContract(
        id="TASK-001",
        title="Setup Auth",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Implement user authentication",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Register endpoint exists", verified_by=VerifiedBy.TEST, test_ref="tests/test_auth.py::test_reg"),
            AcceptanceCriterion(id="AC-2", statement="Login endpoint returns JWT", verified_by=VerifiedBy.TEST, test_ref="tests/test_auth.py::test_login"),
        ],
        inputs=["docs/auth.md"],
        allowed_paths=["backend/auth/**"],
        forbidden_paths=["frontend/**"],
        gates=["unit"],
        estimated_size=EstimatedSize.M,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )

    prompt = PromptCompiler.compile_implementer_prompt(contract)
    assert "TASK-001" in prompt
    assert "Setup Auth" in prompt
    assert "backend/auth/**" in prompt
    assert "frontend/**" in prompt
    assert "Register endpoint exists" in prompt
    assert "Login endpoint returns JWT" in prompt
    assert "Shell Access" in prompt


def test_compile_fix_prompt():
    contract = TaskContract(
        id="TASK-002",
        title="Fix Auth Bug",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Fix JWT token validity",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Token validity", verified_by=VerifiedBy.TEST, test_ref="tests/test_auth.py::test_jwt")
        ],
        inputs=["docs/auth.md"],
        allowed_paths=["backend/auth/**"],
        forbidden_paths=[],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )

    prev_res = AgentResult(
        task_id=contract.id,
        run_id="run-1",
        outcome=TaskOutcome.FAILED,
        summary="Tried to implement JWT but hit a syntax error",
    )

    failures = [
        Failure(file="backend/auth/jwt.py", line=42, rule="E999", message="SyntaxError: invalid syntax")
    ]

    review = ReviewResult(
        task_id=contract.id,
        attempt=1,
        verdict=ReviewVerdict.CHANGES_REQUESTED,
        findings=[
            ReviewFinding(
                severity=FindingSeverity.HIGH,
                file="backend/auth/jwt.py",
                line=42,
                issue="Missing colon",
                suggestion="Add colon after def",
            )
        ],
    )

    prompt = PromptCompiler.compile_fix_prompt(
        contract=contract,
        previous_result=prev_res,
        failures=failures,
        raw_gate_output="FAILED tests/test_auth.py::test_jwt - SyntaxError: invalid syntax",
        review=review,
    )

    assert "Sadece bu bulguları gider. Başka refactor yapma." in prompt
    assert "SyntaxError: invalid syntax" in prompt
    assert "backend/auth/jwt.py:42" in prompt
    assert "Tried to implement JWT" in prompt
    assert "Missing colon" in prompt
