"""Test interactive UI REST API endpoints (Phase 10 enhancements)."""
import json
import time
import urllib.request
from pathlib import Path

from src.events.store import EventStore
from src.ui.server import P2PUIServer
from src.workspace.workspace import Workspace


def test_ui_interactive_endpoints(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    store = EventStore(ws.events_path)

    port = 8996
    server = P2PUIServer(workspace=ws, host="127.0.0.1", port=port)
    base_url = server.start(blocking=False)
    time.sleep(0.3)

    try:
        # 1. Plan project from natural language prompt
        plan_payload = json.dumps({
            "prompt": "Build a FastAPI Todo API with CRUD endpoints",
            "blueprint": "fastapi",
            "autonomy": "guarded",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/run/new",
            data=plan_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert data["tasks_count"] > 0

        # Verify tasks are returned via /api/tasks
        with urllib.request.urlopen(f"{base_url}/api/tasks") as resp:
            t_data = json.loads(resp.read().decode("utf-8"))
            tasks = t_data["tasks"]
            assert len(tasks) > 0
            first_task_id = tasks[0]["id"]

        # 2. Update task status directly from UI
        status_payload = json.dumps({"status": "RUNNING"}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/tasks/{first_task_id}/status",
            data=status_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            s_data = json.loads(resp.read().decode("utf-8"))
            assert s_data["success"] is True
            assert s_data["status"] == "RUNNING"

        # 3. Inject Steer Directive to task
        dir_payload = json.dumps({"directive": "Use SQLite in WAL mode"}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/tasks/{first_task_id}/directive",
            data=dir_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            d_data = json.loads(resp.read().decode("utf-8"))
            assert d_data["success"] is True
            assert "Use SQLite in WAL mode" in d_data["notes"]

        # 4. Toggle human approval
        toggle_payload = json.dumps({"human_approval": True}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/tasks/{first_task_id}/toggle_approval",
            data=toggle_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            tog_data = json.loads(resp.read().decode("utf-8"))
            assert tog_data["success"] is True
            assert tog_data["human_approval"] is True

        # 5. Simulate high-risk approval task
        sim_req = urllib.request.Request(
            f"{base_url}/api/approvals/simulate",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(sim_req) as resp:
            assert resp.status == 200
            sim_data = json.loads(resp.read().decode("utf-8"))
            assert sim_data["success"] is True
            sim_id = sim_data["task_id"]

        # Verify sim task appears in /api/approvals
        with urllib.request.urlopen(f"{base_url}/api/approvals") as resp:
            app_data = json.loads(resp.read().decode("utf-8"))
            app_ids = [a["id"] for a in app_data["approvals"]]
            assert sim_id in app_ids

        # 6. Approve the simulated task
        app_req = urllib.request.Request(
            f"{base_url}/api/approvals/{sim_id}/action",
            data=json.dumps({"action": "approve"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(app_req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # 7. Retro scan
        scan_req = urllib.request.Request(
            f"{base_url}/api/retro/scan",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(scan_req) as resp:
            assert resp.status == 200
            scan_data = json.loads(resp.read().decode("utf-8"))
            assert scan_data["success"] is True

        # 8. Start autonomous run loop
        start_req = urllib.request.Request(
            f"{base_url}/api/run/start",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(start_req) as resp:
                assert resp.status == 200
                start_data = json.loads(resp.read().decode("utf-8"))
                assert start_data["success"] is True
        except urllib.error.HTTPError as e:
            print("RUN START ERROR:", e.code, e.read().decode("utf-8"))
            raise

    finally:
        server.stop()
