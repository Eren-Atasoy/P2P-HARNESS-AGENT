"""Wave scheduler coordinating graph, router, state machine, policy, and execution (docs/03)."""
from pathlib import Path
from typing import Callable, Optional

from src.events.store import EventStore
from src.models.enums import AutonomyLevel, EventType, GateStatus, ReviewVerdict, TaskOutcome, TaskStatus
from src.models.result import AgentResult, GateResult, ReviewResult
from src.models.task import TaskContract
from src.orchestration.graph import TaskGraph
from src.orchestration.policy import PolicyEngine
from src.orchestration.router import CapabilityRouter
from src.orchestration.state_machine import ProgressTracker, TaskStateMachine
from src.runtime.base import RuntimeAdapter


class Scheduler:
    """Orchestrates multi-wave, dependency-ordered, conflict-free task execution."""

    def __init__(
        self,
        graph: TaskGraph,
        router: CapabilityRouter,
        runtime: RuntimeAdapter,
        event_store: Optional[EventStore] = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.GUARDED,
        workspace: Optional[Path] = None,
        run_id: str = "run-default",
    ):
        self.graph = graph
        self.router = router
        self.runtime = runtime
        self.event_store = event_store
        self.autonomy_level = autonomy_level
        self.workspace = workspace or Path(".")
        self.run_id = run_id

        self.state_machine = TaskStateMachine()
        self.tracker = ProgressTracker()
        self.task_states: dict[str, TaskStatus] = {tid: TaskStatus.PENDING for tid in graph.tasks}
        self.task_attempts: dict[str, int] = {tid: 0 for tid in graph.tasks}

    def _log_event(self, event_type: EventType, payload: dict, task_id: Optional[str] = None):
        if self.event_store:
            self.event_store.append(
                event_type=event_type,
                payload=payload,
                task_id=task_id,
                run_id=self.run_id,
            )

    def execute_task(
        self,
        task: TaskContract,
        gate_checker: Optional[Callable[[TaskContract, Path], GateResult]] = None,
        review_checker: Optional[Callable[[TaskContract, Path], ReviewResult]] = None,
    ) -> TaskStatus:
        """Executes a single task through its lifecycle (Implement -> Verify -> Review -> Merge)."""
        tid = task.id

        # 1. Route to connection
        try:
            conn = self.router.route(task, attempt=self.task_attempts[tid] + 1)
        except Exception as e:
            self.task_states[tid] = TaskStatus.UNROUTABLE
            self._log_event(EventType.TASK_UNROUTABLE, {"error": str(e)}, task_id=tid)
            self._log_event(EventType.ESCALATED, {"reason": "UNROUTABLE", "error": str(e)}, task_id=tid)
            return TaskStatus.UNROUTABLE

        max_attempts = task.max_attempts

        while self.task_attempts[tid] < max_attempts:
            self.task_attempts[tid] += 1
            curr_attempt = self.task_attempts[tid]

            # Transition to RUNNING
            self.task_states[tid] = TaskStatus.RUNNING
            self._log_event(
                EventType.TASK_STATE_CHANGED,
                {"to": TaskStatus.RUNNING.value, "assigned_to": conn.id, "attempts": curr_attempt},
                task_id=tid,
            )

            # Execute via runtime adapter
            result: AgentResult = self.runtime.execute(task, self.workspace)

            # Check outcome
            if result.outcome == TaskOutcome.BLOCKED:
                self.task_states[tid] = TaskStatus.BLOCKED
                self._log_event(EventType.ACR_OPENED, {"acr_path": result.acr or task.acr_path}, task_id=tid)
                return TaskStatus.BLOCKED

            if result.outcome == TaskOutcome.FAILED:
                if curr_attempt >= max_attempts:
                    self.task_states[tid] = TaskStatus.ESCALATED
                    self._log_event(EventType.ESCALATED, {"reason": "Max attempts reached with failure"}, task_id=tid)
                    return TaskStatus.ESCALATED
                continue

            # 2. Verification (Quality Gates)
            self.task_states[tid] = TaskStatus.GATED
            self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.GATED.value}, task_id=tid)

            gate_ok = True
            if gate_checker:
                gate_res = gate_checker(task, self.workspace)
                self._log_event(
                    EventType.GATE_FINISHED,
                    {"gate": gate_res.gate, "status": gate_res.status.value, "exit_code": gate_res.exit_code},
                    task_id=tid,
                )
                if gate_res.status in (GateStatus.FAIL, GateStatus.ERROR):
                    gate_ok = False
                    # Check if stuck on same failure (docs/03 §3.2)
                    if self.tracker.record_and_check_stuck(tid, gate_res.failures or gate_res.output_summary if hasattr(gate_res, "output_summary") else gate_res.status):
                        self.task_states[tid] = TaskStatus.ESCALATED
                        self._log_event(EventType.ESCALATED, {"reason": "Repeated identical gate failure (progress stuck)"}, task_id=tid)
                        return TaskStatus.ESCALATED

                    if gate_res.status == GateStatus.ERROR:
                        # Environment/infrastructure error -> straight to ESCALATED without fix loop!
                        self.task_states[tid] = TaskStatus.ESCALATED
                        self._log_event(EventType.ESCALATED, {"reason": "Gate infrastructure error (ENV)"}, task_id=tid)
                        return TaskStatus.ESCALATED

            if not gate_ok:
                if curr_attempt >= max_attempts:
                    self.task_states[tid] = TaskStatus.ESCALATED
                    self._log_event(EventType.ESCALATED, {"reason": "Max attempts reached on gate failure"}, task_id=tid)
                    return TaskStatus.ESCALATED
                self.task_states[tid] = TaskStatus.FIXING
                self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.FIXING.value}, task_id=tid)
                continue

            # 3. Review (ReviewResult)
            review_ok = True
            if review_checker:
                rev_res = review_checker(task, self.workspace)
                self._log_event(
                    EventType.REVIEW_FINISHED,
                    {"verdict": rev_res.verdict.value, "findings_count": len(rev_res.findings)},
                    task_id=tid,
                )
                if rev_res.verdict != ReviewVerdict.APPROVED:
                    review_ok = False
                    if curr_attempt >= max_attempts or rev_res.verdict == ReviewVerdict.REJECTED:
                        self.task_states[tid] = TaskStatus.ESCALATED
                        self._log_event(EventType.ESCALATED, {"reason": f"Review verdict {rev_res.verdict.value}"}, task_id=tid)
                        return TaskStatus.ESCALATED

            if not review_ok:
                self.task_states[tid] = TaskStatus.FIXING
                self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.FIXING.value}, task_id=tid)
                continue

            # 4. Human Approval / Merging
            self.task_states[tid] = TaskStatus.APPROVED
            self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.APPROVED.value}, task_id=tid)

            if PolicyEngine.requires_human_approval(task, self.autonomy_level):
                # Pauses for human gate
                return TaskStatus.APPROVED

            # Auto-approved -> Merge completed
            self.task_states[tid] = TaskStatus.MERGED
            self._log_event(EventType.MERGE_COMPLETED, {"task_id": tid}, task_id=tid)
            return TaskStatus.MERGED

        self.task_states[tid] = TaskStatus.ESCALATED
        self._log_event(EventType.ESCALATED, {"reason": "Max attempts exhausted"}, task_id=tid)
        return TaskStatus.ESCALATED

    def run_all(
        self,
        gate_checker: Optional[Callable[[TaskContract, Path], GateResult]] = None,
        review_checker: Optional[Callable[[TaskContract, Path], ReviewResult]] = None,
    ) -> dict[str, TaskStatus]:
        """Runs the entire task graph wave by wave."""
        waves = self.graph.compute_waves()

        for wave in waves:
            for tid in wave:
                task = self.graph.tasks[tid]
                self.execute_task(task, gate_checker, review_checker)

        return self.task_states
