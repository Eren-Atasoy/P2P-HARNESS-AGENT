"""Official Exit Criterion Test for Faz 6: Planning Chain.

Per docs/08-roadmap.md §Faz 6:
'Çıkış: p2p new "basit bir yapılacaklar API\'si" sonucunda onaylanmış bir task graph.'
"""
import json
from pathlib import Path
from typer.testing import CliRunner

from src.cli.main import app
from src.events.projector import project_state
from src.events.store import EventStore
from src.models.enums import EstimatedSize, EventType, RiskLevel, TargetType
from src.models.project import ProjectSpec
from src.models.task import TaskContract
from src.orchestration.graph import TaskGraph
from src.workspace.workspace import Workspace

runner = CliRunner()


def test_phase6_official_exit_criterion(tmp_path: Path):
    """
    Executes 'p2p new' on a fresh workspace with the canonical prompt
    'basit bir yapılacaklar API\'si' and proves:
    1. CLI finishes with exit code 0.
    2. .p2p/project.json is generated conforming to ProjectSpec.
    3. .p2p/docs/architecture.md and ADR-001 exist.
    4. Atomic TaskContracts exist on disk under .p2p/tasks/*.json.
    5. No task has EstimatedSize.L (invariant).
    6. All tasks form a cycle-free DAG with computed waves.
    7. Events are recorded cleanly in .p2p/events.jsonl and projectable to state.
    """
    workspace_dir = tmp_path / "todo_project"
    prompt = "basit bir yapılacaklar API'si"

    # Run the CLI command: p2p new
    result = runner.invoke(
        app,
        ["new", prompt, "--workspace", str(workspace_dir), "--autonomy", "guarded", "--approve"],
    )

    assert result.exit_code == 0, f"CLI failed with error: {result.stdout}"
    assert "Planning chain completed successfully!" in result.stdout

    ws = Workspace(workspace_dir)

    # 1. Verify ProjectSpec
    assert ws.project_spec_path.exists(), "project.json must exist"
    project_data = json.loads(ws.project_spec_path.read_text(encoding="utf-8"))
    spec = ProjectSpec.model_validate(project_data)
    assert spec.prompt == prompt
    assert TargetType.API in spec.targets
    assert spec.stack["backend"] == "fastapi"

    # 2. Verify Architecture Documentation and ADR
    arch_doc = ws.p2p_docs_dir / "architecture.md"
    assert arch_doc.exists(), "architecture.md must exist"
    arch_text = arch_doc.read_text(encoding="utf-8")
    assert "## 2. Component Boundaries" in arch_text
    assert "## 4. API Endpoints" in arch_text

    adr_files = list((ws.p2p_docs_dir / "adr").glob("*.md"))
    assert len(adr_files) >= 1, "At least one ADR must be generated"

    # 3. Verify Task Contracts and TaskGraph validity
    task_files = list(ws.tasks_dir.glob("*.json"))
    assert len(task_files) >= 3, "At least 3 atomic tasks should be generated"

    graph = TaskGraph()
    for tf in task_files:
        task_dict = json.loads(tf.read_text(encoding="utf-8"))
        contract = TaskContract.model_validate(task_dict)
        graph.add_task(contract)

        # Invariants
        assert contract.estimated_size in (EstimatedSize.S, EstimatedSize.M)
        assert contract.estimated_size != EstimatedSize.L
        assert len(contract.acceptance_criteria) >= 1
        assert len(contract.allowed_paths) >= 1
        assert contract.risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)

    # Validate DAG (Zero cycles, all dependencies satisfied)
    graph.validate()
    waves = graph.compute_waves()
    assert len(waves) >= 2, "Tasks must be organized into parallel/sequential waves"

    # 4. Verify Event Log and Projected State
    assert ws.events_path.exists(), "events.jsonl must exist"
    store = EventStore(ws.events_path)
    events = store.read_all()
    assert len(events) >= 5

    state = project_state(events)
    assert state.project_name == spec.name
    assert len(state.tasks) == len(graph.tasks)

    # Verify decisions exist
    assert len(state.decisions) >= 1
