"""Extensible Plugin and Registry architecture for Prompt2Product (docs/08 Faz 9).

Allows registering custom RuntimeAdapters, Blueprints, and Quality Gates
without modifying the core orchestrator or pipeline codebase.
"""
from typing import Any, Callable, Optional, Type
from pathlib import Path

from src.blueprints.base import Blueprint
from src.runtime.base import RuntimeAdapter


class PluginRegistry:
    """Central registry for runtime adapters, project blueprints, and quality gates."""

    def __init__(self) -> None:
        self._runtimes: dict[str, Callable[..., RuntimeAdapter]] = {}
        self._blueprints: dict[str, Type[Blueprint]] = {}
        self._gates: dict[str, Any] = {}

    # --- Runtime Adapters ---
    def register_runtime(self, name: str, adapter_factory: Callable[..., RuntimeAdapter]) -> None:
        """Registers a runtime adapter factory by name."""
        self._runtimes[name.lower()] = adapter_factory

    def get_runtime(self, name: str, **kwargs: Any) -> Optional[RuntimeAdapter]:
        """Instantiates and returns a runtime adapter by name, or None if not found."""
        factory = self._runtimes.get(name.lower())
        if factory is None:
            return None
        return factory(**kwargs)

    def list_runtimes(self) -> list[str]:
        """Returns sorted list of registered runtime names."""
        return sorted(self._runtimes.keys())

    def has_runtime(self, name: str) -> bool:
        """Returns True if runtime is registered."""
        return name.lower() in self._runtimes

    # --- Blueprints ---
    def register_blueprint(self, name: str, blueprint_cls: Type[Blueprint]) -> None:
        """Registers a project blueprint class by name."""
        self._blueprints[name.lower()] = blueprint_cls

    def get_blueprint(self, name: str, **kwargs: Any) -> Optional[Blueprint]:
        """Instantiates and returns a blueprint by name, or None if not found."""
        cls = self._blueprints.get(name.lower())
        if cls is None:
            return None
        return cls(**kwargs)

    def list_blueprints(self) -> list[str]:
        """Returns sorted list of registered blueprint names."""
        return sorted(self._blueprints.keys())

    # --- Quality Gates ---
    def register_gate(self, name: str, gate_handler: Any) -> None:
        """Registers a custom quality gate parser or runner."""
        self._gates[name.lower()] = gate_handler

    def get_gate(self, name: str) -> Optional[Any]:
        """Returns registered gate handler or None."""
        return self._gates.get(name.lower())

    def list_gates(self) -> list[str]:
        """Returns sorted list of registered gate names."""
        return sorted(self._gates.keys())


# Singleton instance
plugin_registry = PluginRegistry()


def _init_builtin_plugins() -> None:
    """Registers standard built-in runtimes and blueprints into registry."""
    from src.runtime.mock import MockRuntime
    from src.runtime.claude import ClaudeCodeRuntime
    from src.runtime.gemini import GeminiCliRuntime
    from src.runtime.api import ApiRuntime
    from src.runtime.ollama import OllamaRuntime
    from src.blueprints.fastapi import FastApiBlueprint
    from src.blueprints.nextjs import NextJsBlueprint
    from src.blueprints.node_express import NodeExpressBlueprint
    from src.blueprints.python_cli import PythonCliBlueprint

    plugin_registry.register_runtime("mock", lambda **kwargs: MockRuntime(**kwargs))
    plugin_registry.register_runtime("claude_code", lambda **kwargs: ClaudeCodeRuntime(**kwargs))
    plugin_registry.register_runtime("gemini_cli", lambda **kwargs: GeminiCliRuntime(**kwargs))
    plugin_registry.register_runtime("api", lambda **kwargs: ApiRuntime(**kwargs))
    plugin_registry.register_runtime("ollama", lambda **kwargs: OllamaRuntime(**kwargs))
    plugin_registry.register_blueprint("fastapi", FastApiBlueprint)
    plugin_registry.register_blueprint("nextjs", NextJsBlueprint)
    plugin_registry.register_blueprint("node_express", NodeExpressBlueprint)
    plugin_registry.register_blueprint("python_cli", PythonCliBlueprint)


_init_builtin_plugins()
