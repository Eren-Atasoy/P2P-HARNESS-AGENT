"""DiscoveryEngine for Prompt2Product (docs/03 §5.2, docs/08 §Faz 6).

Analyzes user prompt, resolves ambiguities (G1 gate), selects stack,
and creates the ProjectSpec (.p2p/project.json).
"""
import re
from typing import Optional
from uuid import uuid4

from src.events.store import EventStore
from src.models.decision import Decision
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, EventType, TargetType
from src.models.event import Event
from src.models.project import ProjectSpec
from src.workspace.workspace import Workspace


def slugify(text: str) -> str:
    """Creates a clean kebab-case name from a prompt or string."""
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisouCGISOU")
    ascii_text = text.translate(tr_map).lower()
    cleaned = re.sub(r"[^\w\s-]", "", ascii_text).strip()
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-")
    if len(slug) > 50:
        slug = slug[:50].rsplit("-", 1)[0]
    return slug.strip("-") or "p2p-project"


class DiscoveryEngine:
    """Discovers project scope, targets, technology stack, and ambiguities from a prompt."""

    def __init__(self, workspace: Workspace, event_store: Optional[EventStore] = None):
        self.workspace = workspace
        self.event_store = event_store

    def discover(
        self,
        prompt: str,
        autonomy_level: AutonomyLevel = AutonomyLevel.GUARDED,
    ) -> tuple[ProjectSpec, list[Decision], bool]:
        """
        Processes a user prompt and returns:
        (ProjectSpec, list[Decision], g1_passed)
        """
        # 1. Determine TargetTypes
        lower_prompt = prompt.lower()
        targets: list[TargetType] = []
        if any(w in lower_prompt for w in ["api", "backend", "endpoint", "rest", "crud"]):
            targets.append(TargetType.API)
        if any(w in lower_prompt for w in ["web", "frontend", "ui", "sayfa", "arayüz", "dashboard"]):
            targets.append(TargetType.WEB)
        if any(w in lower_prompt for w in ["cli", "terminal", "konsol", "komut"]):
            targets.append(TargetType.CLI)

        if not targets:
            # Default to API if nothing specified
            targets = [TargetType.API]

        # 2. Extract Stack and Ambiguities
        decisions: list[Decision] = []
        is_supervised = autonomy_level == AutonomyLevel.SUPERVISED
        decided_by = DecidedBy.HUMAN if is_supervised else DecidedBy.DEFAULT

        # Database choice ambiguity
        db_choice = "sqlite"
        if "postgres" in lower_prompt:
            db_choice = "postgresql"
        elif "mongo" in lower_prompt:
            db_choice = "mongodb"
        else:
            decisions.append(
                Decision(
                    id="DEC-AMB-DB",
                    question="Which database engine should be used?",
                    options=["sqlite", "postgresql"],
                    chosen="sqlite",
                    rationale="SQLite chosen as lightweight zero-config default for fast verification.",
                    decided_by=decided_by,
                    kind=DecisionKind.AMBIGUITY,
                )
            )

        # Auth choice ambiguity
        has_auth_mention = any(w in lower_prompt for w in ["auth", "login", "jwt", "şifre", "kullanıcı"])
        auth_choice = "jwt" if has_auth_mention else "none"
        if not has_auth_mention and TargetType.API in targets:
            decisions.append(
                Decision(
                    id="DEC-AMB-AUTH",
                    question="Should authentication and authorization be included?",
                    options=["none", "jwt", "session"],
                    chosen="none",
                    rationale="No authentication requested in user prompt; skipped to keep minimal scope.",
                    decided_by=decided_by,
                    kind=DecisionKind.AMBIGUITY,
                )
            )

        stack = {
            "backend": "fastapi" if TargetType.API in targets else "python",
            "database": db_choice,
            "frontend": "vanilla_html_css" if TargetType.WEB in targets else "none",
            "test": "pytest",
        }

        # 3. Create ProjectSpec
        project_name = slugify(prompt)
        spec = ProjectSpec(
            id=uuid4(),
            name=project_name,
            prompt=prompt,
            stack=stack,
            decisions=[d.model_dump(mode="json") for d in decisions],
            targets=targets,
        )

        # 4. Evaluate Gate G1 (Ambiguity Resolution)
        # If supervised and there are unresolved decisions requiring human input, G1 does not pass.
        # In guarded or full, default choices are accepted automatically.
        g1_passed = not (is_supervised and len(decisions) > 0)

        # Save project.json to workspace
        self.workspace.ensure_directories()
        self.workspace.project_spec_path.write_text(
            spec.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Record events if store provided
        if self.event_store:
            self.event_store.append(
                event_type=EventType.PROJECT_CREATED,
                payload={"name": spec.name, "targets": [t.value for t in spec.targets]},
            )
            for dec in decisions:
                self.event_store.append(
                    event_type=EventType.DECISION_RECORDED,
                    payload=dec.model_dump(mode="json"),
                )

        return spec, decisions, g1_passed
