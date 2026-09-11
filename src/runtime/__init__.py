"""Runtime adapters package (docs/04 §4)."""
from src.runtime.base import HealthStatus, RuntimeAdapter, RuntimeDoctorResult, RuntimeFeatures
from src.runtime.claude import ClaudeCodeRuntime
from src.runtime.gemini import GeminiCliRuntime
from src.runtime.mock import MockRuntime

__all__ = [
    "HealthStatus",
    "RuntimeAdapter",
    "RuntimeDoctorResult",
    "RuntimeFeatures",
    "ClaudeCodeRuntime",
    "GeminiCliRuntime",
    "MockRuntime",
]
