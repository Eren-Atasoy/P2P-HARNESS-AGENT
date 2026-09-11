"""Local Ollama RuntimeAdapter (docs/04 §4, docs/08 Faz 9).

Proves Connection(kind=ConnectionKind.LOCAL) for fully offline, on-premise execution.
Works with local Ollama daemon running on http://localhost:11434.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from src.models.enums import TaskOutcome
from src.models.result import AgentResult
from src.models.task import TaskContract
from src.runtime.base import HealthStatus, RuntimeAdapter, RuntimeDoctorResult, RuntimeFeatures


class OllamaRuntime(RuntimeAdapter):
    """RuntimeAdapter connecting to local Ollama service."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 120.0,
        http_client: Optional[Callable[[str, dict[str, Any]], dict[str, Any]]] = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._custom_http = http_client

    def _call_ollama(self, endpoint_path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Performs HTTP POST to Ollama endpoint."""
        url = f"{self.host}{endpoint_path}"
        if self._custom_http:
            return self._custom_http(url, payload)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)

    def execute(self, contract: TaskContract, workspace: Path, run_id: Optional[str] = None) -> AgentResult:
        """Executes task contract using local Ollama model."""
        system_prompt = (
            "You are an autonomous local software engineer implementing a task contract.\n"
            "Return output strictly as a JSON object with keys:\n"
            "- 'files': dict of {path: content}\n"
            "- 'summary': string summary\n"
            "- 'outcome': 'completed' or 'failed'\n"
        )
        user_prompt = f"TASK ID: {contract.id}\nTITLE: {contract.title}\nSPEC:\n{contract.model_dump_json(indent=2)}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
        }

        created_files = []
        try:
            res_data = self._call_ollama("/api/chat", payload)
            msg_content = res_data.get("message", {}).get("content", "{}")
            parsed = json.loads(msg_content)

            files = parsed.get("files", {})
            for rel_path, content in files.items():
                target_path = workspace / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                created_files.append(rel_path.replace("\\", "/"))

            outcome = TaskOutcome.COMPLETED if parsed.get("outcome") != "failed" else TaskOutcome.FAILED
            summary = parsed.get("summary", f"OllamaRuntime completed {contract.id} with {self.model}")

            return AgentResult(
                task_id=contract.id,
                run_id=run_id or "ollama-run-001",
                outcome=outcome,
                summary=summary,
                files_changed=created_files,
                criteria_addressed=[ac.id for ac in contract.acceptance_criteria],
                assumptions=[f"Executed locally via Ollama ({self.model})"],
                failure_reason=None if outcome == TaskOutcome.COMPLETED else "Local model indicated task failed",
            )
        except Exception as exc:
            return AgentResult(
                task_id=contract.id,
                run_id=run_id or "ollama-run-err",
                outcome=TaskOutcome.FAILED,
                summary=f"OllamaRuntime execution error: {exc}",
                files_changed=created_files,
                criteria_addressed=[],
                assumptions=[],
                failure_reason=str(exc),
            )

    def features(self) -> RuntimeFeatures:
        return RuntimeFeatures(
            can_stream=True,
            can_cancel=True,
            can_pause=False,
            can_resume=False,
            supports_structured_output=True,
            supports_subagents=False,
            supports_mcp=False,
            can_execute=True,
        )

    def health(self) -> HealthStatus:
        if self._custom_http:
            return HealthStatus.OK
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return HealthStatus.OK
            return HealthStatus.DEGRADED
        except Exception:
            return HealthStatus.UNREACHABLE

    def doctor(self, connection_id: str = "ollama-local") -> RuntimeDoctorResult:
        start_t = time.time()
        try:
            if self._custom_http:
                self._custom_http(f"{self.host}/api/tags", {})
            else:
                req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Ollama returned HTTP {resp.status}")

            latency = (time.time() - start_t) * 1000
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=True,
                authenticated=True,
                can_read=True,
                can_write=True,
                can_execute=True,
                version=f"ollama-{self.model}",
                latency_ms=round(latency, 2),
            )
        except Exception as err:
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=False,
                authenticated=False,
                error=f"Cannot reach local Ollama daemon at {self.host}: {err}",
            )
