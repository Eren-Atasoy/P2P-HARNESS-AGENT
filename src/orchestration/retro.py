"""Retrospective Engine: Extracts repeating failure patterns from event logs and proposes rules/gates (docs/03 §8).

Signal comes strictly from events.jsonl, not human memory:
- Same gate + same error signature >= 3 times -> Mechanical gate proposal (ADR-004)
- Same review finding category >= 3 times -> Prompt/instruction rule proposal
- Consecutive escalations on same capability >= 2 times -> Router/connection proposal
- Repeating ACR themes >= 2 times -> Architecture documentation amendment proposal
"""
from collections import defaultdict
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.events.store import EventStore
from src.models.enums import EventType
from src.models.event import Event
from src.workspace.workspace import Workspace


class RetroRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="e.g. REC-001")
    kind: str = Field(description="GATE | RULE | ROUTER | DOCS")
    pattern: str
    count: int
    recommendation: str
    target_file: str
    applied: bool = False


class RetroEngine:
    """Analyzes append-only event stream to derive systemic failure patterns."""

    def __init__(self, workspace: Workspace, event_store: Optional[EventStore] = None):
        self.workspace = workspace
        self.event_store = event_store

    def analyze_events(self, events: list[Event]) -> list[RetroRecommendation]:
        """Scans the event log and deterministically produces actionable recommendations."""
        recommendations: list[RetroRecommendation] = []
        rec_counter = 1

        # 1. Detect repeating gate failures with identical signatures (Threshold >= 3)
        gate_failures = defaultdict(list)
        for ev in events:
            if ev.type == EventType.GATE_FINISHED:
                status = ev.payload.get("status")
                gate = ev.payload.get("gate", "unknown")
                if status in ("FAIL", "ERROR"):
                    msg = str(ev.payload.get("failures", ""))
                    gate_failures[(gate, msg)].append(ev.task_id)

        for (gate, msg), task_ids in gate_failures.items():
            if len(task_ids) >= 3:
                rec_id = f"REC-{rec_counter:03d}"
                rec_counter += 1
                recommendations.append(
                    RetroRecommendation(
                        id=rec_id,
                        kind="GATE",
                        pattern=f"Gate '{gate}' failed {len(task_ids)} times across tasks {set(task_ids)}",
                        count=len(task_ids),
                        recommendation=f"Add strict pre-commit verification or adjust gate threshold for '{gate}'.",
                        target_file=".p2p/gates.yaml",
                    )
                )

        # 2. Detect repeating review findings categories (Threshold >= 3)
        review_categories = defaultdict(int)
        for ev in events:
            if ev.type == EventType.REVIEW_FINISHED:
                findings = ev.payload.get("findings", [])
                for f in findings:
                    cat = f.get("category") or f.get("title") or "general"
                    review_categories[cat] += 1

        for cat, count in review_categories.items():
            if count >= 3:
                rec_id = f"REC-{rec_counter:03d}"
                rec_counter += 1
                recommendations.append(
                    RetroRecommendation(
                        id=rec_id,
                        kind="RULE",
                        pattern=f"Review category '{cat}' flagged {count} times",
                        count=count,
                        recommendation=f"Add explicit guideline in GEMINI.md/AGENTS.md addressing '{cat}' anti-patterns.",
                        target_file=".agents/rules/retro_rules.md",
                    )
                )

        # 3. Detect consecutive escalations on same capability (Threshold >= 2)
        escalation_counts = defaultdict(int)
        for ev in events:
            if ev.type == EventType.ESCALATED:
                cap = ev.payload.get("capability", "general")
                escalation_counts[cap] += 1

        for cap, count in escalation_counts.items():
            if count >= 2:
                rec_id = f"REC-{rec_counter:03d}"
                rec_counter += 1
                recommendations.append(
                    RetroRecommendation(
                        id=rec_id,
                        kind="ROUTER",
                        pattern=f"Capability '{cap}' triggered {count} escalations",
                        count=count,
                        recommendation=f"Update routing.yaml to assign higher capability runtime for '{cap}'.",
                        target_file=".p2p/routing.yaml",
                    )
                )

        # 4. Detect repeating ACR events (Threshold >= 2)
        acr_events = [ev for ev in events if ev.type == EventType.ACR_OPENED]
        if len(acr_events) >= 2:
            rec_id = f"REC-{rec_counter:03d}"
            rec_counter += 1
            recommendations.append(
                RetroRecommendation(
                    id=rec_id,
                    kind="DOCS",
                    pattern=f"{len(acr_events)} architectural change requests opened during execution",
                    count=len(acr_events),
                    recommendation="Architecture document requires clearer schema relationship and contract boundaries.",
                    target_file=".p2p/docs/architecture.md",
                )
            )

        return recommendations

    def apply_recommendation(self, recommendation: RetroRecommendation) -> bool:
        """Applies an approved recommendation to the target file and records RETRO_APPLIED event."""
        target_path = self.workspace.root_path / recommendation.target_file
        target_path.parent.mkdir(parents=True, exist_ok=True)

        note = (
            f"\n\n<!-- Applied by p2p retro ({recommendation.id}) -->\n"
            f"# Retrospective Rule: {recommendation.pattern}\n"
            f"- Recommendation: {recommendation.recommendation}\n"
            f"- Enforcement: Mandatory\n"
        )

        prev_content = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        target_path.write_text(prev_content + note, encoding="utf-8")
        recommendation.applied = True

        if self.event_store:
            self.event_store.append(
                event_type=EventType.RETRO_APPLIED,
                payload={
                    "rec_id": recommendation.id,
                    "kind": recommendation.kind,
                    "recommendation": recommendation.recommendation,
                    "target_file": recommendation.target_file,
                },
            )

        return True
