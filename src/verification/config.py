"""Declarative gate configuration per docs/05 §6."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
import yaml

from src.models.enums import GateStatus


class GateDefinition(BaseModel):
    """Configuration for a single verification gate."""

    cmd: list[str]
    cwd: str = "."
    timeout_s: int = 300
    on_missing_tool: GateStatus = GateStatus.ERROR
    parse: str = "none"
    isolation: str = "none"  # "none" or "serialized"
    required: bool = True


class GatesConfig(BaseModel):
    """Root configuration mapping gate names to their definitions."""

    gates: dict[str, GateDefinition] = Field(default_factory=dict)

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> GatesConfig:
        gates_raw = data.get("gates", {})
        parsed_gates: dict[str, GateDefinition] = {}
        for name, gate_data in gates_raw.items():
            parsed_gates[name] = GateDefinition(**gate_data)
        return cls(gates=parsed_gates)

    @classmethod
    def load_from_yaml(cls, path: Path | str) -> GatesConfig:
        yaml_path = Path(path)
        if not yaml_path.exists():
            return cls.default_config()
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
        return cls.load_from_dict(content)

    @classmethod
    def default_config(cls) -> GatesConfig:
        """Default baseline gates configuration."""
        return cls(
            gates={
                "unit": GateDefinition(
                    cmd=["pytest", "-q", "--tb=short", "tests/"],
                    cwd=".",
                    timeout_s=300,
                    on_missing_tool=GateStatus.ERROR,
                    parse="pytest",
                ),
                "lint": GateDefinition(
                    cmd=["ruff", "check", "."],
                    cwd=".",
                    timeout_s=120,
                    on_missing_tool=GateStatus.ERROR,
                    parse="ruff",
                ),
                "typecheck": GateDefinition(
                    cmd=["npx", "tsc", "--noEmit"],
                    cwd=".",
                    timeout_s=300,
                    on_missing_tool=GateStatus.ERROR,
                    parse="tsc",
                ),
                "smoke": GateDefinition(
                    cmd=["docker", "compose", "up", "-d"],
                    cwd=".",
                    timeout_s=300,
                    isolation="serialized",
                    parse="none",
                ),
                "e2e": GateDefinition(
                    cmd=["npx", "playwright", "test"],
                    cwd=".",
                    timeout_s=600,
                    isolation="serialized",
                    parse="playwright",
                ),
            }
        )

    @classmethod
    def default_gates(cls) -> GatesConfig:
        """Alias for default_config."""
        return cls.default_config()
