"""Tests for RepairPlanner and failure classification (docs/03 §3)."""
from src.models.enums import Capability, EstimatedSize, GateStatus, RiskLevel, VerifiedBy
from src.models.result import Failure, GateResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.repair import FailureClass, RepairPlanner


def test_classify_gate_failure():
    err_gate = GateResult(
        gate="smoke",
        status=GateStatus.ERROR,
        exit_code=127,
        duration_ms=10,
        log_path="smoke.log",
    )
    assert RepairPlanner.classify_gate_failure(err_gate) == FailureClass.ENV

    fail_lint = GateResult(
        gate="lint",
        status=GateStatus.FAIL,
        exit_code=1,
        duration_ms=10,
        log_path="lint.log",
    )
    assert RepairPlanner.classify_gate_failure(fail_lint) == FailureClass.SYNTAX

    fail_unit = GateResult(
        gate="unit",
        status=GateStatus.FAIL,
        exit_code=1,
        duration_ms=10,
        log_path="unit.log",
    )
    assert RepairPlanner.classify_gate_failure(fail_unit) == FailureClass.TEST_FAIL


def test_env_error_escalates_immediately_without_fix_loop():
    planner = RepairPlanner()
    task = TaskContract(
        id="TASK-001",
        title="Env Test",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Env test intent",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Must work", verified_by=VerifiedBy.GATE, gate_ref="smoke")
        ],
        inputs=["docs/01"],
        allowed_paths=["src/**"],
        forbidden_paths=[],
        gates=["smoke"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
        max_attempts=3,
    )

    env_gate = GateResult(
        gate="smoke",
        status=GateStatus.ERROR,
        exit_code=127,
        duration_ms=10,
        log_path="smoke.log",
    )

    should_retry, f_class, reason = planner.should_enter_fix_loop(
        task=task,
        attempt=1,
        gate_results=[env_gate],
    )
    # Docs/03 §3 rule: ENV errors NEVER enter fix loop -> straight to ESCALATED
    assert should_retry is False
    assert f_class == FailureClass.ENV
    assert "Environment/tooling error" in reason


def test_circuit_breaker_identical_failures_twice():
    planner = RepairPlanner()
    task = TaskContract(
        id="TASK-002",
        title="Stuck Test",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Stuck test intent",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Calc works", verified_by=VerifiedBy.TEST, test_ref="tests/test_calc.py::test_fn")
        ],
        inputs=["docs/01"],
        allowed_paths=["src/**"],
        forbidden_paths=[],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
        max_attempts=5,
    )

    failures = [
        Failure(file="src/calc.py", line=10, rule="assert", message="Expected 4 got 5")
    ]
    gate = GateResult(
        gate="unit",
        status=GateStatus.FAIL,
        exit_code=1,
        duration_ms=10,
        log_path="unit.log",
        failures=failures,
    )

    # Attempt 1 -> enters fix loop
    should_retry, _, _ = planner.should_enter_fix_loop(task, 1, [gate])
    assert should_retry is True

    # Attempt 2 with IDENTICAL failure -> triggers circuit breaker and escalates!
    should_retry_2, f_class, reason = planner.should_enter_fix_loop(task, 2, [gate])
    assert should_retry_2 is False
    assert "zero progress" in reason.lower()
