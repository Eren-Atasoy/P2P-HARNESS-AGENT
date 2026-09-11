"""Gemini CLI headless runtime adapter (docs/04 §4)."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from src.models.enums import TaskOutcome
from src.models.result import AgentResult, RunUsage
from src.models.task import TaskContract
from src.runtime.base import HealthStatus, RuntimeAdapter, RuntimeDoctorResult, RuntimeFeatures


class GeminiCliRuntime(RuntimeAdapter):
    """Executes tasks using Gemini CLI (`gemini -p ... --output-format json`)."""

    def __init__(
        self,
        executable: Optional[str] = None,
        timeout_s: int = 600,
        prompt_override: Optional[str] = None,
    ):
        self.executable = executable or shutil.which("gemini") or "gemini"
        self.timeout_s = timeout_s
        self.prompt_override = prompt_override

    def execute(self, contract: TaskContract, workspace: Path, run_id: Optional[str] = None) -> AgentResult:
        run_id = run_id or f"run-{int(time.time())}"
        run_dir = workspace / ".p2p" / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        prompt = self.prompt_override or contract.intent or contract.title

        cmd = [self.executable, "-p", prompt, "--output-format", "json"]

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        start_time = time.time()
        try:
            res = subprocess.run(
                cmd,
                cwd=str(workspace),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_s,
                env=env,
            )
            duration_ms = (time.time() - start_time) * 1000
            stdout = res.stdout
            stderr = res.stderr
            exit_code = res.returncode
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.time() - start_time) * 1000
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else "Command timed out"
            exit_code = 124
        except FileNotFoundError:
            duration_ms = 0
            stdout = ""
            stderr = f"Gemini executable not found: {self.executable}"
            exit_code = 127

        (run_dir / "gemini_stdout.log").write_text(stdout, encoding="utf-8")
        (run_dir / "gemini_stderr.log").write_text(stderr, encoding="utf-8")

        # Check if structured result exists at contract.result_path
        result_file = workspace / contract.result_path
        if result_file.exists():
            try:
                result_data = json.loads(result_file.read_text(encoding="utf-8"))
                agent_result = AgentResult.model_validate(result_data)
                agent_result.usage = RunUsage(duration_ms=int(duration_ms))
                return agent_result
            except Exception:
                pass

        is_error = exit_code != 0
        outcome = TaskOutcome.FAILED if is_error else TaskOutcome.COMPLETED

        return AgentResult(
            task_id=contract.id,
            run_id=run_id,
            outcome=outcome,
            summary=f"Gemini execution finished with exit code {exit_code}",
            files_changed=[],
            criteria_addressed=[ac.id for ac in contract.acceptance_criteria] if outcome == TaskOutcome.COMPLETED else [],
            assumptions=[],
            failure_reason=stderr[:300] if is_error else None,
            usage=RunUsage(duration_ms=int(duration_ms)),
        )

    def features(self) -> RuntimeFeatures:
        return RuntimeFeatures(
            can_stream=False,
            can_cancel=True,
            can_pause=False,
            can_resume=False,
            supports_structured_output=True,
            supports_subagents=False,
            supports_mcp=False,
            can_execute=True,
        )

    def health(self) -> HealthStatus:
        if not shutil.which(self.executable):
            return HealthStatus.UNREACHABLE
        return HealthStatus.OK

    def doctor(self, connection_id: str = "gemini-cli") -> RuntimeDoctorResult:
        start = time.time()
        try:
            res = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                stdin=subprocess.DEVNULL,
            )
            latency = (time.time() - start) * 1000
            available = (res.returncode == 0)
            version = res.stdout.strip() or res.stderr.strip()
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=available,
                authenticated=available,
                version=version or None,
                latency_ms=round(latency, 2),
                error=None if available else "Gemini CLI returned non-zero on --version",
            )
        except Exception as e:
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=False,
                authenticated=False,
                error=str(e),
            )
