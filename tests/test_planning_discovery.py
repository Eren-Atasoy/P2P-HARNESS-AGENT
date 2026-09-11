"""Unit tests for DiscoveryEngine (Faz 6)."""
import json
import pytest
from src.events.store import EventStore
from src.models.enums import AutonomyLevel, DecidedBy, DecisionKind, EventType, TargetType
from src.models.project import ProjectSpec
from src.planning.discovery import DiscoveryEngine, slugify
from src.workspace.workspace import Workspace


def test_slugify():
    assert slugify("Basit bir yapılacaklar API'si!") == "basit-bir-yapilacaklar-apisi"
    assert slugify("---Todo REST Service---") == "todo-rest-service"
    assert slugify("") == "p2p-project"


def test_discovery_engine_api_prompt(tmp_path):
    ws = Workspace(tmp_path)
    store = EventStore(ws.events_path)
    engine = DiscoveryEngine(ws, store)

    prompt = "Basit bir yapılacaklar REST API'si"
    spec, decisions, g1_passed = engine.discover(prompt, autonomy_level=AutonomyLevel.GUARDED)

    assert isinstance(spec, ProjectSpec)
    assert spec.name == "basit-bir-yapilacaklar-rest-apisi"
    assert TargetType.API in spec.targets
    assert spec.stack["backend"] == "fastapi"
    assert spec.stack["database"] == "sqlite"

    # In guarded mode, G1 passes with default choices
    assert g1_passed is True
    assert len(decisions) >= 1
    for d in decisions:
        assert d.kind == DecisionKind.AMBIGUITY
        assert d.decided_by == DecidedBy.DEFAULT

    # Verify project.json written to disk
    assert ws.project_spec_path.exists()
    loaded_data = json.loads(ws.project_spec_path.read_text(encoding="utf-8"))
    assert loaded_data["name"] == spec.name

    # Verify events written
    events = store.read_all()
    event_types = [e.type for e in events]
    assert EventType.PROJECT_CREATED in event_types
    assert EventType.DECISION_RECORDED in event_types


def test_discovery_engine_supervised_mode_gate_g1(tmp_path):
    ws = Workspace(tmp_path)
    engine = DiscoveryEngine(ws)

    prompt = "Minimal web arayüzü ve API"
    spec, decisions, g1_passed = engine.discover(prompt, autonomy_level=AutonomyLevel.SUPERVISED)

    assert TargetType.WEB in spec.targets
    assert TargetType.API in spec.targets
    # In supervised mode with ambiguities, G1 requires human input
    assert g1_passed is False
    for d in decisions:
        assert d.decided_by == DecidedBy.HUMAN
