"""Unit tests for GateRunner."""

from pathlib import Path
import sys

from src.models.enums import GateStatus
from src.verification.config import GateDefinition, GatesConfig
from src.verification.runner import GateRunner
from src.workspace.workspace import Workspace


def test_gate_runner_pass(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    config = GatesConfig(
        gates={
            "echo_pass": GateDefinition(
                cmd=[sys.executable, "-c", "print('All good')"],
                cwd=".",
                timeout_s=10,
                parse="none",
            )
        }
    )

    runner = GateRunner(ws, config)
    res = runner.run_gate("echo_pass", run_id="test-run-1")

    assert res.status == GateStatus.PASS
    assert res.exit_code == 0
    assert len(res.failures) == 0
    assert (ws.run_dir("test-run-1") / "gates" / "echo_pass.log").exists()


def test_gate_runner_fail(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    # Synthetic script simulating a failed test output
    script = (
        "import sys\n"
        "sys.stdout.write('FAILED tests/test_demo.py::test_fail - AssertionError: demo failed\\n')\n"
        "sys.exit(1)\n"
    )

    config = GatesConfig(
        gates={
            "unit": GateDefinition(
                cmd=[sys.executable, "-c", script],
                cwd=".",
                timeout_s=10,
                parse="pytest",
            )
        }
    )

    runner = GateRunner(ws, config)
    res = runner.run_gate("unit")

    assert res.status == GateStatus.FAIL
    assert res.exit_code == 1
    assert len(res.failures) == 1
    assert res.failures[0].rule == "test_fail"
    assert "demo failed" in res.failures[0].message


def test_gate_runner_missing_tool_error(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    config = GatesConfig(
        gates={
            "nonexistent": GateDefinition(
                cmd=["non_existent_binary_xyz_123"],
                cwd=".",
                on_missing_tool=GateStatus.ERROR,
            )
        }
    )

    runner = GateRunner(ws, config)
    res = runner.run_gate("nonexistent")

    assert res.status == GateStatus.ERROR
    assert res.exit_code == 127
    assert any("not found" in f.message for f in res.failures)


def test_gate_runner_fail_fast(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    config = GatesConfig(
        gates={
            "gate_fail": GateDefinition(
                cmd=[sys.executable, "-c", "import sys; sys.exit(1)"],
                parse="none",
            ),
            "gate_after": GateDefinition(
                cmd=[sys.executable, "-c", "print('after')"],
                parse="none",
            ),
        }
    )

    runner = GateRunner(ws, config)
    results = runner.run_gates(["gate_fail", "gate_after"], fail_fast=True)

    assert len(results) == 2
    assert results[0].status == GateStatus.FAIL
    assert results[1].status == GateStatus.SKIPPED
