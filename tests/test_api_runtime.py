"""Unit tests for ApiRuntime (OpenAI-compatible endpoints)."""
import json
from pathlib import Path
from src.models.enums import TaskOutcome, VerifiedBy
from src.models.task import AcceptanceCriterion, TaskContract
from src.runtime.api import ApiRuntime


def test_api_runtime_doctor():
    # Test doctor with simulated custom client
    def dummy_http(url, payload, headers):
        return {"choices": [{"message": {"content": "{}"}}]}

    runtime = ApiRuntime(
        endpoint="https://api.example.com/v1/chat/completions",
        api_key="test-key",
        http_client=dummy_http,
    )

    doc = runtime.doctor()
    assert doc.available is True
    assert doc.authenticated is True
    assert "gpt-4o" in doc.version


def test_api_runtime_execution(tmp_path: Path):
    def fake_http(url, payload, headers):
        assert "Authorization" in headers
        assert "Bearer secret-token" in headers["Authorization"]
        assert payload["model"] == "custom-model"

        # Simulating LLM returning JSON with code files
        model_resp = {
            "summary": "Generated auth module",
            "outcome": "completed",
            "files": {
                "src/auth.py": "def authenticate(): return True\n",
                "tests/test_auth.py": "def test_auth(): assert True\n",
            },
        }
        return {"choices": [{"message": {"content": json.dumps(model_resp)}}]}

    runtime = ApiRuntime(
        endpoint="https://api.openai-mock.com/v1/chat/completions",
        api_key="secret-token",
        model="custom-model",
        http_client=fake_http,
    )

    from src.models.enums import Capability, EstimatedSize, RiskLevel

    contract = TaskContract(
        id="API-001",
        title="Create auth module",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Implement authentication logic cleanly.",
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", statement="auth exists", verified_by=VerifiedBy.MANUAL)],
        inputs=["docs/01"],
        allowed_paths=["src/**", "tests/**"],
        forbidden_paths=[".p2p/**"],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        human_approval=True,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )

    result = runtime.execute(contract, workspace=tmp_path)

    assert result.outcome == TaskOutcome.COMPLETED
    assert result.task_id == "API-001"
    assert (tmp_path / "src" / "auth.py").exists()
    assert (tmp_path / "src" / "auth.py").read_text() == "def authenticate(): return True\n"
    assert "src/auth.py" in result.files_changed


def test_api_runtime_features_and_health():
    runtime = ApiRuntime(endpoint="", api_key="")
    assert runtime.health().value == "unreachable"

    runtime_ok = ApiRuntime(endpoint="http://localhost:8000/v1")
    assert runtime_ok.health().value == "ok"
    assert runtime_ok.features().can_stream is True
