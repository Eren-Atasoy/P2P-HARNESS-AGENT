"""Prompt2Product CLI interface powered by Typer and Rich."""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src import __version__
from src.events.projector import project_state
from src.events.store import EventStore
from src.models.decision import Decision
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, EventType
from src.planning.architect import ArchitecturePlanner
from src.planning.decomposer import TaskDecomposer
from src.planning.discovery import DiscoveryEngine
from src.runtime.claude import ClaudeCodeRuntime
from src.runtime.gemini import GeminiCliRuntime
from src.runtime.mock import MockRuntime
from src.workspace.workspace import Workspace

app = typer.Typer(help="Prompt2Product — Autonomous, model-agnostic, local-first software engineering platform")
console = Console()


@app.command()
def version():
    """Prints Prompt2Product version."""
    console.print(f"[bold cyan]Prompt2Product[/bold cyan] version [green]{__version__}[/green]")


@app.command()
def new(
    prompt: str = typer.Argument(..., help="Natural language product description or requirements"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Target workspace root directory"),
    blueprint: str = typer.Option("fastapi", "--blueprint", "-b", help="Project blueprint: fastapi | python_cli"),
    autonomy: str = typer.Option("guarded", "--autonomy", "-a", help="Autonomy level: supervised | guarded | full"),
    approve: bool = typer.Option(False, "--approve", help="Explicitly approve project gates G1, G2, G3"),
):
    """Initializes a new project from a prompt through the planning chain (G1 -> G2 -> G3)."""
    console.print(Panel(f"[bold cyan]Prompt2Product Planning Chain[/bold cyan]\nPrompt: [white]{prompt}[/white]\nBlueprint: [cyan]{blueprint}[/cyan]", border_style="cyan"))

    ws = Workspace(workspace)
    ws.ensure_directories()
    store = EventStore(ws.events_path)

    try:
        autonomy_level = AutonomyLevel(autonomy.lower())
    except ValueError:
        console.print(f"[bold red]Invalid autonomy level:[/bold red] '{autonomy}'. Use supervised, guarded, or full.")
        raise typer.Exit(code=1)

    # Step 1: Discovery (G1)
    console.print("[dim]1/3 Running DiscoveryEngine and ambiguity extraction (Gate G1)...[/dim]")
    discovery = DiscoveryEngine(ws, store)
    spec, decisions, g1_passed = discovery.discover(prompt, autonomy_level=autonomy_level)
    g1_status = "[green]PASSED[/green]" if g1_passed else "[yellow]AWAITING APPROVAL[/yellow]"
    console.print(f"    Project Name: [bold white]{spec.name}[/bold white] | G1: {g1_status}")

    # Step 2: Architecture Planning (G2)
    console.print("[dim]2/3 Running ArchitecturePlanner and ADR generation (Gate G2)...[/dim]")
    architect = ArchitecturePlanner(ws, store)
    _, adrs, g2_passed, _ = architect.plan_architecture(spec, autonomy_level=autonomy_level, approved_by_user=approve)
    g2_status = "[green]PASSED[/green]" if g2_passed else "[yellow]AWAITING APPROVAL[/yellow]"
    console.print(f"    Architecture: [bold white].p2p/docs/architecture.md[/bold white] | ADRs: {len(adrs)} | G2: {g2_status}")

    # Step 3: Task Decomposition (G3)
    console.print("[dim]3/3 Running TaskDecomposer and DAG validation (Gate G3)...[/dim]")
    decomposer = TaskDecomposer(ws, store)
    graph, g3_passed, _ = decomposer.decompose(spec, autonomy_level=autonomy_level, approved_by_user=approve)
    g3_status = "[green]PASSED[/green]" if g3_passed else "[yellow]AWAITING APPROVAL[/yellow]"
    console.print(f"    Tasks Created: [bold white]{len(graph.tasks)}[/bold white] | G3: {g3_status}")

    # Tasks summary table
    table = Table(title=f"Planned Tasks for {spec.name}", border_style="dim")
    table.add_column("Task ID", style="bold white")
    table.add_column("Title")
    table.add_column("Risk")
    table.add_column("Depends On")
    table.add_column("Allowed Paths")

    for tid, t in graph.tasks.items():
        risk_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(t.risk.value, "white")
        table.add_row(
            t.id,
            t.title,
            f"[{risk_color}]{t.risk.value}[/{risk_color}]",
            ", ".join(t.depends_on) or "-",
            ", ".join(t.allowed_paths[:2]),
        )
    console.print(table)

    # Step 4: Blueprint Scaffolding & Infrastructure (Faz 7 & 9)
    from src.plugins.registry import plugin_registry
    bp_instance = plugin_registry.get_blueprint(blueprint)
    if not bp_instance:
        console.print(f"[bold red]Unknown blueprint:[/bold red] '{blueprint}'. Available: {', '.join(plugin_registry.list_blueprints())}")
        raise typer.Exit(code=1)

    scaffold = bp_instance.generate_scaffold(ws, spec)
    infra = bp_instance.generate_infra(ws, spec)
    tests = bp_instance.generate_tests(ws, spec)
    console.print(f"[dim]Scaffolded {len(scaffold)} source files, {len(infra)} infra files, {len(tests)} test files using [{blueprint}] blueprint.[/dim]")

    console.print("[bold green]Planning chain completed successfully![/bold green] Ready to run: [cyan]p2p run[/cyan]")


@app.command()
def run(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root containing .p2p directory"),
    autonomy: str = typer.Option("guarded", "--autonomy", "-a", help="Autonomy level: supervised | guarded | full"),
):
    """Executes the autonomous loop over planned tasks (docs/03 §7)."""
    from src.events.store import EventStore
    from src.orchestration.engine import OrchestratorEngine
    from src.orchestration.graph import TaskGraph
    from src.orchestration.router import TaskRouter
    from src.runtime.mock import MockRuntime
    from src.verification.config import default_gates
    from src.verification.runner import GateRunner

    ws = Workspace(workspace)
    if not ws.p2p_dir.exists():
        console.print(f"[red]No .p2p directory found at {workspace}. Run 'p2p new' first.[/red]")
        raise typer.Exit(code=1)

    try:
        autonomy_level = AutonomyLevel(autonomy.lower())
    except ValueError:
        console.print(f"[red]Invalid autonomy level:[/red] '{autonomy}'. Use supervised, guarded, or full.")
        raise typer.Exit(code=1)

    console.print(Panel(f"[bold cyan]Prompt2Product Autonomous Run[/bold cyan]\nAutonomy: [white]{autonomy_level.value}[/white]", border_style="cyan"))

    # Load tasks into graph
    graph = TaskGraph()
    for task_file in ws.tasks_dir.glob("*.json"):
        import json
        from src.models.task import TaskContract
        task_data = json.loads(task_file.read_text(encoding="utf-8"))
        graph.add_task(TaskContract.model_validate(task_data))

    store = EventStore(ws.events_path)
    router = TaskRouter(routing_config={})
    runtime = MockRuntime()
    gate_runner = GateRunner(default_gates(), workspace_root=ws.root_path)

    engine = OrchestratorEngine(
        workspace=ws,
        task_graph=graph,
        router=router,
        runtime=runtime,
        gate_runner=gate_runner,
        event_store=store,
        autonomy_level=autonomy_level,
    )

    exit_reason = engine.run_loop()
    status_style = "green" if exit_reason.value == "COMPLETED" else "yellow"
    console.print(f"Loop exited: [{status_style}]{exit_reason.value}[/{status_style}]")


@app.command()
def doctor():
    """Runs diagnostics on runtime adapters and CLI connections (docs/04 §4)."""
    console.print(Panel("[bold cyan]Prompt2Product Runtime Doctor[/bold cyan]", border_style="cyan"))

    adapters = [
        ("claude-code", ClaudeCodeRuntime()),
        ("gemini-cli", GeminiCliRuntime()),
        ("mock-local", MockRuntime()),
    ]

    table = Table(title="Connection Diagnostics", border_style="dim")
    table.add_column("Connection ID", style="bold white")
    table.add_column("Available")
    table.add_column("Version")
    table.add_column("Latency (ms)")
    table.add_column("Status")

    for cid, adapter in adapters:
        res = adapter.doctor(connection_id=cid)
        avail_style = "green" if res.available else "red"
        avail_str = f"[{avail_style}]{res.available}[/{avail_style}]"
        latency_str = f"{res.latency_ms:.1f}" if res.latency_ms is not None else "-"
        status_style = "green" if res.available else "yellow"
        status_text = "READY" if res.available else (res.error or "NOT FOUND")

        table.add_row(
            res.connection_id,
            avail_str,
            res.version or "-",
            latency_str,
            f"[{status_style}]{status_text}[/{status_style}]",
        )

    console.print(table)


@app.command()
def steer(
    task_id: str = typer.Argument(..., help="ID of the task to steer (e.g. TASK-001)"),
    guidance: str = typer.Argument(..., help="Human steering instruction or decision"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root containing .p2p directory"),
):
    """Injects a human steering decision into an escalated task (docs/03 §3.5)."""
    p2p_dir = workspace / ".p2p"
    events_path = p2p_dir / "events.jsonl"
    p2p_dir.mkdir(parents=True, exist_ok=True)

    store = EventStore(events_path)

    dec_id = f"DEC-STEER-{task_id}"
    store.append(
        event_type=EventType.DECISION_RECORDED,
        payload={
            "decision_id": dec_id,
            "chosen": guidance,
            "rationale": "Steered by operator via CLI",
            "decided_by": DecidedBy.HUMAN.value,
            "kind": DecisionKind.STEER.value,
        },
        task_id=task_id,
    )
    store.append(
        event_type=EventType.HUMAN_STEERED,
        payload={"guidance": guidance},
        task_id=task_id,
    )
    store.append(
        event_type=EventType.TASK_STATE_CHANGED,
        payload={"to": "READY", "reason": "human_steer"},
        task_id=task_id,
    )

    console.print(
        f"[bold green]Successfully steered task [cyan]{task_id}[/cyan]:[/bold green] '{guidance}'"
    )
    console.print(f"[dim]Decision recorded as {dec_id} (decided_by=human)[/dim]")


@app.command()
def status(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root containing .p2p directory")
):
    """Displays the current projected state from the append-only event log (.p2p/events.jsonl)."""
    p2p_dir = workspace / ".p2p"
    events_path = p2p_dir / "events.jsonl"

    if not events_path.exists():
        console.print(f"[yellow]No event log found at {events_path}. Project not initialized or no events recorded yet.[/yellow]")
        raise typer.Exit(code=0)

    store = EventStore(events_path)
    events = store.read_all()

    if not events:
        console.print(f"[yellow]Event log {events_path} is empty.[/yellow]")
        raise typer.Exit(code=0)

    state = project_state(events)

    # Header Panel
    proj_name = state.project_name or "Unnamed Project"
    run_id = state.run_id or "N/A"
    status_style = "green" if state.status == "COMPLETED" else ("yellow" if state.status == "RUNNING" else "white")

    header_text = (
        f"[bold]Project:[/bold] {proj_name}\n"
        f"[bold]Run ID:[/bold] {run_id}\n"
        f"[bold]Status:[/bold] [{status_style}]{state.status}[/{status_style}]\n"
        f"[bold]Autonomy Level:[/bold] {state.autonomy_level.value}\n"
        f"[bold]Events Processed:[/bold] {state.last_seq}"
    )
    console.print(Panel(header_text, title="[bold cyan]Prompt2Product Status[/bold cyan]", border_style="cyan"))

    # Tasks Table
    if state.tasks:
        table = Table(title="Tasks", border_style="dim")
        table.add_column("Task ID", style="bold white")
        table.add_column("Status")
        table.add_column("Risk")
        table.add_column("Assigned To")
        table.add_column("Attempts")
        table.add_column("Gates")
        table.add_column("ACR")

        for tid, t in state.tasks.items():
            st_color = {
                "COMPLETED": "green",
                "MERGED": "green",
                "RUNNING": "cyan",
                "GATED": "magenta",
                "FIXING": "yellow",
                "ESCALATED": "red",
                "BLOCKED": "red",
                "PENDING": "white",
            }.get(t.status.value, "white")

            risk_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(t.risk.value, "white")
            gates_summary = ", ".join(f"{k}:{v.value}" for k, v in t.gate_status.items()) or "-"

            table.add_row(
                t.id,
                f"[{st_color}]{t.status.value}[/{st_color}]",
                f"[{risk_color}]{t.risk.value}[/{risk_color}]",
                t.assigned_to or "-",
                str(t.attempts),
                gates_summary,
                f"[bold red]{t.acr}[/bold red]" if t.acr else "-",
            )
        console.print(table)
    else:
        console.print("[dim]No tasks recorded in current run.[/dim]")

    # Decisions Table (Rule docs/02 §6: decided_by=default must be highlighted)
    if state.decisions:
        dec_table = Table(title="Decisions & Governance", border_style="dim")
        dec_table.add_column("ID", style="bold white")
        dec_table.add_column("Kind")
        dec_table.add_column("Question")
        dec_table.add_column("Chosen")
        dec_table.add_column("Decided By")

        for d in state.decisions:
            by_style = "bold yellow" if d.decided_by.value == "default" else "green"
            dec_table.add_row(
                d.id,
                d.kind.value,
                d.question[:60] + ("..." if len(d.question) > 60 else ""),
                d.chosen,
                f"[{by_style}]{d.decided_by.value}[/{by_style}]",
            )
        console.print(dec_table)


@app.command()
def issues(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status: OPEN | CLOSED"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root containing .p2p directory"),
):
    """Lists tracked collaboration issues (docs/07 §7)."""
    from src.collaboration.issues import LocalIssueStore
    from src.collaboration.models import IssueStatus

    ws = Workspace(workspace)
    store = LocalIssueStore(ws)

    st_filter = None
    if status:
        try:
            st_filter = IssueStatus(status.upper())
        except ValueError:
            console.print(f"[red]Invalid status:[/red] '{status}'. Use OPEN or CLOSED.")
            raise typer.Exit(code=1)

    issue_list = store.list_issues(status=st_filter)
    if not issue_list:
        console.print("[dim]No issues found matching filter.[/dim]")
        return

    table = Table(title="Collaboration Issues & Backlog", border_style="dim")
    table.add_column("Issue ID", style="bold white")
    table.add_column("Title")
    table.add_column("Severity")
    table.add_column("Status")
    table.add_column("Task ID")
    table.add_column("Labels")

    for iss in issue_list:
        sev_color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "blue"}.get(iss.severity.value, "white")
        st_color = "green" if iss.status == IssueStatus.OPEN else "dim white"
        table.add_row(
            iss.id,
            iss.title,
            f"[{sev_color}]{iss.severity.value}[/{sev_color}]",
            f"[{st_color}]{iss.status.value}[/{st_color}]",
            iss.task_id or "-",
            ", ".join(iss.labels),
        )
    console.print(table)


@app.command()
def pr(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status: OPEN | MERGED | CLOSED"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root containing .p2p directory"),
):
    """Lists tracked Pull Requests (Task PRs & Release PRs) (docs/07 §7)."""
    from src.collaboration.models import PRStatus
    from src.collaboration.pull_requests import LocalPRStore

    ws = Workspace(workspace)
    store = LocalPRStore(ws)

    st_filter = None
    if status:
        try:
            st_filter = PRStatus(status.upper())
        except ValueError:
            console.print(f"[red]Invalid status:[/red] '{status}'. Use OPEN, MERGED, or CLOSED.")
            raise typer.Exit(code=1)

    pr_list = store.list_prs(status=st_filter)
    if not pr_list:
        console.print("[dim]No pull requests found matching filter.[/dim]")
        return

    table = Table(title="Pull Requests (Task & Release)", border_style="dim")
    table.add_column("PR #", style="bold white")
    table.add_column("Title")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Branch Flow")

    for p in pr_list:
        st_color = "green" if p.status == PRStatus.MERGED else ("cyan" if p.status == PRStatus.OPEN else "dim white")
        table.add_row(
            f"#{p.number}",
            p.title,
            p.pr_type.value,
            f"[{st_color}]{p.status.value}[/{st_color}]",
            f"{p.head_branch} -> {p.base_branch}",
        )
    console.print(table)


@app.command()
def retro(
    apply: Optional[str] = typer.Option(None, "--apply", help="ID of recommendation to apply (e.g. REC-001)"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root containing .p2p directory"),
):
    """Analyzes event log to extract repeating failure patterns and synthesize rules/gates (docs/03 §8)."""
    from src.events.store import EventStore
    from src.orchestration.retro import RetroEngine

    ws = Workspace(workspace)
    if not ws.events_path.exists():
        console.print(f"[yellow]No events.jsonl found at {ws.events_path}. Run a project first.[/yellow]")
        raise typer.Exit(code=0)

    store = EventStore(ws.events_path)
    events = store.read_all()

    engine = RetroEngine(ws, store)
    recommendations = engine.analyze_events(events)

    if not recommendations:
        console.print("[green]No systemic failure patterns detected in event history. Clean execution![/green]")
        return

    table = Table(title="Retrospective Failure Patterns & Rule Proposals", border_style="dim")
    table.add_column("ID", style="bold white")
    table.add_column("Kind")
    table.add_column("Pattern")
    table.add_column("Count")
    table.add_column("Recommendation")
    table.add_column("Target File")

    for rec in recommendations:
        kind_color = {"GATE": "bold red", "RULE": "yellow", "ROUTER": "cyan", "DOCS": "blue"}.get(rec.kind, "white")
        table.add_row(
            rec.id,
            f"[{kind_color}]{rec.kind}[/{kind_color}]",
            rec.pattern,
            str(rec.count),
            rec.recommendation,
            rec.target_file,
        )
    console.print(table)

    if apply:
        matching = [r for r in recommendations if r.id == apply]
        if not matching:
            console.print(f"[red]Recommendation '{apply}' not found.[/red]")
            raise typer.Exit(code=1)
        target_rec = matching[0]
        engine.apply_recommendation(target_rec)
        console.print(f"[bold green]Successfully applied {apply}[/bold green] to [white]{target_rec.target_file}[/white]")
        console.print(f"[dim]Recorded RETRO_APPLIED event in .p2p/events.jsonl[/dim]")


@app.command()
def audit(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Root directory to audit"),
):
    """Audits codebase for security secrets, tautological tests, and vendor independence (docs/08 Faz 9)."""
    from src.verification.audit import ProjectAuditor

    target_dir = path.resolve()
    console.print(f"[bold blue]Running P2P Security & Hygiene Audit on:[/bold blue] {target_dir}")

    auditor = ProjectAuditor(target_dir)
    report = auditor.audit()

    if report.issues:
        table = Table(title="Audit Findings", border_style="dim")
        table.add_column("Severity")
        table.add_column("Category")
        table.add_column("Location")
        table.add_column("Message")

        for issue in report.issues:
            sev_style = {
                "CRITICAL": "bold red",
                "HIGH": "red",
                "MEDIUM": "yellow",
                "LOW": "blue",
            }.get(issue.severity, "white")

            table.add_row(
                f"[{sev_style}]{issue.severity}[/{sev_style}]",
                issue.category,
                f"{issue.file}:{issue.line}",
                issue.message,
            )
        console.print(table)

    console.print(
        f"\n[bold]Scanned:[/bold] {report.files_scanned} files | "
        f"[bold red]Critical:[/bold red] {report.critical_count} | "
        f"[red]High:[/red] {report.high_count} | "
        f"[yellow]Medium:[/yellow] {report.medium_count} | "
        f"[blue]Low:[/blue] {report.low_count}"
    )

    if not report.passed:
        console.print("[bold red]Audit FAILED: Critical or High severity issues detected.[/bold red]")
        raise typer.Exit(code=1)
    else:
        console.print("[bold green]Audit PASSED: No critical security or vendor leakage issues found.[/bold green]")


@app.command()
def ui(
    port: int = typer.Option(8080, "--port", "-p", help="Port to serve the dashboard on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to bind to"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not automatically open browser"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Target workspace root directory"),
):
    """Launches the P2P Web Control Panel Dashboard (docs/12 §2.A, docs/08 Faz 10)."""
    import webbrowser
    from src.ui.server import P2PUIServer

    ws = Workspace(workspace)
    ws.ensure_directories()

    server = P2PUIServer(workspace=ws, host=host, port=port)
    url = f"http://{host}:{port}"
    console.print(Panel(
        f"[bold cyan]P2P Web Control Panel[/bold cyan]\n"
        f"URL: [bold green]{url}[/bold green]\n"
        f"Workspace: [white]{ws.root_path}[/white]\n"
        f"Design System: [dim]docs/12 §1 - §2 (Geist, Semantic Tokens, 7 Views)[/dim]",
        border_style="cyan",
    ))

    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    console.print("[dim]Press Ctrl+C to stop the dashboard server...[/dim]")
    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down P2P UI server...[/yellow]")
        server.stop()


if __name__ == "__main__":
    app()
