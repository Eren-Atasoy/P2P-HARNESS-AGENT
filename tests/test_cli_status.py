"""Tests for p2p status and version CLI commands."""
from pathlib import Path
from typer.testing import CliRunner

from src.cli.main import app
from src.events.store import EventStore
from src.models.enums import EventType

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Prompt2Product version" in result.stdout


def test_cli_status_no_events(tmp_path: Path):
    result = runner.invoke(app, ["status", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "No event log found" in result.stdout


def test_cli_status_with_events(tmp_path: Path):
    events_dir = tmp_path / ".p2p"
    events_file = events_dir / "events.jsonl"
    store = EventStore(events_file)

    store.append(EventType.PROJECT_CREATED, {"name": "crm-app"})
    store.append(EventType.RUN_STARTED, {"autonomy_level": "full"}, run_id="run-77")
    store.append(EventType.TASK_CREATED, {"risk": "low"}, task_id="FE-001", run_id="run-77")

    result = runner.invoke(app, ["status", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "crm-app" in result.stdout
    assert "run-77" in result.stdout
    assert "FE-001" in result.stdout
