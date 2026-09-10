"""Enums defining system-wide constants and categories across Prompt2Product.

Matches docs/02, docs/03, and docs/04 bindings strictly.
"""
from enum import Enum


class TargetType(str, Enum):
    WEB = "web"
    API = "api"
    MOBILE = "mobile"
    CLI = "cli"


class Capability(str, Enum):
    ARCHITECTURE = "architecture"
    PLANNING = "planning"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    MIGRATION = "migration"
    TEST = "test"
    BROWSER = "browser"
    SECURITY = "security"
    REVIEW = "review"
    DOCS = "docs"
    DEVOPS = "devops"
    RESEARCH = "research"
    UI = "ui"
    DESIGN_SYSTEM = "design-system"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EstimatedSize(str, Enum):
    S = "S"
    M = "M"
    L = "L"


class VerifiedBy(str, Enum):
    TEST = "test"
    GATE = "gate"
    MANUAL = "manual"


class TaskOutcome(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    GATED = "GATED"
    FIXING = "FIXING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    MERGED = "MERGED"
    PAUSED = "PAUSED"
    UNROUTABLE = "UNROUTABLE"


class GateStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class ReviewVerdict(str, Enum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REJECTED = "REJECTED"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecidedBy(str, Enum):
    HUMAN = "human"
    DEFAULT = "default"


class DecisionKind(str, Enum):
    AMBIGUITY = "ambiguity"
    GATE = "gate"
    STEER = "steer"
    RETRO = "retro"


class AutonomyLevel(str, Enum):
    SUPERVISED = "supervised"
    GUARDED = "guarded"
    FULL = "full"


class ConnectionKind(str, Enum):
    SUBSCRIPTION = "subscription"
    API = "api"
    LOCAL = "local"
    GATEWAY = "gateway"


class RuntimeType(str, Enum):
    CLAUDE_CODE = "claude_code"
    GEMINI_CLI = "gemini_cli"
    API = "api"
    OLLAMA = "ollama"
    MOCK = "mock"


class CostTier(str, Enum):
    FREE = "free"
    SUBSCRIPTION = "subscription"
    METERED = "metered"


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAUTHENTICATED = "unauthenticated"
    UNAVAILABLE = "unavailable"


class AutomationPolicy(str, Enum):
    ALLOWED = "allowed"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    PROJECT_CREATED = "PROJECT_CREATED"
    TASK_CREATED = "TASK_CREATED"
    TASK_STATE_CHANGED = "TASK_STATE_CHANGED"
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    GATE_FINISHED = "GATE_FINISHED"
    REVIEW_FINISHED = "REVIEW_FINISHED"
    DECISION_RECORDED = "DECISION_RECORDED"
    ACR_OPENED = "ACR_OPENED"
    ACR_RESOLVED = "ACR_RESOLVED"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    MERGE_COMPLETED = "MERGE_COMPLETED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    ESCALATED = "ESCALATED"
    TASK_PAUSED = "TASK_PAUSED"
    TASK_UNROUTABLE = "TASK_UNROUTABLE"
    HUMAN_STEERED = "HUMAN_STEERED"
    RETRO_APPLIED = "RETRO_APPLIED"
    CONNECTION_HEALTH = "CONNECTION_HEALTH"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
