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
from src.models.enums import DecidedBy, DecisionKind, EventType
from src.runtime.claude import ClaudeCodeRuntime
from src.runtime.gemini import GeminiCliRuntime
from src.runtime.mock import MockRuntime

app = typer.Typer(help="Prompt2Product — Autonomous, model-agnostic, local-first software engineering platform")
console = Console()


@app.command()
def version():
    """Prints Prompt2Product version."""
    console.print(f"[bold cyan]Prompt2Product[/bold cyan] version [green]{__version__}[/green]")


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


if __name__ == "__main__":
    app()
