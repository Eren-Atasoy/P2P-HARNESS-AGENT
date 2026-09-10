"""Tests for MockRuntime deterministic execution."""
from pathlib import Path

from src.models import (
    AcceptanceCriterion,
    Capability,
    EstimatedSize,
    RiskLevel,
    TaskContract,
    TaskOutcome,
    VerifiedBy,
)
from src.runtime.mock import MockRuntime


def test_mock_runtime_file_creation_and_result(tmp_path: Path):
    contract = TaskContract(
        id="DB-001",
        title="Create initial schema",
        capabilities=[Capability.DATABASE],
        risk=RiskLevel.MEDIUM,
        intent="Database schema setup.",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Tables are defined",
                verified_by=VerifiedBy.TEST,
                test_ref="tests/test_db.py::test_schema",
            )
        ],
        inputs=["docs/02"],
        allowed_paths=["backend/models/**"],
        forbidden_paths=["frontend/**"],
        gates=["lint"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )

    runtime = MockRuntime(
        default_outcome=TaskOutcome.COMPLETED,
        files_to_create={"backend/models/user.py": "class User: pass"},
    )

    workspace = tmp_path / "workspace"
    result = runtime.execute(contract, workspace)

    assert result.task_id == "DB-001"
    assert result.outcome == TaskOutcome.COMPLETED
    assert "backend/models/user.py" in result.files_changed
    assert (workspace / "backend/models/user.py").exists()
    assert (workspace / "backend/models/user.py").read_text(encoding="utf-8") == "class User: pass"
    assert len(runtime.invocations) == 1
