"""Unit tests for OllamaRuntime (local offline execution)."""
import json
from pathlib import Path
from src.models.enums import TaskOutcome, VerifiedBy
from src.models.task import AcceptanceCriterion, TaskContract
from src.runtime.ollama import OllamaRuntime


def test_ollama_runtime_doctor():
    def mock_ollama_http(url, payload):
        return {"models": [{"name": "llama3:latest"}]}

    runtime = OllamaRuntime(
        host="http://localhost:11434",
        model="llama3",
        http_client=mock_ollama_http,
    )

    doc = runtime.doctor()
    assert doc.available is True
    assert doc.authenticated is True
    assert "ollama-llama3" in doc.version


def test_ollama_runtime_execution(tmp_path: Path):
    def mock_ollama_chat(url, payload):
        assert "/api/chat" in url
        assert payload["model"] == "codellama"
        assert payload["format"] == "json"

        generated = {
            "summary": "Generated math utility via Ollama",
            "outcome": "completed",
            "files": {
                "math_utils.py": "def add(a, b): return a + b\n",
            },
        }
        return {"message": {"content": json.dumps(generated)}}

    runtime = OllamaRuntime(
        host="http://localhost:11434",
        model="codellama",
        http_client=mock_ollama_chat,
    )

    from src.models.enums import Capability, EstimatedSize, RiskLevel

    contract = TaskContract(
        id="OLLAMA-001",
        title="Generate math utils",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        intent="Add utility functions using local model.",
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", statement="math_utils created", verified_by=VerifiedBy.MANUAL)],
        inputs=["docs/01"],
        allowed_paths=["*.py"],
        forbidden_paths=[".p2p/**"],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        human_approval=True,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )

    result = runtime.execute(contract, workspace=tmp_path)

    assert result.outcome == TaskOutcome.COMPLETED
    assert (tmp_path / "math_utils.py").exists()
    assert (tmp_path / "math_utils.py").read_text() == "def add(a, b): return a + b\n"
    assert "math_utils.py" in result.files_changed


def test_ollama_runtime_features():
    runtime = OllamaRuntime(http_client=lambda u, p: {})
    assert runtime.health().value == "ok"
    assert runtime.features().can_stream is True
