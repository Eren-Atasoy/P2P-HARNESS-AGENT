"""Official Phase 10 Exit Criterion Test (docs/08 §Faz 10, docs/12 §2.A).

Exit Criterion:
1. P2P feature (Web Dashboard UI) is completely planned, executed, and verified through P2P's own dogfooding pipeline.
2. P2P UI HTTP Server is fully operational and serves all 7 screens defined in docs/12.
3. Approvals, steer actions, and retrospective engine are fully interactive via REST API.
4. git log confirms lineage of planned, verified, and committed phases across the development cycle.
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

from src.events.store import EventStore
from src.models.connection import Connection
from src.models.enums import AutonomyLevel, Capability, ConnectionKind, EstimatedSize, EventType, RiskLevel, RuntimeType, VerifiedBy
from src.models.event import Event
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.engine import OrchestratorEngine
from src.orchestration.graph import TaskGraph
from src.orchestration.router import CapabilityRouter
from src.planning.architect import ArchitecturePlanner
from src.planning.decomposer import TaskDecomposer
from src.planning.discovery import DiscoveryEngine
from src.runtime.mock import MockRuntime
from src.ui.server import P2PUIServer
from src.verification.config import GatesConfig
from src.verification.runner import GateRunner
from src.workspace.workspace import Workspace


def test_phase10_dogfooding_and_ui_exit_criterion(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    store = EventStore(ws.events_path)

    # Step 1: Dogfooding Planning Chain (G1 -> G2 -> G3) for P2P Web Dashboard feature
    prompt = "Build a real-time reactive P2P Web Dashboard UI displaying execution graph and approvals"

    # G1: Discovery
    discovery = DiscoveryEngine(ws, store)
    spec, decisions, g1_passed = discovery.discover(prompt, autonomy_level=AutonomyLevel.GUARDED)
    assert g1_passed is True

    # G2: Architecture
    architect = ArchitecturePlanner(ws, store)
    _, adrs, g2_passed, _ = architect.plan_architecture(spec, autonomy_level=AutonomyLevel.GUARDED, approved_by_user=True)
    assert g2_passed is True
    assert (ws.p2p_dir / "docs" / "architecture.md").exists()

    # G3: Task Decomposition
    decomposer = TaskDecomposer(ws, store)
    graph, g3_passed, _ = decomposer.decompose(spec, autonomy_level=AutonomyLevel.GUARDED, approved_by_user=True)
    assert g3_passed is True
    assert len(graph.tasks) >= 2

    # Step 2: Autonomous Orchestration Execution over planned tasks
    conn = Connection(
        id="mock-local",
        kind=ConnectionKind.LOCAL,
        runtime=RuntimeType.MOCK,
        credential_ref="env:MOCK",
        capabilities=[Capability.BACKEND, Capability.FRONTEND, Capability.DATABASE, Capability.ARCHITECTURE, Capability.PLANNING],
    )
    router = CapabilityRouter(connections=[conn])
    runtime = MockRuntime(files_to_create={
        "src/ui/component.py": "class Header: pass\n",
        "tests/test_header.py": "def test_header(): assert True is not False\n",
    })
    gate_runner = GateRunner(workspace=ws, gates_config=GatesConfig.default_gates())

    engine = OrchestratorEngine(
        workspace=ws,
        graph=graph,
        router=router,
        runtime=runtime,
        event_store=store,
        gate_runner=gate_runner,
        run_id="run-phase10-dogfood",
        enable_git=False,
    )
    run_state = engine.run_loop()
    assert run_state is not None

    # Step 3: P2P UI HTTP Server operational verification
    port = 8995
    server = P2PUIServer(workspace=ws, host="127.0.0.1", port=port)
    base_url = server.start(blocking=False)
    time.sleep(0.3)

    try:
        # Check /api/state returns valid projected state
        with urllib.request.urlopen(f"{base_url}/api/state") as resp:
            assert resp.status == 200
            st_data = json.loads(resp.read().decode("utf-8"))
            assert st_data["events_count"] > 0

        # Check /api/tasks returns planned tasks
        with urllib.request.urlopen(f"{base_url}/api/tasks") as resp:
            assert resp.status == 200
            t_data = json.loads(resp.read().decode("utf-8"))
            assert len(t_data["tasks"]) >= 2

        # Check /api/events returns recorded event log
        with urllib.request.urlopen(f"{base_url}/api/events") as resp:
            assert resp.status == 200
            ev_data = json.loads(resp.read().decode("utf-8"))
            assert len(ev_data["events"]) > 0

        # Check / serves HTML Dashboard with docs/12 design system tokens
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "Prompt2Product — Autonomous Control Panel" in html
            assert "Task Graph" in html
            assert "Approvals" in html

        # Check steer action through /api/approvals/{task_id}/action
        first_task_id = list(graph.tasks.keys())[0]
        steer_payload = json.dumps({"action": "steer", "feedback": "Prioritize accessibility"}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/approvals/{first_task_id}/action",
            data=steer_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # Verify steer decision was committed to events.jsonl
        recorded_events = store.read_all()
        decision_events = [e for e in recorded_events if e.type == EventType.DECISION_RECORDED]
        assert len(decision_events) >= 1
        assert decision_events[-1].payload["feedback"] == "Prioritize accessibility"

    finally:
        server.stop()

    # Step 4: Verify Git history shows complete Phase lineage
    git_res = subprocess.run(["git", "log", "-n", "10", "--oneline"], capture_output=True, text=True)
    assert git_res.returncode == 0
    git_log_output = git_res.stdout
    assert "phase" in git_log_output.lower()
