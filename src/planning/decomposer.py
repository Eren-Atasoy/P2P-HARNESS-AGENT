"""TaskDecomposer for Prompt2Product (docs/02 §2, docs/03 §5, docs/08 §Faz 6).

Decomposes architecture into atomic, DAG-valid TaskContracts with
automated risk derivation, size bounds (no L sizes), strict path scopes,
acceptance criteria, and G3 gate validation.
"""
from pathlib import Path
from typing import Optional

from src.events.store import EventStore
from src.models.decision import Decision
from src.models.enums import (
    AutonomyLevel,
    Capability,
    DecidedBy,
    DecisionKind,
    EstimatedSize,
    EventType,
    RiskLevel,
    VerifiedBy,
)
from src.models.event import Event
from src.models.project import ProjectSpec
from src.models.task import AcceptanceCriterion, TaskContract
from src.orchestration.graph import TaskGraph
from src.workspace.workspace import Workspace


class TaskDecomposer:
    """Decomposes system architecture into atomic TaskContracts and validates TaskGraph."""

    def __init__(self, workspace: Workspace, event_store: Optional[EventStore] = None):
        self.workspace = workspace
        self.event_store = event_store

    @staticmethod
    def derive_risk(title: str, intent: str, allowed_paths: list[str]) -> RiskLevel:
        """
        Derives verifiable risk level from target paths and keywords (docs/03 §5.1).
        Rule: If any high risk trigger is present, risk is elevated to HIGH and never reduced.
        """
        combined = f"{title.lower()} {intent.lower()} {' '.join(allowed_paths).lower()}"

        # High risk triggers: auth, security, crypto, token, secrets, destructive migrations
        high_triggers = [
            "auth", "login", "password", "token", "secret", "crypto",
            "payment", "migration", "drop", "delete_all", "credentials"
        ]
        if any(trigger in combined for trigger in high_triggers):
            return RiskLevel.HIGH

        # Medium risk triggers: business logic, schemas, models, api endpoints, db operations
        medium_triggers = [
            "model", "schema", "database", "crud", "endpoint", "api", "service", "route"
        ]
        if any(trigger in combined for trigger in medium_triggers):
            return RiskLevel.MEDIUM

        # Low risk: docs, readme, formatting, linter, presentation styling
        return RiskLevel.LOW

    def decompose(
        self,
        spec: ProjectSpec,
        autonomy_level: AutonomyLevel = AutonomyLevel.GUARDED,
        approved_by_user: bool = False,
    ) -> tuple[TaskGraph, bool, Optional[Decision]]:
        """
        Decomposes architecture into atomic TaskContracts, saves them to .p2p/tasks/,
        validates the TaskGraph, and evaluates the G3 gate.
        Returns:
            (task_graph, g3_passed, g3_decision)
        """
        self.workspace.ensure_directories()
        tasks_dir = self.workspace.tasks_dir
        tasks_dir.mkdir(parents=True, exist_ok=True)

        graph = TaskGraph()

        # Generate standard canonical atomic tasks for the planned architecture
        # Task 1: Setup Models and Schemas
        t1_allowed = ["backend/app/models.py", "tests/test_models.py"]
        t1_risk = self.derive_risk(
            title="Implement domain models and Pydantic schemas",
            intent="Define data models and request/response validation schemas for items.",
            allowed_paths=t1_allowed,
        )
        task_1 = TaskContract(
            id="CORE-001",
            title="Implement domain models and Pydantic schemas",
            capabilities=[Capability.BACKEND],
            risk=t1_risk,
            depends_on=[],
            intent="Define the data structures for items, including validation constraints and serialization rules.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="AC-1",
                    statement="Item schema validates title and completed fields correctly.",
                    verified_by=VerifiedBy.TEST,
                    test_ref="tests/test_models.py::test_item_schema",
                )
            ],
            inputs=[".p2p/docs/architecture.md"],
            allowed_paths=t1_allowed,
            forbidden_paths=[".p2p/**", ".git/**", "frontend/**"],
            gates=["pytest"],
            estimated_size=EstimatedSize.S,
            max_attempts=3,
            human_approval=False,
            result_path=".p2p/runs/{run_id}/result.json",
            acr_path=".p2p/acr/ACR-CORE-001.md",
        )

        # Task 2: Data Access Layer & CRUD
        t2_allowed = ["backend/app/crud.py", "tests/test_crud.py"]
        t2_risk = self.derive_risk(
            title="Implement in-memory/sqlite CRUD operations",
            intent="Implement create, read, update, delete storage operations for items.",
            allowed_paths=t2_allowed,
        )
        task_2 = TaskContract(
            id="CORE-002",
            title="Implement in-memory/sqlite CRUD operations",
            capabilities=[Capability.BACKEND, Capability.DATABASE],
            risk=t2_risk,
            depends_on=["CORE-001"],
            intent="Provide reliable CRUD operations matching the domain model specifications.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="AC-1",
                    statement="CRUD operations handle create, retrieve, update, and deletion.",
                    verified_by=VerifiedBy.TEST,
                    test_ref="tests/test_crud.py::test_crud_operations",
                )
            ],
            inputs=[".p2p/docs/architecture.md", "backend/app/models.py"],
            allowed_paths=t2_allowed,
            forbidden_paths=[".p2p/**", ".git/**", "frontend/**"],
            gates=["pytest"],
            estimated_size=EstimatedSize.M,
            max_attempts=3,
            human_approval=False,
            result_path=".p2p/runs/{run_id}/result.json",
            acr_path=".p2p/acr/ACR-CORE-002.md",
        )

        # Task 3: API Endpoints
        t3_allowed = ["backend/app/main.py", "tests/test_api.py"]
        t3_risk = self.derive_risk(
            title="Implement REST API endpoints and router",
            intent="Mount HTTP endpoints for /health and /items according to architecture contract.",
            allowed_paths=t3_allowed,
        )
        task_3 = TaskContract(
            id="API-001",
            title="Implement REST API endpoints and router",
            capabilities=[Capability.BACKEND],
            risk=t3_risk,
            depends_on=["CORE-002"],
            intent="Expose RESTful endpoints conforming strictly to the OpenAPI schema documented in architecture.md.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="AC-1",
                    statement="GET /health returns 200 OK and status ok.",
                    verified_by=VerifiedBy.TEST,
                    test_ref="tests/test_api.py::test_health",
                ),
                AcceptanceCriterion(
                    id="AC-2",
                    statement="POST /items creates an item and returns 201 Created.",
                    verified_by=VerifiedBy.TEST,
                    test_ref="tests/test_api.py::test_create_item",
                ),
            ],
            inputs=[".p2p/docs/architecture.md", "backend/app/models.py", "backend/app/crud.py"],
            allowed_paths=t3_allowed,
            forbidden_paths=[".p2p/**", ".git/**"],
            gates=["pytest"],
            estimated_size=EstimatedSize.M,
            max_attempts=3,
            human_approval=False,
            result_path=".p2p/runs/{run_id}/result.json",
            acr_path=".p2p/acr/ACR-API-001.md",
        )

        # Task 4: Documentation & Readme
        t4_allowed = ["README.md", "docs/**"]
        t4_risk = self.derive_risk(
            title="Create project documentation and quickstart instructions",
            intent="Write comprehensive README with installation and running guide.",
            allowed_paths=t4_allowed,
        )
        task_4 = TaskContract(
            id="DOCS-001",
            title="Create project documentation and quickstart instructions",
            capabilities=[Capability.DOCS],
            risk=t4_risk,
            depends_on=["API-001"],
            intent="Document the project setup, run instructions, and API endpoints for consumers.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="AC-1",
                    statement="README includes project overview and run instructions.",
                    verified_by=VerifiedBy.GATE,
                    gate_ref="pytest",
                )
            ],
            inputs=[".p2p/docs/architecture.md"],
            allowed_paths=t4_allowed,
            forbidden_paths=[".p2p/**", ".git/**", "backend/**"],
            gates=["pytest"],
            estimated_size=EstimatedSize.S,
            max_attempts=3,
            human_approval=False,
            result_path=".p2p/runs/{run_id}/result.json",
            acr_path=".p2p/acr/ACR-DOCS-001.md",
        )

        tasks = [task_1, task_2, task_3, task_4]

        # Add to graph and validate DAG
        for task in tasks:
            graph.add_task(task)
            # Write to disk
            task_file = tasks_dir / f"{task.id}.json"
            task_file.write_text(task.model_dump_json(indent=2), encoding="utf-8")

            if self.event_store:
                self.event_store.append(
                    event_type=EventType.TASK_CREATED,
                    task_id=task.id,
                    payload={"risk": task.risk.value, "title": task.title},
                )

        # Validate DAG
        graph.validate()

        # Evaluate G3 Gate (Scope & Task Graph Approval)
        g3_passed = False
        g3_decision: Optional[Decision] = None

        if approved_by_user or autonomy_level != AutonomyLevel.SUPERVISED:
            g3_passed = True
            g3_decision = Decision(
                id="DEC-G3",
                question="Do you approve the proposed task graph and work breakdown?",
                options=["Approve", "Reject"],
                chosen="Approve",
                rationale="Task graph validated with zero cycles and verifiable risk classifications.",
                decided_by=DecidedBy.HUMAN if approved_by_user else DecidedBy.DEFAULT,
                kind=DecisionKind.GATE,
            )

        if g3_decision and self.event_store:
            self.event_store.append(
                event_type=EventType.DECISION_RECORDED,
                payload=g3_decision.model_dump(mode="json"),
            )

        return graph, g3_passed, g3_decision
