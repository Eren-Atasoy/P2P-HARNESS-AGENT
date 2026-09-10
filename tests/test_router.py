"""Tests for CapabilityRouter capability matching, scoring, UNROUTABLE diagnostic, and escalation."""
import pytest
from src.models import (
    AcceptanceCriterion,
    AutomationPolicy,
    Capability,
    Connection,
    ConnectionKind,
    EstimatedSize,
    HealthStatus,
    RiskLevel,
    RuntimeType,
    TaskContract,
    VerifiedBy,
)
from src.orchestration.router import CapabilityRouter, UnroutableTaskError


def make_conn(cid: str, caps: list[Capability], quality: dict[str, float] = None, health=HealthStatus.OK, policy=AutomationPolicy.ALLOWED) -> Connection:
    return Connection(
        id=cid,
        kind=ConnectionKind.SUBSCRIPTION,
        runtime=RuntimeType.MOCK,
        credential_ref="session",
        capabilities=caps,
        quality=quality or {},
        health=health,
        automation_policy=policy,
    )


def make_task(tid: str, caps: list[Capability]) -> TaskContract:
    return TaskContract(
        id=tid,
        title=f"Task {tid}",
        capabilities=caps,
        risk=RiskLevel.LOW,
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


def test_router_selects_highest_quality_matching_connection():
    conn_a = make_conn("conn-a", [Capability.BACKEND, Capability.DATABASE], {"backend": 0.85})
    conn_b = make_conn("conn-b", [Capability.BACKEND, Capability.DATABASE], {"backend": 0.95})

    router = CapabilityRouter([conn_a, conn_b])
    task = make_task("API-001", [Capability.BACKEND])

    selected = router.route(task)
    assert selected.id == "conn-b"


def test_router_raises_unroutable_with_diagnostic_when_no_match():
    conn_backend = make_conn("conn-be", [Capability.BACKEND])
    router = CapabilityRouter([conn_backend])

    # Task requires browser capability which no connection offers
    task = make_task("E2E-001", [Capability.BACKEND, Capability.BROWSER])

    with pytest.raises(UnroutableTaskError) as exc_info:
        router.route(task)

    msg = str(exc_info.value)
    assert "UNROUTABLE" in msg
    assert "browser" in msg
    assert "Recommendation" in msg


def test_router_escalation_on_repeated_failure():
    conn_be = make_conn("gemini-conn", [Capability.BACKEND], {"backend": 0.88})
    conn_expert = make_conn("claude-conn", [Capability.BACKEND], {"backend": 0.92})

    escalation_map = {"backend": "claude-conn"}
    router = CapabilityRouter([conn_be, conn_expert], escalation_map=escalation_map)
    task = make_task("API-001", [Capability.BACKEND])

    # First attempt: routes by quality
    first = router.route(task, attempt=1)
    assert first.id == "claude-conn"

    # Suppose gemini had higher score originally, on attempt 2 it picks escalation connection
    conn_fast = make_conn("fast-conn", [Capability.BACKEND], {"backend": 0.99})
    router2 = CapabilityRouter([conn_fast, conn_expert], escalation_map=escalation_map)
    assert router2.route(task, attempt=1).id == "fast-conn"
    assert router2.route(task, attempt=2).id == "claude-conn"
