"""Unit tests for P2P Web Dashboard HTTP & REST API Server (docs/12 §2.A, docs/08 Faz 10)."""
import json
import urllib.request
from pathlib import Path
import time
import pytest

from src.models.enums import Capability, EstimatedSize, EventType, RiskLevel, VerifiedBy
from src.models.event import Event
from src.models.task import AcceptanceCriterion, TaskContract
from src.ui.server import P2PUIServer
from src.workspace.workspace import Workspace


@pytest.fixture
def ui_test_env(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()

    # Create dummy tasks
    task1 = TaskContract(
        id="UI-001",
        title="Implement header component",
        capabilities=[Capability.FRONTEND],
        risk=RiskLevel.LOW,
        intent="Header navigation and theme toggle.",
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", statement="header renders", verified_by=VerifiedBy.MANUAL)],
        inputs=["docs/12"],
        allowed_paths=["src/ui/**"],
        forbidden_paths=[".p2p/**"],
        gates=["unit"],
        estimated_size=EstimatedSize.S,
        human_approval=True,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )
    (ws.tasks_dir / "UI-001.json").write_text(task1.model_dump_json(), encoding="utf-8")

    task2 = TaskContract(
        id="AUTH-002",
        title="Implement oauth provider",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.HIGH,
        intent="High-risk auth configuration.",
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", statement="oauth works", verified_by=VerifiedBy.MANUAL)],
        inputs=["docs/01"],
        allowed_paths=["src/auth/**"],
        forbidden_paths=[".p2p/**"],
        gates=["unit"],
        estimated_size=EstimatedSize.M,
        human_approval=True,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )
    (ws.tasks_dir / "AUTH-002.json").write_text(task2.model_dump_json(), encoding="utf-8")

    # Record some initial events
    from src.events.store import EventStore
    store = EventStore(ws.events_path)
    store.append(
        EventType.RUN_STARTED,
        payload={"run_id": "run-dogfood-01"},
    )

    # Pick a port for testing
    port = 8991
    server = P2PUIServer(workspace=ws, host="127.0.0.1", port=port)
    base_url = server.start(blocking=False)
    time.sleep(0.3)

    yield base_url, ws

    server.stop()


def test_ui_api_endpoints(ui_test_env):
    base_url, ws = ui_test_env

    # 1. Test GET /api/state
    with urllib.request.urlopen(f"{base_url}/api/state") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "events_count" in data
        assert data["events_count"] >= 1

    # 2. Test GET /api/tasks
    with urllib.request.urlopen(f"{base_url}/api/tasks") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["tasks"]) == 2
        task_ids = [t["id"] for t in data["tasks"]]
        assert "UI-001" in task_ids
        assert "AUTH-002" in task_ids

    # 3. Test GET /api/approvals (Both tasks have human_approval=True)
    with urllib.request.urlopen(f"{base_url}/api/approvals") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["approvals"]) == 2

    # 4. Test GET /api/connections
    with urllib.request.urlopen(f"{base_url}/api/connections") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["connections"]) >= 3

    # 5. Test POST /api/approvals/{task_id}/action
    post_data = json.dumps({"action": "approve", "feedback": "LGTM"}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/approvals/AUTH-002/action",
        data=post_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["success"] is True
        assert res["task_id"] == "AUTH-002"

    # 6. Test Static files: / and /static/style.css
    with urllib.request.urlopen(f"{base_url}/") as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "<title>Prompt2Product" in html
        assert 'data-theme="dark"' in html

    with urllib.request.urlopen(f"{base_url}/static/style.css") as resp:
        assert resp.status == 200
        css = resp.read().decode("utf-8")
        assert "--accent-brand:" in css
        assert "--bg-base:" in css
