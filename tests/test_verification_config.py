"""Unit tests for GatesConfig and GateDefinition."""

from pathlib import Path
from src.models.enums import GateStatus
from src.verification.config import GateDefinition, GatesConfig


def test_gates_config_default() -> None:
    config = GatesConfig.default_config()
    assert "unit" in config.gates
    assert "smoke" in config.gates
    assert config.gates["smoke"].isolation == "serialized"
    assert config.gates["unit"].parse == "pytest"


def test_gates_config_load_from_dict() -> None:
    data = {
        "gates": {
            "custom_lint": {
                "cmd": ["flake8", "."],
                "cwd": "backend",
                "timeout_s": 60,
                "on_missing_tool": "ERROR",
                "parse": "none",
                "isolation": "none",
            }
        }
    }
    config = GatesConfig.load_from_dict(data)
    assert "custom_lint" in config.gates
    gate = config.gates["custom_lint"]
    assert gate.cmd == ["flake8", "."]
    assert gate.cwd == "backend"
    assert gate.timeout_s == 60
    assert gate.on_missing_tool == GateStatus.ERROR


def test_gates_config_load_from_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "gates.yaml"
    yaml_file.write_text(
        """
gates:
  unit:
    cmd: ["pytest"]
    timeout_s: 180
    parse: "pytest"
""",
        encoding="utf-8",
    )
    config = GatesConfig.load_from_yaml(yaml_file)
    assert "unit" in config.gates
    assert config.gates["unit"].timeout_s == 180
