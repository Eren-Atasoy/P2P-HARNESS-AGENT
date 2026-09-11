"""Architecture Change Request (ACR) Manager (docs/03 §4, docs/08 §Faz 6).

Handles opening, parsing, architect review, resolution (ACCEPTED, REJECTED, DEFERRED),
and graph adjustments for ACRs.
"""
from pathlib import Path
from typing import Optional

from src.events.store import EventStore
from src.models.enums import Capability, EstimatedSize, EventType, RiskLevel, VerifiedBy
from src.models.event import Event
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.graph import TaskGraph
from src.workspace.workspace import Workspace


class ACRManager:
    """Manages the full lifecycle of Architecture Change Requests."""

    def __init__(self, workspace: Workspace, event_store: Optional[EventStore] = None):
        self.workspace = workspace
        self.event_store = event_store

    def open_acr(
        self,
        task_id: str,
        acr_id: str,
        title: str,
        observation: str,
        proposed_change: str,
        conflict: str = ".p2p/docs/architecture.md",
        workaround_possible: bool = False,
    ) -> Path:
        """Creates a standardized ACR file on disk and emits ACR_OPENED event."""
        self.workspace.ensure_directories()
        acr_dir = self.workspace.acr_dir
        acr_dir.mkdir(parents=True, exist_ok=True)

        acr_file = acr_dir / f"{acr_id}.md"
        content = f"""# {acr_id}: {title}
- Task: {task_id}
- Çelişen belge/karar: {conflict}
- Gözlem: {observation}
- Neden mevcut mimariyle çözülemiyor: Requires architectural modification.
- Önerilen değişiklik: {proposed_change}
- Etkilenen bileşenler: backend/app
- Geçici çözüm mümkün mü: {"evet" if workaround_possible else "hayır"}
"""
        acr_file.write_text(content, encoding="utf-8")

        if self.event_store:
            self.event_store.append(
                event_type=EventType.ACR_OPENED,
                task_id=task_id,
                payload={"acr_id": acr_id, "acr_path": str(acr_file), "title": title},
            )

        return acr_file

    def parse_acr(self, acr_path: Path) -> dict:
        """Parses an ACR markdown file into a structured dictionary."""
        lines = acr_path.read_text(encoding="utf-8").splitlines()
        data = {
            "acr_id": acr_path.stem,
            "title": "",
            "task_id": "",
            "conflict": "",
            "observation": "",
            "proposed_change": "",
            "workaround_possible": False,
        }

        if lines:
            first = lines[0].strip()
            if first.startswith("#"):
                data["title"] = first.lstrip("#").strip()

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("- Task:"):
                data["task_id"] = line_str.replace("- Task:", "").strip()
            elif line_str.startswith("- Çelişen belge/karar:"):
                data["conflict"] = line_str.replace("- Çelişen belge/karar:", "").strip()
            elif line_str.startswith("- Gözlem:"):
                data["observation"] = line_str.replace("- Gözlem:", "").strip()
            elif line_str.startswith("- Önerilen değişiklik:"):
                data["proposed_change"] = line_str.replace("- Önerilen değişiklik:", "").strip()
            elif line_str.startswith("- Geçici çözüm mümkün mü:"):
                data["workaround_possible"] = "evet" in line_str.lower()

        return data

    def resolve_acr(
        self,
        acr_path: Path,
        verdict: str,  # ACCEPTED | REJECTED | DEFERRED
        rationale: str,
        task_graph: Optional[TaskGraph] = None,
    ) -> tuple[str, Optional[TaskContract]]:
        """
        Resolves an open ACR per docs/03 §4:
        - REJECTED: Rationale added to task notes, task unblocked to retry/fix.
        - ACCEPTED: Architecture amended, new prerequisite task generated, original task depends on it.
        - DEFERRED: Technical debt recorded, original task proceeds with workaround.
        Returns:
            (verdict, optional_new_task_contract)
        """
        parsed = self.parse_acr(acr_path)
        task_id = parsed.get("task_id")
        acr_id = parsed.get("acr_id", acr_path.stem)
        verdict_upper = verdict.upper()

        new_task: Optional[TaskContract] = None
        target_task: Optional[TaskContract] = None

        if task_graph and task_id:
            target_task = task_graph.get_task(task_id)

        if verdict_upper == "ACCEPTED":
            # 1. Amend architecture document
            arch_doc = self.workspace.p2p_docs_dir / "architecture.md"
            if arch_doc.exists():
                curr = arch_doc.read_text(encoding="utf-8")
                amendment = (
                    f"\n\n## Architecture Amendment ({acr_id})\n"
                    f"- Status: ACCEPTED\n"
                    f"- Rationale: {rationale}\n"
                    f"- Changes: {parsed.get('proposed_change')}\n"
                )
                arch_doc.write_text(curr + amendment, encoding="utf-8")

            # 2. Create new task to implement the amendment
            new_task_id = f"AMEND-{acr_id[-3:]}"
            new_task = TaskContract(
                id=new_task_id,
                title=f"Architectural Amendment for {acr_id}",
                capabilities=[Capability.BACKEND],
                risk=RiskLevel.MEDIUM,
                depends_on=[],
                intent=f"Apply approved architectural changes from {acr_id}: {rationale}",
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-1",
                        statement="Architectural amendment changes verified.",
                        verified_by=VerifiedBy.GATE,
                        gate_ref="pytest",
                    )
                ],
                inputs=[".p2p/docs/architecture.md"],
                allowed_paths=["backend/app/**", "tests/**"],
                forbidden_paths=[".p2p/**", ".git/**"],
                gates=["pytest"],
                estimated_size=EstimatedSize.S,
                max_attempts=3,
                human_approval=False,
                result_path=".p2p/runs/{run_id}/result.json",
                acr_path=f".p2p/acr/ACR-{new_task_id}.md",
                notes=f"Generated from accepted ACR {acr_id}",
            )

            if task_graph:
                task_graph.add_task(new_task)
                # Write new task to disk
                new_task_file = self.workspace.tasks_dir / f"{new_task.id}.json"
                new_task_file.write_text(new_task.model_dump_json(indent=2), encoding="utf-8")

                if target_task:
                    # Make target task depend on new amendment task
                    if new_task_id not in target_task.depends_on:
                        target_task.depends_on.append(new_task_id)
                    target_task.notes = (target_task.notes or "") + f" [ACR {acr_id} ACCEPTED: depends on {new_task_id}]"
                    orig_file = self.workspace.tasks_dir / f"{target_task.id}.json"
                    orig_file.write_text(target_task.model_dump_json(indent=2), encoding="utf-8")

                task_graph.validate()

        elif verdict_upper == "REJECTED":
            if target_task:
                target_task.notes = (target_task.notes or "") + f" [ACR {acr_id} REJECTED: {rationale}]"
                orig_file = self.workspace.tasks_dir / f"{target_task.id}.json"
                orig_file.write_text(target_task.model_dump_json(indent=2), encoding="utf-8")

        elif verdict_upper == "DEFERRED":
            # Record technical debt
            debt_file = self.workspace.p2p_docs_dir / "tech_debt.md"
            debt_note = f"\n- **{acr_id}** on {task_id}: {rationale} (Deferred, proceed with workaround)"
            prev_debt = debt_file.read_text(encoding="utf-8") if debt_file.exists() else "# Technical Debt"
            debt_file.write_text(prev_debt + debt_note, encoding="utf-8")
            if target_task:
                target_task.notes = (target_task.notes or "") + f" [ACR {acr_id} DEFERRED: Proceeding with workaround]"
                orig_file = self.workspace.tasks_dir / f"{target_task.id}.json"
                orig_file.write_text(target_task.model_dump_json(indent=2), encoding="utf-8")

        # Emit ACR_RESOLVED event
        if self.event_store:
            self.event_store.append(
                event_type=EventType.ACR_RESOLVED,
                task_id=task_id,
                payload={
                    "acr_id": acr_id,
                    "verdict": verdict_upper,
                    "rationale": rationale,
                    "new_task_id": new_task.id if new_task else None,
                },
            )

        return verdict_upper, new_task
