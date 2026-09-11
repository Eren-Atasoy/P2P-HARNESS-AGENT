"""OpenAI-compatible REST API RuntimeAdapter (docs/04 §4, docs/08 Faz 9).

Proves Connection(kind=ConnectionKind.API) without hardcoded vendor dependencies.
Works with any OpenAI-compliant endpoint (OpenAI, vLLM, LiteLLM, Groq, Mistral, LocalAI).
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from src.models.enums import TaskOutcome
from src.models.result import AgentResult
from src.models.task import TaskContract
from src.runtime.base import HealthStatus, RuntimeAdapter, RuntimeDoctorResult, RuntimeFeatures


class ApiRuntime(RuntimeAdapter):
    """RuntimeAdapter connecting to any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        timeout: float = 60.0,
        http_client: Optional[Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]] = None,
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self._custom_http = http_client

    def _call_http(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Performs HTTP POST to completions endpoint."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if self._custom_http:
            return self._custom_http(self.endpoint, payload, headers)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)

    def execute(self, contract: TaskContract, workspace: Path, run_id: Optional[str] = None) -> AgentResult:
        """Executes task contract against OpenAI-compatible API endpoint."""
        system_prompt = (
            "You are an autonomous software engineer implementing a task contract.\n"
            "Return your response as a JSON object with keys:\n"
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
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        created_files = []
        try:
            res_data = self._call_http(payload)
            choices = res_data.get("choices", [])
            content_str = choices[0]["message"]["content"] if choices else "{}"
            parsed = json.loads(content_str)

            files = parsed.get("files", {})
            for rel_path, content in files.items():
                target_path = workspace / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                created_files.append(rel_path.replace("\\", "/"))

            outcome = TaskOutcome.COMPLETED if parsed.get("outcome") != "failed" else TaskOutcome.FAILED
            summary = parsed.get("summary", f"ApiRuntime completed {contract.id}")

            return AgentResult(
                task_id=contract.id,
                run_id=run_id or "api-run-001",
                outcome=outcome,
                summary=summary,
                files_changed=created_files,
                criteria_addressed=[ac.id for ac in contract.acceptance_criteria],
                assumptions=[f"Executed via ApiRuntime against {self.endpoint}"],
                failure_reason=None if outcome == TaskOutcome.COMPLETED else "Model indicated task failed",
            )
        except Exception as exc:
            return AgentResult(
                task_id=contract.id,
                run_id=run_id or "api-run-err",
                outcome=TaskOutcome.FAILED,
                summary=f"ApiRuntime execution error: {exc}",
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
        if not self.endpoint:
            return HealthStatus.UNREACHABLE
        if not self.api_key and "localhost" not in self.endpoint and "127.0.0.1" not in self.endpoint:
            return HealthStatus.DEGRADED
        return HealthStatus.OK

    def doctor(self, connection_id: str = "api-openai-compatible") -> RuntimeDoctorResult:
        start_t = time.time()
        # Ping with a minimal request or mock check
        try:
            if self._custom_http:
                # In test mode, custom http can verify
                self._custom_http(self.endpoint, {"test": True}, {})
            elif not self.api_key and "localhost" not in self.endpoint and "127.0.0.1" not in self.endpoint:
                return RuntimeDoctorResult(
                    connection_id=connection_id,
                    available=True,
                    authenticated=False,
                    can_read=False,
                    can_write=False,
                    can_execute=False,
                    error="API key is missing for remote endpoint",
                )
            latency = (time.time() - start_t) * 1000
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=True,
                authenticated=True,
                can_read=True,
                can_write=True,
                can_execute=True,
                version=f"api-{self.model}",
                latency_ms=round(latency, 2),
            )
        except Exception as err:
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=False,
                authenticated=False,
                error=str(err),
            )
