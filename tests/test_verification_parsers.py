"""Unit tests for verification output parsers."""

from src.verification.parsers import (
    EslintParser,
    NoneParser,
    PytestParser,
    RuffParser,
    TscParser,
    get_parser,
)


def test_pytest_parser_success() -> None:
    parser = PytestParser()
    failures = parser.parse("2 passed in 0.12s", "", 0)
    assert len(failures) == 0


def test_pytest_parser_failure() -> None:
    parser = PytestParser()
    sample_output = """
============================= test session starts =============================
tests/test_api.py .F.                                                    [100%]

================================== FAILURES ===================================
__________________________________ test_auth __________________________________
tests/test_api.py:42: in test_auth
    assert response.status_code == 200
E   assert 401 == 200

=========================== short test summary info ===========================
FAILED tests/test_api.py::test_auth - assert 401 == 200
========================= 1 failed, 2 passed in 0.45s =========================
"""
    failures = parser.parse(sample_output, "", 1)
    assert len(failures) >= 1
    assert failures[0].file == "tests/test_api.py"
    assert failures[0].rule == "test_auth"
    assert "assert 401 == 200" in failures[0].message


def test_tsc_parser_failure() -> None:
    parser = TscParser()
    sample_output = """
src/components/Button.tsx:24:5 - error TS2322: Type 'string' is not assignable to type 'number'.
src/utils/api.ts(10,3): error TS7006: Parameter 'data' implicitly has an 'any' type.
"""
    failures = parser.parse(sample_output, "", 1)
    assert len(failures) == 2
    assert failures[0].file == "src/components/Button.tsx"
    assert failures[0].line == 24
    assert failures[0].rule == "TS2322"
    assert "Type 'string' is not assignable to type 'number'" in failures[0].message

    assert failures[1].file == "src/utils/api.ts"
    assert failures[1].line == 10
    assert failures[1].rule == "TS7006"


def test_eslint_parser_failure() -> None:
    parser = EslintParser()
    sample_output = """
frontend/src/App.tsx
  14:7  error  'user' is assigned a value but never used  @typescript-eslint/no-unused-vars
  28:3  error  Unexpected console statement               no-console

frontend/src/main.tsx
  5:1   error  Missing semicolon                          semi
"""
    failures = parser.parse(sample_output, "", 1)
    assert len(failures) == 3
    assert failures[0].file == "frontend/src/App.tsx"
    assert failures[0].line == 14
    assert failures[0].rule == "@typescript-eslint/no-unused-vars"

    assert failures[2].file == "frontend/src/main.tsx"
    assert failures[2].rule == "semi"


def test_ruff_parser_failure() -> None:
    parser = RuffParser()
    sample_output = """
backend/api/users.py:12:1: F401 `os` imported but unused
backend/api/auth.py:45:5: E711 Comparison to `None` should be `cond is None`
"""
    failures = parser.parse(sample_output, "", 1)
    assert len(failures) == 2
    assert failures[0].file == "backend/api/users.py"
    assert failures[0].line == 12
    assert failures[0].rule == "F401"
    assert "imported but unused" in failures[0].message


def test_none_parser_fallback() -> None:
    parser = NoneParser()
    failures = parser.parse("Command failed abruptly", "fatal: out of memory", 137)
    assert len(failures) == 1
    assert "fatal: out of memory" in failures[0].message


def test_get_parser_factory() -> None:
    assert isinstance(get_parser("pytest"), PytestParser)
    assert isinstance(get_parser("tsc"), TscParser)
    assert isinstance(get_parser("eslint"), EslintParser)
    assert isinstance(get_parser("ruff"), RuffParser)
    assert isinstance(get_parser("unknown"), NoneParser)
