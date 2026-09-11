"""Unit tests for TautologyScanner (Faz 8)."""
from pathlib import Path
from src.verification.tautology import TautologyScanner


def test_tautology_literal_assert():
    code = """
def test_fake_one():
    assert True

def test_fake_two():
    assert not False

def test_fake_three():
    assert 1 == 1

def test_fake_four():
    assert "abc" == "abc"
"""
    failures = TautologyScanner.scan_code(code, "test_fake.py")
    assert len(failures) == 4
    rules = [f.rule for f in failures]
    assert "tautology/literal-assert" in rules
    assert "tautology/literal-not-assert" in rules
    assert "tautology/identical-compare" in rules


def test_tautology_empty_and_no_assert():
    code = """
def test_empty_pass():
    pass

def test_empty_docstring_only():
    '''This is a test without statements.'''

def test_no_assertions():
    x = 10
    y = 20
    total = x + y
"""
    failures = TautologyScanner.scan_code(code, "test_empty.py")
    assert len(failures) == 3
    rules = [f.rule for f in failures]
    assert rules.count("tautology/empty-test") == 2
    assert "tautology/no-assertions" in rules


def test_tautology_valid_tests():
    code = """
def test_real_addition():
    assert 2 + 2 == 4

def test_expect_call():
    expect(response.status_code).toBe(200)

def test_verify_token():
    verify_token("token123")
"""
    failures = TautologyScanner.scan_code(code, "test_valid.py")
    assert len(failures) == 0
