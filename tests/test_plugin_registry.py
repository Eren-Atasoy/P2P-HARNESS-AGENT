"""Unit tests for PluginRegistry and dynamic plugin extensions (Faz 9)."""
from pathlib import Path
from src.blueprints.base import Blueprint
from src.models.enums import TargetType, TaskOutcome
from src.models.project import ProjectSpec
from src.models.result import AgentResult
from src.models.task import TaskContract
from src.plugins.registry import PluginRegistry, plugin_registry
from src.runtime.base import RuntimeAdapter
from src.workspace.workspace import Workspace


class CustomDummyAdapter(RuntimeAdapter):
    def execute(self, contract: TaskContract, workspace: Path, run_id: str = None) -> AgentResult:
        return AgentResult(
            task_id=contract.id,
            run_id="custom-run",
            outcome=TaskOutcome.COMPLETED,
            summary="Custom third-party runtime executed",
            files_changed=[],
            criteria_addressed=[],
            assumptions=[],
        )


class CustomDummyBlueprint(Blueprint):
    @property
    def name(self) -> str:
        return "custom_bp"

    @property
    def targets(self) -> list[TargetType]:
        return [TargetType.LIBRARY]

    def generate_scaffold(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        return []

    def generate_infra(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        return []

    def generate_tests(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        return []


def test_builtin_plugins_registered():
    assert plugin_registry.has_runtime("mock")
    assert plugin_registry.has_runtime("claude_code")
    assert plugin_registry.has_runtime("gemini_cli")
    assert plugin_registry.has_runtime("api")
    assert plugin_registry.has_runtime("ollama")

    blueprints = plugin_registry.list_blueprints()
    assert "fastapi" in blueprints
    assert "python_cli" in blueprints


def test_dynamic_runtime_registration():
    custom_registry = PluginRegistry()
    custom_registry.register_runtime("custom_dummy", lambda **kwargs: CustomDummyAdapter())

    assert custom_registry.has_runtime("custom_dummy")
    adapter = custom_registry.get_runtime("custom_dummy")
    assert isinstance(adapter, CustomDummyAdapter)


def test_dynamic_blueprint_registration():
    custom_registry = PluginRegistry()
    custom_registry.register_blueprint("custom_bp", CustomDummyBlueprint)

    assert "custom_bp" in custom_registry.list_blueprints()
    bp = custom_registry.get_blueprint("custom_bp")
    assert isinstance(bp, CustomDummyBlueprint)
    assert bp.name == "custom_bp"
