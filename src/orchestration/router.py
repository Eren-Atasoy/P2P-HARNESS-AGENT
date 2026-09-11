"""Capability-based task router and diagnostic provider (docs/04 §5)."""
from typing import Optional
from src.models.connection import Connection
from src.models.enums import AutomationPolicy, Capability, HealthStatus
from src.models.task import TaskContract


class UnroutableTaskError(Exception):
    """Raised when no available connection satisfies all required task capabilities."""
    pass


class CapabilityRouter:
    """Routes tasks to the most suitable connection based on capabilities and quality."""

    def __init__(
        self,
        connections: Optional[list[Connection]] = None,
        escalation_map: Optional[dict[str, str]] = None,
    ):
        self.connections = {c.id: c for c in (connections or [])}
        self.escalation_map = escalation_map or {}

    def add_connection(self, connection: Connection) -> None:
        """Adds or updates a connection in the router."""
        self.connections[connection.id] = connection

    def get_candidate_connections(self, task: TaskContract) -> list[Connection]:
        candidates = []
        required_caps = set(task.capabilities)

        for conn in self.connections.values():
            if conn.health == HealthStatus.UNAVAILABLE:
                continue
            if conn.automation_policy == AutomationPolicy.PROHIBITED:
                continue

            conn_caps = set(conn.capabilities)
            if required_caps.issubset(conn_caps):
                candidates.append(conn)

        return candidates

    def route(self, task: TaskContract, attempt: int = 1) -> Connection:
        """
        Routes task to best matching Connection.
        Raises UnroutableTaskError if no connection satisfies all capabilities.
        """
        candidates = self.get_candidate_connections(task)

        if not candidates:
            # Diagnose missing capabilities for actionable error message
            all_provided = set()
            for c in self.connections.values():
                if c.health != HealthStatus.UNAVAILABLE and c.automation_policy != AutomationPolicy.PROHIBITED:
                    all_provided.update(c.capabilities)

            missing = [cap.value for cap in task.capabilities if cap not in all_provided]
            diag = (
                f"UNROUTABLE: Task '{task.id}' requires capabilities {[c.value for c in task.capabilities]}.\n"
                f"Missing capability/capabilities in active connections: {missing or 'No active provider has all combined'}.\n"
                f"Recommendation: Add a connection providing {missing} or reduce task scope."
            )
            raise UnroutableTaskError(diag)

        # On repeated failure attempt, check if escalation map specifies a connection
        if attempt > 1 and self.escalation_map:
            for cap in task.capabilities:
                target_conn_id = self.escalation_map.get(cap.value)
                if target_conn_id and target_conn_id in self.connections:
                    escalated_conn = self.connections[target_conn_id]
                    if escalated_conn in candidates:
                        return escalated_conn

        # Score candidates based on quality score
        def score(conn: Connection) -> tuple[float, str]:
            # Average quality score across required capabilities
            q_sum = sum(conn.quality.get(c.value, 0.5) for c in task.capabilities)
            avg_q = q_sum / len(task.capabilities)
            # Invert connection ID for deterministic tie-breaking
            return (avg_q, conn.id)

        candidates.sort(key=score, reverse=True)
        return candidates[0]
