"""Unit tests for ImpactAnalyzer (Faz 8)."""
from pathlib import Path
from src.verification.regression import ImpactAnalyzer


def test_impact_analyzer_localized_change(tmp_path: Path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    t_auth = tests_dir / "test_auth.py"
    t_auth.write_text("import app.auth\ndef test_auth(): pass", encoding="utf-8")

    t_items = tests_dir / "test_items.py"
    t_items.write_text("import app.items\ndef test_items(): pass", encoding="utf-8")

    t_users = tests_dir / "test_users.py"
    t_users.write_text("import app.users\ndef test_users(): pass", encoding="utf-8")

    analyzer = ImpactAnalyzer(tmp_path)

    # When only auth.py changes, only test_auth.py should be selected
    affected = analyzer.select_affected_tests(["backend/app/auth.py"])
    assert len(affected) == 1
    assert affected[0] == t_auth


def test_impact_analyzer_global_trigger(tmp_path: Path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    t_1 = tests_dir / "test_one.py"
    t_1.write_text("def test_1(): pass", encoding="utf-8")

    t_2 = tests_dir / "test_two.py"
    t_2.write_text("def test_2(): pass", encoding="utf-8")

    analyzer = ImpactAnalyzer(tmp_path)

    # When requirements.txt or conftest.py changes, ALL tests must run
    affected = analyzer.select_affected_tests(["requirements.txt"])
    assert len(affected) == 2
    assert t_1 in affected and t_2 in affected
