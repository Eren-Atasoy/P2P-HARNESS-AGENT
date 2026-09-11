"""P2P Web Dashboard HTTP & REST API Server (docs/12 §2.A, docs/08 Faz 10).

Serves the P2P Control Panel SPA and JSON APIs for run overview, task graph,
event stream, human approvals, connections, and retrospectives.
Uses Python's standard library to guarantee zero external dependency runtime.
"""
import http.server
import json
import mimetypes
import os
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Optional

from src.events.projector import project_state
from src.events.store import EventStore
from src.models.task import TaskContract
from src.orchestration.retro import RetroEngine
from src.plugins.registry import plugin_registry
from src.workspace.workspace import Workspace


class P2PUIHandler(http.server.SimpleHTTPRequestHandler):
    """Handles REST API and static asset requests for the P2P Dashboard."""

    workspace: Workspace = None
    store: EventStore = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.static_dir = Path(__file__).parent / "static"
        super().__init__(*args, **kwargs)

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Helper to send JSON response with CORS headers."""
        try:
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def do_OPTIONS(self) -> None:
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Dispatches GET requests to API or static dashboard files."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/state":
            self._handle_get_state()
        elif path == "/api/tasks":
            self._handle_get_tasks()
        elif path == "/api/events":
            self._handle_get_events()
        elif path == "/api/approvals":
            self._handle_get_approvals()
        elif path == "/api/connections":
            self._handle_get_connections()
        elif path == "/api/retro":
            self._handle_get_retro()
        else:
            self._handle_static_files(path)

    def do_POST(self) -> None:
        """Dispatches POST actions for approvals, tasks, runs, and retro."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if path.startswith("/api/approvals/") and path.endswith("/action"):
            parts = path.strip("/").split("/")
            task_id = parts[2]
            self._handle_approval_action(task_id, payload)
        elif path == "/api/approvals/simulate":
            self._handle_simulate_approval(payload)
        elif path == "/api/retro/apply":
            self._handle_retro_apply(payload)
        elif path == "/api/retro/scan":
            self._handle_retro_scan(payload)
        elif path.startswith("/api/tasks/") and path.endswith("/status"):
            parts = path.strip("/").split("/")
            task_id = parts[2]
            self._handle_task_status_update(task_id, payload)
        elif path.startswith("/api/tasks/") and path.endswith("/directive"):
            parts = path.strip("/").split("/")
            task_id = parts[2]
            self._handle_task_directive(task_id, payload)
        elif path.startswith("/api/tasks/") and path.endswith("/toggle_approval"):
            parts = path.strip("/").split("/")
            task_id = parts[2]
            self._handle_task_toggle_approval(task_id, payload)
        elif path == "/api/run/new":
            self._handle_run_new(payload)
        elif path == "/api/run/start":
            self._handle_run_start(payload)
        else:
            self._send_json({"error": "Not Found"}, status=404)

    # --- API Handlers ---

    def _handle_get_state(self) -> None:
        events = self.store.read_all() if self.store else []
        state = project_state(events) if events else None

        data = {
            "workspace": str(self.workspace.root_path) if self.workspace else "",
            "events_count": len(events),
            "state": state.model_dump() if state else {
                "tasks": {},
                "waves": [],
                "acr_log": [],
                "decisions": [],
                "blockages": [],
            },
        }
        self._send_json(data)

    def _handle_get_tasks(self) -> None:
        tasks = []
        if self.workspace and self.workspace.tasks_dir.exists():
            for task_file in sorted(self.workspace.tasks_dir.glob("*.json")):
                try:
                    t_data = json.loads(task_file.read_text(encoding="utf-8"))
                    tasks.append(t_data)
                except Exception:
                    pass
        self._send_json({"tasks": tasks})

    def _handle_get_events(self) -> None:
        events = []
        if self.store:
            for ev in self.store.read_all():
                events.append(ev.model_dump())
        self._send_json({"events": events})

    def _handle_get_approvals(self) -> None:
        approvals = []
        if self.workspace and self.workspace.tasks_dir.exists():
            for task_file in sorted(self.workspace.tasks_dir.glob("*.json")):
                try:
                    t_data = json.loads(task_file.read_text(encoding="utf-8"))
                    is_pending = t_data.get("status") not in ("APPROVED", "COMPLETED", "REJECTED")
                    if is_pending and (t_data.get("human_approval") or t_data.get("risk") == "high"):
                        approvals.append(t_data)
                except Exception:
                    pass
        self._send_json({"approvals": approvals})

    def _handle_approval_action(self, task_id: str, payload: dict[str, Any]) -> None:
        action = payload.get("action", "approve")  # approve | reject | steer
        feedback = payload.get("feedback", "")

        # Record decision event if store exists
        if self.store:
            from src.models.enums import EventType
            self.store.append(
                EventType.DECISION_RECORDED,
                payload={
                    "action": action,
                    "feedback": feedback,
                    "decided_by": "human",
                },
                task_id=task_id,
            )

        # Update task file on disk
        if self.workspace and self.workspace.tasks_dir.exists():
            task_file = self.workspace.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                try:
                    t_dict = json.loads(task_file.read_text(encoding="utf-8"))
                    if action == "approve":
                        t_dict["human_approval"] = False
                        t_dict["status"] = "APPROVED"
                    elif action == "reject":
                        t_dict["status"] = "REJECTED"
                    elif action == "steer":
                        existing_notes = t_dict.get("notes") or ""
                        t_dict["notes"] = f"{existing_notes}\n[STEER DIRECTIVE]: {feedback}".strip()
                    task_file.write_text(json.dumps(t_dict, indent=2), encoding="utf-8")
                except Exception:
                    pass

        self._send_json({
            "success": True,
            "task_id": task_id,
            "action": action,
            "message": f"Action '{action}' successfully recorded for task {task_id}.",
        })

    def _handle_task_status_update(self, task_id: str, payload: dict[str, Any]) -> None:
        new_status = payload.get("status", "COMPLETED")
        if self.workspace and self.workspace.tasks_dir.exists():
            task_file = self.workspace.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                try:
                    t_dict = json.loads(task_file.read_text(encoding="utf-8"))
                    t_dict["status"] = new_status
                    task_file.write_text(json.dumps(t_dict, indent=2), encoding="utf-8")
                    if self.store:
                        from src.models.enums import EventType
                        self.store.append(
                            EventType.TASK_STATUS_CHANGED,
                            payload={"status": new_status},
                            task_id=task_id,
                        )
                    self._send_json({"success": True, "task_id": task_id, "status": new_status})
                    return
                except Exception as err:
                    self._send_json({"success": False, "error": str(err)}, status=500)
                    return
        self._send_json({"success": False, "error": f"Task {task_id} not found"}, status=404)

    def _handle_task_directive(self, task_id: str, payload: dict[str, Any]) -> None:
        directive = payload.get("directive", "").strip()
        if not directive:
            self._send_json({"success": False, "error": "Directive cannot be empty"}, status=400)
            return

        if self.workspace and self.workspace.tasks_dir.exists():
            task_file = self.workspace.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                try:
                    t_dict = json.loads(task_file.read_text(encoding="utf-8"))
                    existing = t_dict.get("notes") or ""
                    t_dict["notes"] = f"{existing}\n[DIRECTIVE]: {directive}".strip()
                    task_file.write_text(json.dumps(t_dict, indent=2), encoding="utf-8")
                    if self.store:
                        from src.models.enums import EventType
                        self.store.append(
                            EventType.DECISION_RECORDED,
                            payload={"directive": directive, "decided_by": "human"},
                            task_id=task_id,
                        )
                    self._send_json({"success": True, "task_id": task_id, "notes": t_dict["notes"]})
                    return
                except Exception as err:
                    self._send_json({"success": False, "error": str(err)}, status=500)
                    return
        self._send_json({"success": False, "error": f"Task {task_id} not found"}, status=404)

    def _handle_task_toggle_approval(self, task_id: str, payload: dict[str, Any]) -> None:
        human_approval = bool(payload.get("human_approval", True))
        if self.workspace and self.workspace.tasks_dir.exists():
            task_file = self.workspace.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                try:
                    t_dict = json.loads(task_file.read_text(encoding="utf-8"))
                    t_dict["human_approval"] = human_approval
                    task_file.write_text(json.dumps(t_dict, indent=2), encoding="utf-8")
                    self._send_json({"success": True, "task_id": task_id, "human_approval": human_approval})
                    return
                except Exception as err:
                    self._send_json({"success": False, "error": str(err)}, status=500)
                    return
        self._send_json({"success": False, "error": f"Task {task_id} not found"}, status=404)

    def _handle_simulate_approval(self, payload: dict[str, Any]) -> None:
        if not self.workspace:
            self._send_json({"success": False, "error": "Workspace not configured"}, status=500)
            return

        self.workspace.ensure_directories()
        sim_id = f"SEC-{int(time.time()) % 1000:03d}"
        sim_task = {
            "id": sim_id,
            "title": "Migrate Production DB & Rotate JWT Secret",
            "capabilities": ["database", "backend"],
            "risk": "high",
            "depends_on": [],
            "intent": "Critical migration and secret rotation requiring human sign-off before proceeding.",
            "acceptance_criteria": [
                {
                    "id": "AC-1",
                    "statement": "Database migration executed and verified safely",
                    "verified_by": "gate",
                    "gate_ref": "security_audit",
                }
            ],
            "inputs": ["database/schema.sql"],
            "allowed_paths": ["src/db/**", "alembic/**"],
            "forbidden_paths": [".env.production", "secrets/**"],
            "gates": ["security_audit", "pytest_suite"],
            "estimated_size": "M",
            "max_attempts": 3,
            "human_approval": True,
            "result_path": f".p2p/results/{sim_id}.json",
            "acr_path": f".p2p/acr/{sim_id}.json",
            "notes": "Awaiting human review in UI dashboard",
            "status": "PENDING_APPROVAL",
        }

        task_path = self.workspace.tasks_dir / f"{sim_id}.json"
        task_path.write_text(json.dumps(sim_task, indent=2), encoding="utf-8")

        if self.store:
            from src.models.enums import EventType
            self.store.append(
                EventType.TASK_DISCOVERED,
                payload={"simulated": True, "risk": "high"},
                task_id=sim_id,
            )

        self._send_json({"success": True, "task_id": sim_id, "task": sim_task})

    def _handle_get_connections(self) -> None:
        connections = []
        for name in plugin_registry.list_runtimes():
            adapter = plugin_registry.get_runtime(name)
            doc = adapter.doctor(name) if adapter else None
            feat = adapter.features() if adapter else None
            connections.append({
                "id": name,
                "kind": "api" if name == "api" else ("local" if name == "ollama" else "cli"),
                "available": doc.available if doc else False,
                "authenticated": doc.authenticated if doc else False,
                "version": doc.version if doc else "N/A",
                "can_stream": feat.can_stream if feat else False,
            })
        self._send_json({"connections": connections})

    def _handle_get_retro(self) -> None:
        if not self.workspace or not self.store:
            self._send_json({"recommendations": []})
            return

        engine = RetroEngine(self.workspace, self.store)
        recs = engine.analyze_events(self.store.read_all())
        self._send_json({
            "recommendations": [r.model_dump() for r in recs]
        })

    def _handle_retro_apply(self, payload: dict[str, Any]) -> None:
        rec_id = payload.get("id")
        if not self.workspace or not self.store or not rec_id:
            self._send_json({"success": False, "error": "Missing recommendation ID"}, status=400)
            return

        engine = RetroEngine(self.workspace, self.store)
        recs = engine.analyze_events(self.store.read_all())
        matching = [r for r in recs if r.id == rec_id]
        if not matching:
            self._send_json({"success": False, "error": f"Recommendation {rec_id} not found"}, status=404)
            return

        engine.apply_recommendation(matching[0])
        self._send_json({"success": True, "applied_id": rec_id})

    def _handle_retro_scan(self, payload: dict[str, Any]) -> None:
        if not self.workspace or not self.store:
            self._send_json({"success": True, "recommendations": []})
            return

        engine = RetroEngine(self.workspace, self.store)
        recs = engine.analyze_events(self.store.read_all())
        self._send_json({
            "success": True,
            "recommendations": [r.model_dump() for r in recs],
        })

    def _handle_run_new(self, payload: dict[str, Any]) -> None:
        prompt = payload.get("prompt", "").strip()
        bp_name = payload.get("blueprint", "fastapi")
        autonomy = payload.get("autonomy", "guarded")

        if not prompt:
            self._send_json({"success": False, "error": "Prompt cannot be empty"}, status=400)
            return

        try:
            from src.models.enums import AutonomyLevel
            from src.planning.discovery import DiscoveryEngine
            from src.planning.architect import ArchitecturePlanner
            from src.planning.decomposer import TaskDecomposer

            self.workspace.ensure_directories()
            if not self.store:
                self.store = EventStore(self.workspace.events_path)

            autonomy_level = AutonomyLevel(autonomy.lower())

            discovery = DiscoveryEngine(self.workspace, self.store)
            spec, decisions, _ = discovery.discover(prompt, autonomy_level=autonomy_level)

            architect = ArchitecturePlanner(self.workspace, self.store)
            _, adrs, _, _ = architect.plan_architecture(spec, autonomy_level=autonomy_level, approved_by_user=True)

            decomposer = TaskDecomposer(self.workspace, self.store)
            graph, _, _ = decomposer.decompose(spec, autonomy_level=autonomy_level, approved_by_user=True)

            bp = plugin_registry.get_blueprint(bp_name)
            if bp:
                bp.generate_scaffold(self.workspace, spec)
                bp.generate_infra(self.workspace, spec)
                bp.generate_tests(self.workspace, spec)

            self._send_json({
                "success": True,
                "project_name": spec.name,
                "tasks_count": len(graph.tasks),
                "adrs_count": len(adrs),
            })
        except Exception as err:
            self._send_json({"success": False, "error": str(err)}, status=500)

    def _handle_run_start(self, payload: dict[str, Any]) -> None:
        try:
            from src.models.enums import AutonomyLevel
            from src.orchestration.engine import OrchestratorEngine
            from src.orchestration.graph import TaskGraph
            from src.orchestration.router import CapabilityRouter
            from src.runtime.mock import MockRuntime
            from src.verification.config import GatesConfig
            from src.verification.runner import GateRunner
            from src.models.connection import Connection
            from src.models.enums import ConnectionKind, RuntimeType, Capability

            graph = TaskGraph()
            if self.workspace and self.workspace.tasks_dir.exists():
                for t_file in self.workspace.tasks_dir.glob("*.json"):
                    try:
                        t_data = json.loads(t_file.read_text(encoding="utf-8"))
                        clean_data = {k: v for k, v in t_data.items() if k != "status"}
                        graph.add_task(TaskContract.model_validate(clean_data))
                    except Exception:
                        pass

            if not graph.tasks:
                self._send_json({"success": False, "error": "No tasks found to run. Plan project first."}, status=400)
                return

            conn = Connection(
                id="default-local",
                kind=ConnectionKind.LOCAL,
                runtime=RuntimeType.MOCK,
                credential_ref="env:DEFAULT",
                capabilities=[Capability.BACKEND, Capability.FRONTEND, Capability.DATABASE, Capability.ARCHITECTURE, Capability.PLANNING],
            )
            router = CapabilityRouter(connections=[conn])
            runtime = MockRuntime()
            gate_runner = GateRunner(workspace=self.workspace, gates_config=GatesConfig.default_gates())

            engine = OrchestratorEngine(
                workspace=self.workspace,
                graph=graph,
                router=router,
                runtime=runtime,
                event_store=self.store,
                gate_runner=gate_runner,
                enable_git=False,
            )

            # Run in separate thread so UI server stays responsive
            t = threading.Thread(target=engine.run_loop, daemon=True)
            t.start()

            self._send_json({"success": True, "message": "Autonomous orchestrator loop started."})
        except Exception as err:
            self._send_json({"success": False, "error": str(err)}, status=500)

    # --- Static File Serving ---

    def _handle_static_files(self, path: str) -> None:
        if path == "/" or not path or path == "/index.html":
            file_path = self.static_dir / "index.html"
        else:
            rel_path = path.lstrip("/")
            if rel_path.startswith("static/"):
                rel_path = rel_path[len("static/"):]
            file_path = self.static_dir / rel_path

        if not file_path.exists() or not file_path.is_file():
            # SPA Fallback to index.html
            file_path = self.static_dir / "index.html"

        if not file_path.exists():
            self.send_error(404, "Static dashboard asset not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "text/html"

        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception as e:
            try:
                self.send_error(500, f"Error reading asset: {e}")
            except Exception:
                pass


class RobustThreadingHTTPServer(http.server.ThreadingHTTPServer):
    """Threading HTTPServer that gracefully suppresses client abort exceptions on Windows/POSIX."""
    daemon_threads = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        import sys
        exc_type, _, _ = sys.exc_info()
        if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # Client closed connection abruptly (e.g. browser refresh/tab close/polling abort)
            return
        super().handle_error(request, client_address)


class P2PUIServer:
    """Controls the lifecycle of the P2P UI HTTP Server."""

    def __init__(self, workspace: Workspace, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.workspace = workspace
        self.host = host
        self.port = port
        self.server: Optional[RobustThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = False) -> str:
        """Starts the UI server and returns the web URL."""
        handler_cls = P2PUIHandler
        handler_cls.workspace = self.workspace
        events_path = self.workspace.events_path
        handler_cls.store = EventStore(events_path) if events_path.exists() else None

        self.server = RobustThreadingHTTPServer((self.host, self.port), handler_cls)
        url = f"http://{self.host}:{self.port}"

        if blocking:
            self.server.serve_forever()
        else:
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()

        return url

    def stop(self) -> None:
        """Shuts down the UI server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
