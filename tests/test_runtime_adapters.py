"""Tests for runtime adapters (docs/04 §4)."""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models.enums import Capability, EstimatedSize, RiskLevel, TaskOutcome, VerifiedBy
from src.models.result import AgentResult
from src.models.task import AcceptanceCriterion, TaskContract
from src.runtime.base import HealthStatus
from src.runtime.claude import ClaudeCodeRuntime
from src.runtime.gemini import GeminiCliRuntime
from src.runtime.mock import MockRuntime


@pytest.fixture
def sample_task() -> TaskContract:
    return TaskContract(
        id="TASK-001",
        title="Test Task",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="A test task intent",
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", statement="Must work", verified_by=VerifiedBy.TEST, test_ref="tests/test_app.py::test_fn")
        ],
        inputs=["docs/01"],
        allowed_paths=["src/test.py"],
        forbidden_paths=[],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )


def test_mock_runtime(tmp_path: Path, sample_task: TaskContract):
    runtime = MockRuntime(files_to_create={"src/test.py": "print('hello')"})
    assert runtime.health() == HealthStatus.OK
    doctor_res = runtime.doctor()
    assert doctor_res.available is True
    assert doctor_res.version == "mock-1.0.0"

    features = runtime.features()
    assert features.supports_structured_output is True

    result = runtime.execute(sample_task, tmp_path, run_id="run-1")
    assert result.outcome == TaskOutcome.COMPLETED
    assert "src/test.py" in result.files_changed
    assert (tmp_path / "src" / "test.py").exists()


def test_claude_runtime_success_parsing(tmp_path: Path, sample_task: TaskContract):
    runtime = ClaudeCodeRuntime(executable="claude")

    claude_stdout = json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "Created src/test.py successfully",
        "total_cost_usd": 0.005,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    })

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout=claude_stdout,
            stderr="",
        )

        result = runtime.execute(sample_task, tmp_path, run_id="run-claude")
        assert result.outcome == TaskOutcome.COMPLETED
        assert result.usage is not None
        assert result.usage.total_cost_usd == 0.005
        assert result.usage.input_tokens == 100

        # Verify stdin=DEVNULL was passed (V4 requirement)
        _, kwargs = mock_run.call_args
        assert kwargs["stdin"] == subprocess.DEVNULL


def test_claude_runtime_failure(tmp_path: Path, sample_task: TaskContract):
    runtime = ClaudeCodeRuntime(executable="claude")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="API quota exceeded or network error",
        )

        result = runtime.execute(sample_task, tmp_path, run_id="run-fail")
        assert result.outcome == TaskOutcome.FAILED
        assert "API quota exceeded" in (result.failure_reason or "")


def test_gemini_runtime_doctor():
    runtime = GeminiCliRuntime(executable="gemini")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gemini", "--version"],
            returncode=0,
            stdout="gemini-cli v1.2.0",
            stderr="",
        )
        doc = runtime.doctor()
        assert doc.available is True
        assert doc.version == "gemini-cli v1.2.0"
