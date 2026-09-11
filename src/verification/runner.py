"""Gate runner executing verification commands and enforcing serialized isolation."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import threading
import time
from typing import TYPE_CHECKING

from src.models.enums import GateStatus
from src.models.result import GateFailure, GateResult
from src.verification.config import GatesConfig
from src.verification.parsers import get_parser

if TYPE_CHECKING:
    from src.workspace.workspace import Workspace


class GateRunner:
    """Executes declarative verification gates and produces GateResult objects."""

    _serialized_lock = threading.Lock()

    def __init__(self, workspace: Workspace, gates_config: GatesConfig | None = None) -> None:
        self.workspace = workspace
        self.gates_config = gates_config or GatesConfig.default_config()

    def run_gate(
        self,
        gate_name: str,
        target_dir: Path | None = None,
        run_id: str | None = None,
    ) -> GateResult:
        """Run a single verification gate and return its structured result."""
        if gate_name not in self.gates_config.gates:
            return GateResult(
                gate=gate_name,
                status=GateStatus.ERROR,
                exit_code=-1,
                duration_ms=0,
                log_path="",
                failures=[
                    GateFailure(
                        file=None,
                        line=None,
                        rule="configuration",
                        message=f"Gate '{gate_name}' is not defined in gates configuration.",
                    )
                ],
            )

        gate_def = self.gates_config.gates[gate_name]
        base_dir = Path(target_dir).resolve() if target_dir is not None else self.workspace.root_path
        working_cwd = (base_dir / gate_def.cwd).resolve()

        # Check working directory existence
        if not working_cwd.exists():
            return GateResult(
                gate=gate_name,
                status=GateStatus.ERROR,
                exit_code=-1,
                duration_ms=0,
                log_path="",
                failures=[
                    GateFailure(
                        file=None,
                        line=None,
                        rule="filesystem",
                        message=f"Working directory for gate '{gate_name}' does not exist: {working_cwd}",
                    )
                ],
            )

        # Environment configuration
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["LC_ALL"] = "C.UTF-8"

        start_time = time.perf_counter()
        stdout_text = ""
        stderr_text = ""
        exit_code = 0
        status = GateStatus.PASS
        failures: list[GateFailure] = []

        def execute_cmd() -> tuple[str, str, int]:
            proc = subprocess.run(
                gate_def.cmd,
                cwd=str(working_cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=gate_def.timeout_s,
                check=False,
            )
            return proc.stdout or "", proc.stderr or "", proc.returncode

        try:
            if gate_def.isolation == "serialized":
                with self._serialized_lock:
                    stdout_text, stderr_text, exit_code = execute_cmd()
            else:
                stdout_text, stderr_text, exit_code = execute_cmd()

            if exit_code == 0:
                status = GateStatus.PASS
                failures = []
            else:
                status = GateStatus.FAIL
                parser = get_parser(gate_def.parse)
                failures = parser.parse(stdout_text, stderr_text, exit_code)

        except FileNotFoundError:
            status = gate_def.on_missing_tool
            exit_code = 127
            failures = [
                GateFailure(
                    file=None,
                    line=None,
                    rule="missing_tool",
                    message=f"Required tool not found for command: {gate_def.cmd[0]}",
                )
            ]
        except subprocess.TimeoutExpired:
            status = GateStatus.ERROR
            exit_code = 124
            failures = [
                GateFailure(
                    file=None,
                    line=None,
                    rule="timeout",
                    message=f"Gate '{gate_name}' timed out after {gate_def.timeout_s} seconds.",
                )
            ]
        except Exception as err:
            status = GateStatus.ERROR
            exit_code = 1
            failures = [
                GateFailure(
                    file=None,
                    line=None,
                    rule="execution_error",
                    message=f"Unexpected error executing gate '{gate_name}': {err}",
                )
            ]

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Write log file if run_id provided
        log_posix_path = ""
        if run_id:
            gates_log_dir = self.workspace.run_dir(run_id) / "gates"
            gates_log_dir.mkdir(parents=True, exist_ok=True)
            log_file = gates_log_dir / f"{gate_name}.log"
            log_content = (
                f"=== GATE: {gate_name} ===\n"
                f"Command: {' '.join(gate_def.cmd)}\n"
                f"Cwd: {working_cwd}\n"
                f"Exit Code: {exit_code}\n"
                f"Duration: {elapsed_ms}ms\n\n"
                f"--- STDOUT ---\n{stdout_text}\n"
                f"--- STDERR ---\n{stderr_text}\n"
            )
            log_file.write_text(log_content, encoding="utf-8")
            log_posix_path = self.workspace.relative_posix_path(log_file)

        return GateResult(
            gate=gate_name,
            status=status,
            exit_code=exit_code,
            duration_ms=elapsed_ms,
            log_path=log_posix_path,
            failures=failures,
        )

    def run_gates(
        self,
        gate_names: list[str],
        target_dir: Path | None = None,
        run_id: str | None = None,
        fail_fast: bool = True,
    ) -> list[GateResult]:
        """Execute multiple gates in order with optional fail-fast."""
        results: list[GateResult] = []

        for name in gate_names:
            res = self.run_gate(name, target_dir=target_dir, run_id=run_id)
            results.append(res)

            if fail_fast and res.status in {GateStatus.FAIL, GateStatus.ERROR}:
                # Mark remaining gates as SKIPPED
                remaining_index = gate_names.index(name) + 1
                for remaining_name in gate_names[remaining_index:]:
                    results.append(
                        GateResult(
                            gate=remaining_name,
                            status=GateStatus.SKIPPED,
                            exit_code=0,
                            duration_ms=0,
                            log_path="",
                            failures=[],
                        )
                    )
                break

        return results
