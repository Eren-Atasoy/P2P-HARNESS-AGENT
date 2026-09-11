"""Unit tests for ProjectAuditor (security, tautologies, vendor-independence)."""
from pathlib import Path
from src.verification.audit import ProjectAuditor


def test_audit_detects_secret_leak(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    bad_code = """
def connect_api():
    # Dangerous hardcoded token
    api_key = "ghp_123456789012345678901234567890123456"
    return api_key
"""
    (src_dir / "service.py").write_text(bad_code)

    auditor = ProjectAuditor(tmp_path)
    report = auditor.audit()

    assert report.passed is False
    assert report.critical_count >= 1
    categories = [i.category for i in report.issues]
    assert "SECRET_LEAK" in categories


def test_audit_detects_tautologies_in_tests(tmp_path: Path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    tautology_code = """
def test_fake():
    assert True
"""
    (tests_dir / "test_fake.py").write_text(tautology_code)

    auditor = ProjectAuditor(tmp_path)
    report = auditor.audit()

    assert report.passed is False
    assert report.high_count >= 1
    categories = [i.category for i in report.issues]
    assert "TAUTOLOGY" in categories


def test_audit_passes_on_clean_code(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    clean_code = """
import os

def get_token():
    return os.environ.get("SERVICE_TOKEN")
"""
    (src_dir / "clean.py").write_text(clean_code)

    auditor = ProjectAuditor(tmp_path)
    report = auditor.audit()

    assert report.passed is True
    assert report.critical_count == 0
    assert report.high_count == 0
