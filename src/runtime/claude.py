"""Claude Code headless runtime adapter (docs/04 §4 and docs/11 V4)."""
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


class ClaudeCodeRuntime(RuntimeAdapter):
    """Executes tasks using Claude Code CLI in headless mode (`claude -p ... --output-format json`)."""

    def __init__(
        self,
        executable: Optional[str] = None,
        timeout_s: int = 600,
        prompt_override: Optional[str] = None,
    ):
        self.executable = executable or shutil.which("claude") or "claude"
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
                stdin=subprocess.DEVNULL,  # CRITICAL: prevents terminal stall (V4)
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
            stderr = f"Claude executable not found: {self.executable}"
            exit_code = 127

        # Log stdout/stderr for audit
        (run_dir / "claude_stdout.log").write_text(stdout, encoding="utf-8")
        (run_dir / "claude_stderr.log").write_text(stderr, encoding="utf-8")

        # Parse JSON output from Claude CLI if available
        claude_meta = {}
        if stdout.strip():
            try:
                claude_meta = json.loads(stdout)
            except json.JSONDecodeError:
                pass

        # Check if structured result exists at contract.result_path
        result_file = workspace / contract.result_path
        if result_file.exists():
            try:
                result_data = json.loads(result_file.read_text(encoding="utf-8"))
                agent_result = AgentResult.model_validate(result_data)
                # Enrich usage if present
                if claude_meta.get("usage") or "total_cost_usd" in claude_meta:
                    usage = claude_meta.get("usage", {})
                    agent_result.usage = RunUsage(
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        total_cost_usd=claude_meta.get("total_cost_usd"),
                        duration_ms=int(duration_ms),
                    )
                return agent_result
            except Exception:
                pass

        # Fallback if result.json was not written directly by agent
        is_error = (exit_code != 0) or claude_meta.get("is_error", False)
        outcome = TaskOutcome.FAILED if is_error else TaskOutcome.COMPLETED

        summary_text = (
            claude_meta.get("result")
            or (f"Execution completed with exit code {exit_code}" if not is_error else f"Execution failed: {stderr[:200]}")
        )

        usage = claude_meta.get("usage", {})
        run_usage = RunUsage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_cost_usd=claude_meta.get("total_cost_usd"),
            duration_ms=int(duration_ms),
        )

        return AgentResult(
            task_id=contract.id,
            run_id=run_id,
            outcome=outcome,
            summary=str(summary_text)[:500],
            files_changed=[],
            criteria_addressed=[ac.id for ac in contract.acceptance_criteria] if outcome == TaskOutcome.COMPLETED else [],
            assumptions=[],
            failure_reason=stderr[:300] if is_error else None,
            usage=run_usage,
        )

    def features(self) -> RuntimeFeatures:
        return RuntimeFeatures(
            can_stream=True,
            can_cancel=True,
            can_pause=False,
            can_resume=False,
            supports_structured_output=True,
            supports_subagents=True,
            supports_mcp=True,
            can_execute=True,
        )

    def health(self) -> HealthStatus:
        if not shutil.which(self.executable):
            return HealthStatus.UNREACHABLE
        return HealthStatus.OK

    def doctor(self, connection_id: str = "claude-code") -> RuntimeDoctorResult:
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
                error=None if available else "Claude CLI returned non-zero on --version",
            )
        except Exception as e:
            return RuntimeDoctorResult(
                connection_id=connection_id,
                available=False,
                authenticated=False,
                error=str(e),
            )
