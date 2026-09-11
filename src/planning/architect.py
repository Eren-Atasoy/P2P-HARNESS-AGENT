"""ArchitecturePlanner for Prompt2Product (docs/03 §5.2, docs/08 §Faz 6).

Produces .p2p/docs/architecture.md and initial ADR records based on ProjectSpec.
Evaluates the G2 (Architecture Approval) project gate.
"""
from pathlib import Path
from typing import Optional

from src.events.store import EventStore
from src.models.decision import Decision
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, EventType
from src.models.event import Event
from src.models.project import ProjectSpec
from src.orchestration.policy import PolicyEngine
from src.workspace.workspace import Workspace


class ArchitecturePlanner:
    """Plans architecture, directory structure, data models, and evaluates G2 gate."""

    def __init__(self, workspace: Workspace, event_store: Optional[EventStore] = None):
        self.workspace = workspace
        self.event_store = event_store

    def plan_architecture(
        self,
        spec: ProjectSpec,
        autonomy_level: AutonomyLevel = AutonomyLevel.GUARDED,
        approved_by_user: bool = False,
    ) -> tuple[str, list[Path], bool, Optional[Decision]]:
        """
        Generates architecture.md and ADRs.
        Returns:
            (architecture_markdown, list_of_adr_paths, g2_passed, g2_decision)
        """
        self.workspace.ensure_directories()
        docs_dir = self.workspace.p2p_docs_dir
        adr_dir = docs_dir / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)

        backend_stack = spec.stack.get("backend", "fastapi")
        db_stack = spec.stack.get("database", "sqlite")
        targets_str = ", ".join(t.value for t in spec.targets)

        # 1. Generate architecture.md
        arch_content = f"""# System Architecture: {spec.name}

## 1. Executive Summary
- **Prompt:** "{spec.prompt}"
- **Targets:** {targets_str}
- **Backend Stack:** {backend_stack}
- **Database:** {db_stack}
- **P2P Semver:** {spec.p2p_version}

## 2. Component Boundaries & Directory Layout
```
backend/
├── app/
│   ├── main.py          # Application entrypoint and router mount
│   ├── models.py        # Database/Pydantic schemas
│   ├── crud.py          # Data access operations
│   └── config.py        # Configuration and settings
tests/
├── test_api.py          # Functional API and schema tests
└── conftest.py          # Test fixtures and test client
```

## 3. Data Schema
- **Entity: Item**
  - `id`: integer primary key / uuid
  - `title`: string (1..200 chars), required
  - `description`: string, optional
  - `completed`: boolean, default false
  - `created_at`: ISO8601 timestamp

## 4. API Endpoints
| Method | Path | Request Body | Response Status | Description |
|---|---|---|---|---|
| `GET` | `/health` | None | `200 OK` | Service liveness probe |
| `GET` | `/items` | None | `200 OK` | List all items |
| `POST` | `/items` | `ItemCreate` | `201 Created` | Create a new item |
| `GET` | `/items/{{id}}` | None | `200 OK` / `404` | Get single item by ID |
| `PUT` | `/items/{{id}}` | `ItemUpdate` | `200 OK` / `404` | Update existing item |
| `DELETE` | `/items/{{id}}` | None | `204 No Content` / `404` | Delete item |

## 5. Security and Scope Boundaries
- Zero external credentials required for local verification.
- Local SQLite storage in `.data/` or in-memory for testing.
"""
        arch_path = docs_dir / "architecture.md"
        arch_path.write_text(arch_content, encoding="utf-8")

        # 2. Generate ADR-001 (Stack Selection)
        adr_001_content = f"""# ADR-001: Technology Stack Selection for {spec.name}

## Status
ACCEPTED

## Context
Project requires rapid verification, clear contract boundaries, and deterministic quality gates.

## Decision
- Backend: {backend_stack}
- Database: {db_stack}
- Test Engine: pytest

## Consequences
- High-speed local test execution without external daemon dependencies.
- Standard OpenAPI generation out of the box.
"""
        adr_001_path = adr_dir / "ADR-001-stack-selection.md"
        adr_001_path.write_text(adr_001_content, encoding="utf-8")

        adr_paths = [adr_001_path]

        # 3. Evaluate G2 Gate (Architecture Approval)
        g2_passed = False
        g2_decision: Optional[Decision] = None

        if approved_by_user:
            g2_passed = True
            g2_decision = Decision(
                id="DEC-G2",
                question="Do you approve the proposed architecture and data model?",
                options=["Approve", "Reject"],
                chosen="Approve",
                rationale="Approved explicitly by user.",
                decided_by=DecidedBy.HUMAN,
                kind=DecisionKind.GATE,
            )
        else:
            auto_approved, dec = PolicyEngine.evaluate_project_gate(
                gate_name="G2",
                autonomy_level=autonomy_level,
                question="Do you approve the proposed architecture and data model?",
            )
            g2_passed = auto_approved
            g2_decision = dec

        if g2_decision and self.event_store:
            self.event_store.append(
                event_type=EventType.DECISION_RECORDED,
                payload=g2_decision.model_dump(mode="json"),
            )

        return arch_content, adr_paths, g2_passed, g2_decision
