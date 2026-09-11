"""Tests for NextJsBlueprint and NodeExpressBlueprint."""
from pathlib import Path

from src.blueprints.nextjs import NextJsBlueprint
from src.blueprints.node_express import NodeExpressBlueprint
from src.models.project import ProjectSpec
from src.plugins.registry import plugin_registry
from src.workspace.workspace import Workspace


def test_nextjs_blueprint_scaffold_and_infra(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    spec = ProjectSpec(name="E-Commerce Storefront", prompt="Build an e-commerce storefront")

    bp = plugin_registry.get_blueprint("nextjs")
    assert bp is not None
    assert bp.name == "nextjs"

    # 1. Scaffold
    scaffold_paths = bp.generate_scaffold(ws, spec)
    assert len(scaffold_paths) > 0
    pkg_file = ws.frontend_dir / "package.json"
    assert pkg_file.exists()
    assert "next" in pkg_file.read_text(encoding="utf-8")
    assert (ws.frontend_dir / "src" / "app" / "page.js").exists()
    assert (ws.frontend_dir / "src" / "components" / "Header.js").exists()

    # 2. Infra
    infra_paths = bp.generate_infra(ws, spec)
    assert len(infra_paths) > 0
    assert (ws.frontend_dir / "Dockerfile").exists()
    assert (ws.frontend_dir / "docker-compose.yml").exists()

    # 3. Tests
    test_paths = bp.generate_tests(ws, spec)
    assert len(test_paths) > 0
    assert (ws.frontend_dir / "tests" / "page.test.js").exists()


def test_node_express_blueprint_scaffold_and_infra(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure_directories()
    spec = ProjectSpec(name="Customer Microservice", prompt="Build a customer microservice")

    bp = plugin_registry.get_blueprint("node_express")
    assert bp is not None
    assert bp.name == "node_express"

    # 1. Scaffold
    scaffold_paths = bp.generate_scaffold(ws, spec)
    assert len(scaffold_paths) > 0
    pkg_file = ws.backend_dir / "package.json"
    assert pkg_file.exists()
    assert "express" in pkg_file.read_text(encoding="utf-8")
    assert (ws.backend_dir / "src" / "server.js").exists()
    assert (ws.backend_dir / "src" / "routes" / "items.js").exists()

    # 2. Infra
    infra_paths = bp.generate_infra(ws, spec)
    assert len(infra_paths) > 0
    assert (ws.backend_dir / "Dockerfile").exists()
    assert (ws.backend_dir / "docker-compose.yml").exists()

    # 3. Tests
    test_paths = bp.generate_tests(ws, spec)
    assert len(test_paths) > 0
    assert (ws.backend_dir / "tests" / "api.test.js").exists()
