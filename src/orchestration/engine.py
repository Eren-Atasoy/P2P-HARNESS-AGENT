"""Autonomous Orchestrator Engine running the full dispatch-verify-review-repair loop (docs/03 §7)."""
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from src.events.store import EventStore
from src.models.decision import Decision
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, EventType, GateStatus, TaskStatus
from src.models.result import AgentResult, GateResult
from src.models.task import TaskContract
from src.orchestration.graph import TaskGraph, paths_conflict
from src.orchestration.policy import PolicyEngine
from src.orchestration.prompts import PromptCompiler
from src.orchestration.repair import FailureClass, RepairPlanner
from src.orchestration.router import CapabilityRouter
from src.verification.config import GatesConfig
from src.verification.runner import GateRunner
from src.workspace.git import GitManager
from src.workspace.scope import ScopeValidator
from src.workspace.workspace import Workspace


class LoopExitReason(str, Enum):
    COMPLETED = "COMPLETED"
    DEADLOCKED = "DEADLOCKED"
    WAITING_HUMAN = "WAITING_HUMAN"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    NO_PROGRESS = "NO_PROGRESS"


class LoopResult(BaseModel):
    exit_reason: LoopExitReason
    task_states: dict[str, TaskStatus]
    iterations: int
    events_count: int
    details: Optional[str] = None


class OrchestratorEngine:
    """Core autonomous orchestrator running the loop until termination (docs/03 §7)."""

    def __init__(
        self,
        workspace: Workspace,
        graph: TaskGraph,
        router: CapabilityRouter,
        runtime: any,
        event_store: Optional[EventStore] = None,
        git_manager: Optional[GitManager] = None,
        gates_config: Optional[GatesConfig] = None,
        gate_runner: Optional[GateRunner] = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.FULL,
        run_id: str = "run-default",
        max_iterations: int = 50,
        enable_git: bool = True,
    ):
        self.workspace = workspace
        self.graph = graph
        self.router = router
        self.runtime = runtime
        self.event_store = event_store
        self.git_manager = git_manager or GitManager(workspace)
        self.gates_config = gates_config or GatesConfig.default_gates()
        self.gate_runner = gate_runner or GateRunner(workspace, self.gates_config)
        self.autonomy_level = autonomy_level
        self.run_id = run_id
        self.max_iterations = max_iterations
        self.enable_git = enable_git

        self.scope_validator = ScopeValidator(self.git_manager)
        self.repair_planner = RepairPlanner()
        self.prompt_compiler = PromptCompiler()

        self.task_states: dict[str, TaskStatus] = {tid: TaskStatus.PENDING for tid in graph.tasks}
        self.task_attempts: dict[str, int] = {tid: 0 for tid in graph.tasks}
        self.last_results: dict[str, AgentResult] = {}
        self.last_gate_results: dict[str, list[GateResult]] = {}
        self.human_guidance: dict[str, str] = {}
        self.decisions: list[Decision] = []

    def _log_event(self, event_type: EventType, payload: dict, task_id: Optional[str] = None):
        if self.event_store:
            self.event_store.append(
                event_type=event_type,
                payload=payload,
                task_id=task_id,
                run_id=self.run_id,
            )

    def steer(self, task_id: str, guidance: str) -> bool:
        """Injects human decision into an ESCALATED task and resets it to READY (docs/03 §3.5)."""
        if task_id not in self.task_states:
            return False

        dec = Decision(
            id=f"DEC-STEER-{task_id}-{len(self.decisions) + 1}",
            question="Human steering guidance injected",
            chosen=guidance,
            rationale="Steered by operator via CLI",
            decided_by=DecidedBy.HUMAN,
            kind=DecisionKind.STEER,
        )
        self.decisions.append(dec)
        self.human_guidance[task_id] = guidance

        self._log_event(
            EventType.DECISION_RECORDED,
            {"decision_id": dec.id, "chosen": dec.chosen, "decided_by": dec.decided_by.value},
            task_id=task_id,
        )
        self._log_event(
            EventType.HUMAN_STEERED,
            {"guidance": guidance},
            task_id=task_id,
        )

        self.task_states[task_id] = TaskStatus.READY
        self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.READY.value, "reason": "human_steer"}, task_id=task_id)
        return True

    def run_loop(self) -> LoopResult:
        """Executes the loop until completion, deadlock, human escalation, budget exhaustion, or no-progress."""
        iteration = 0
        events_start = len(self.event_store.read_all()) if self.event_store else 0

        self._log_event(
            EventType.RUN_STARTED,
            {"autonomy": self.autonomy_level.value, "autonomy_level": self.autonomy_level.value, "tasks": list(self.graph.tasks.keys())},
        )

        for tid, task in self.graph.tasks.items():
            self._log_event(
                EventType.TASK_CREATED,
                {"risk": task.risk.value, "title": task.title},
                task_id=tid,
            )

        while iteration < self.max_iterations:
            iteration += 1
            progress_in_tick = False

            # Check completion: all tasks MERGED or APPROVED
            unfinished = [
                tid for tid, st in self.task_states.items()
                if st not in (TaskStatus.MERGED, TaskStatus.APPROVED)
            ]
            if not unfinished:
                self._log_event(EventType.RUN_FINISHED, {"exit_reason": LoopExitReason.COMPLETED.value})
                return LoopResult(
                    exit_reason=LoopExitReason.COMPLETED,
                    task_states=self.task_states,
                    iterations=iteration,
                    events_count=(len(self.event_store.read_all()) - events_start) if self.event_store else 0,
                    details="All tasks successfully completed and verified",
                )

            # 1. Transition eligible PENDING tasks to READY
            for tid in unfinished:
                if self.task_states[tid] == TaskStatus.PENDING:
                    deps = self.graph.tasks[tid].depends_on
                    deps_satisfied = all(
                        self.task_states.get(d) in (TaskStatus.MERGED, TaskStatus.APPROVED)
                        for d in deps
                    )
                    if deps_satisfied:
                        self.task_states[tid] = TaskStatus.READY
                        self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.READY.value}, task_id=tid)
                        progress_in_tick = True

            ready_tasks = [tid for tid in unfinished if self.task_states[tid] == TaskStatus.READY]

            if not ready_tasks:
                escalated = [tid for tid, st in self.task_states.items() if st == TaskStatus.ESCALATED]
                if escalated:
                    return LoopResult(
                        exit_reason=LoopExitReason.WAITING_HUMAN,
                        task_states=self.task_states,
                        iterations=iteration,
                        events_count=(len(self.event_store.read_all()) - events_start) if self.event_store else 0,
                        details=f"{len(escalated)} task(s) require human steering: {escalated}",
                    )
                # No ready and no escalated, but unfinished exist -> deadlock
                return LoopResult(
                    exit_reason=LoopExitReason.DEADLOCKED,
                    task_states=self.task_states,
                    iterations=iteration,
                    events_count=(len(self.event_store.read_all()) - events_start) if self.event_store else 0,
                    details="Dependency deadlock: pending tasks cannot be satisfied",
                )

            # 2. Select batch of tasks with disjoint paths
            selected_tasks: list[TaskContract] = []
            for tid in ready_tasks:
                task = self.graph.tasks[tid]
                has_conflict = any(
                    paths_conflict(sel.allowed_paths, task.allowed_paths)
                    for sel in selected_tasks
                )
                if not has_conflict:
                    selected_tasks.append(task)

            for task in selected_tasks:
                tid = task.id
                attempt = self.task_attempts[tid] + 1
                self.task_attempts[tid] = attempt

                # 3. Route task
                try:
                    conn = self.router.route(task, attempt=attempt)
                except Exception as e:
                    self.task_states[tid] = TaskStatus.UNROUTABLE
                    self._log_event(EventType.TASK_UNROUTABLE, {"error": str(e)}, task_id=tid)
                    self.task_states[tid] = TaskStatus.ESCALATED
                    self._log_event(EventType.ESCALATED, {"reason": "UNROUTABLE", "error": str(e)}, task_id=tid)
                    progress_in_tick = True
                    continue

                # 4. Set state to RUNNING / FIXING
                state_to = TaskStatus.FIXING if attempt > 1 else TaskStatus.RUNNING
                self.task_states[tid] = state_to
                self._log_event(
                    EventType.TASK_STATE_CHANGED,
                    {"to": state_to.value, "assigned_to": conn.id, "attempt": attempt},
                    task_id=tid,
                )

                # 5. Worktree setup
                worktree_path = self.workspace.root_path
                if self.enable_git:
                    try:
                        worktree_path = self.git_manager.create_worktree(tid)
                    except Exception:
                        worktree_path = self.workspace.root_path

                # 6. Prompt compilation
                if attempt == 1:
                    prompt = self.prompt_compiler.compile_implementer_prompt(task)
                else:
                    prev_res = self.last_results.get(tid)
                    prev_gates = self.last_gate_results.get(tid, [])
                    raw_out = "\n".join([g.output_summary for g in prev_gates if g.output_summary])
                    failures = []
                    for g in prev_gates:
                        if g.failures:
                            failures.extend(g.failures)
                    prompt = self.prompt_compiler.compile_fix_prompt(
                        contract=task,
                        previous_result=prev_res,
                        failures=failures,
                        raw_gate_output=raw_out,
                    )

                if tid in self.human_guidance:
                    prompt += f"\n## Operator Steering Instruction\n{self.human_guidance[tid]}\n"

                if hasattr(self.runtime, "prompt_override"):
                    self.runtime.prompt_override = prompt

                # 7. Execute runtime
                agent_result = self.runtime.execute(
                    task,
                    worktree_path,
                    run_id=f"{self.run_id}-{tid}-{attempt}",
                )
                self.last_results[tid] = agent_result

                # 8. Scope validation
                if self.enable_git:
                    scope_res = self.scope_validator.validate_scope(worktree_path, task, agent_result)
                    if not scope_res.is_valid:
                        self._log_event(EventType.POLICY_VIOLATION, {"violating_files": scope_res.unauthorized_files or scope_res.violations}, task_id=tid)
                        self.scope_validator.rollback_unauthorized_changes(worktree_path)

                # 9. Deterministic verification gates
                self.task_states[tid] = TaskStatus.GATED
                self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.GATED.value}, task_id=tid)

                gate_names = task.gates or ["unit"]
                gate_results = self.gate_runner.run_gates(
                    gate_names=gate_names,
                    target_dir=worktree_path,
                    run_id=f"{self.run_id}-{tid}",
                    fail_fast=True,
                )
                self.last_gate_results[tid] = gate_results

                for gr in gate_results:
                    self._log_event(
                        EventType.GATE_FINISHED,
                        {"gate": gr.gate, "status": gr.status.value, "exit_code": gr.exit_code},
                        task_id=tid,
                    )

                all_gates_pass = all(gr.status == GateStatus.PASS for gr in gate_results)

                if not all_gates_pass:
                    should_retry, fail_class, reason = self.repair_planner.should_enter_fix_loop(
                        task=task,
                        attempt=attempt,
                        gate_results=gate_results,
                    )
                    if should_retry:
                        self.task_states[tid] = TaskStatus.READY  # retry in next tick
                        self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.READY.value, "reason": "fix_retry"}, task_id=tid)
                    else:
                        self.task_states[tid] = TaskStatus.ESCALATED
                        self._log_event(EventType.ESCALATED, {"reason": reason, "class": fail_class.value}, task_id=tid)
                        if self.enable_git:
                            self.git_manager.remove_worktree(tid, failed=True)
                    progress_in_tick = True
                    continue

                # Gates passed!
                self.task_states[tid] = TaskStatus.APPROVED
                self._log_event(EventType.TASK_STATE_CHANGED, {"to": TaskStatus.APPROVED.value}, task_id=tid)

                # Check policy approval
                if PolicyEngine.requires_human_approval(task, self.autonomy_level):
                    self.task_states[tid] = TaskStatus.ESCALATED
                    self._log_event(EventType.ESCALATED, {"reason": "Policy requires human approval"}, task_id=tid)
                    progress_in_tick = True
                    continue

                # Merge task
                if self.enable_git:
                    try:
                        self.git_manager.commit_task(
                            worktree_path=worktree_path,
                            task=task,
                            result=agent_result,
                            gates=gate_results,
                            attempt=attempt,
                        )
                        self.git_manager.merge_task(tid)
                        self.git_manager.remove_worktree(tid, failed=False)
                    except Exception as e:
                        self.task_states[tid] = TaskStatus.ESCALATED
                        self._log_event(EventType.ESCALATED, {"reason": f"Git merge failed: {e}"}, task_id=tid)
                        progress_in_tick = True
                        continue

                self.task_states[tid] = TaskStatus.MERGED
                self._log_event(EventType.MERGE_COMPLETED, {"task_id": tid}, task_id=tid)
                progress_in_tick = True

            if not progress_in_tick:
                return LoopResult(
                    exit_reason=LoopExitReason.NO_PROGRESS,
                    task_states=self.task_states,
                    iterations=iteration,
                    events_count=(len(self.event_store.read_all()) - events_start) if self.event_store else 0,
                    details="Zero progress detected in current loop iteration",
                )

        return LoopResult(
            exit_reason=LoopExitReason.BUDGET_EXCEEDED,
            task_states=self.task_states,
            iterations=iteration,
            events_count=(len(self.event_store.read_all()) - events_start) if self.event_store else 0,
            details=f"Max iteration budget ({self.max_iterations}) exceeded",
        )
