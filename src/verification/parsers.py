"""Output parsers for verification gates.

Transforms raw CLI stdout/stderr from pytest, tsc, eslint, and ruff
into structured GateFailure objects per docs/05 §6.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import re
from src.models.result import GateFailure


class BaseOutputParser(ABC):
    """Abstract base parser for gate output."""

    @abstractmethod
    def parse(self, stdout: str, stderr: str, exit_code: int) -> list[GateFailure]:
        """Parse raw output into structured failures."""


class PytestParser(BaseOutputParser):
    """Parser for pytest outputs."""

    # Matches: FAILED tests/test_foo.py::test_bar - AssertionError: msg
    # or FAILED tests/test_foo.py::test_bar
    _FAILED_PATTERN = re.compile(
        r"(?:FAILED|ERROR)\s+([^:\s]+)::(\S+?)(?::(\d+))?(?:\s+-\s+(.*))?$",
        re.MULTILINE,
    )
    _ASSERT_PATTERN = re.compile(r"^E\s+(.*)$", re.MULTILINE)

    def parse(self, stdout: str, stderr: str, exit_code: int) -> list[GateFailure]:
        if exit_code == 0:
            return []

        text = f"{stdout}\n{stderr}"
        failures: list[GateFailure] = []

        for match in self._FAILED_PATTERN.finditer(text):
            file_path = match.group(1).strip()
            test_name = match.group(2).strip()
            line_str = match.group(3)
            msg = match.group(4) or f"Test failed: {test_name}"

            line_num = int(line_str) if line_str else None
            failures.append(
                GateFailure(
                    file=file_path,
                    line=line_num,
                    rule=test_name,
                    message=msg.strip(),
                )
            )

        if not failures:
            # Fallback if specific pattern not matched but exit code != 0
            err_lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip().startswith("E   ") or "Error:" in line or "FAILED" in line
            ]
            msg = "\n".join(err_lines[:5]) if err_lines else f"Pytest exited with status {exit_code}"
            failures.append(GateFailure(file=None, line=None, rule="pytest", message=msg))

        return failures


class TscParser(BaseOutputParser):
    """Parser for TypeScript compiler (tsc) output."""

    # Matches: src/index.ts:12:5 - error TS2322: Type 'string' is not assignable to type 'number'.
    # or: src/index.ts(12,5): error TS2322: ...
    _TSC_PATTERN = re.compile(
        r"^(.*?)(?:\((\d+),\s*\d+\):?|:(\d+):\d+)(?: -)?\s+error\s+(TS\d+):\s+(.*)$",
        re.MULTILINE,
    )

    def parse(self, stdout: str, stderr: str, exit_code: int) -> list[GateFailure]:
        if exit_code == 0:
            return []

        text = f"{stdout}\n{stderr}"
        failures: list[GateFailure] = []

        for match in self._TSC_PATTERN.finditer(text):
            file_path = match.group(1).strip()
            line_str = match.group(2) or match.group(3)
            rule = match.group(4).strip()
            msg = match.group(5).strip()

            failures.append(
                GateFailure(
                    file=file_path,
                    line=int(line_str) if line_str else None,
                    rule=rule,
                    message=msg,
                )
            )

        if not failures:
            failures.append(
                GateFailure(
                    file=None,
                    line=None,
                    rule="tsc",
                    message=f"TypeScript compiler exited with code {exit_code}",
                )
            )

        return failures


class EslintParser(BaseOutputParser):
    """Parser for ESLint standard text output."""

    _LINE_ERROR = re.compile(
        r"^\s*(\d+):(\d+)\s+error\s+(.*?)\s+([@\w\-\/]+)$",
        re.MULTILINE,
    )

    def parse(self, stdout: str, stderr: str, exit_code: int) -> list[GateFailure]:
        if exit_code == 0:
            return []

        text = f"{stdout}\n{stderr}"
        failures: list[GateFailure] = []
        current_file: str | None = None

        for line in text.splitlines():
            line_str = line.strip()
            # If line looks like a file path (starts with / or has path separator and no spaces)
            if (line_str.endswith(".ts") or line_str.endswith(".tsx") or line_str.endswith(".js")) and " " not in line_str:
                current_file = line_str
                continue

            match = self._LINE_ERROR.match(line)
            if match:
                line_num = int(match.group(1))
                msg = match.group(3).strip()
                rule = match.group(4).strip()
                failures.append(
                    GateFailure(
                        file=current_file,
                        line=line_num,
                        rule=rule,
                        message=msg,
                    )
                )

        if not failures:
            failures.append(
                GateFailure(
                    file=None,
                    line=None,
                    rule="eslint",
                    message=f"ESLint check failed with exit code {exit_code}",
                )
            )

        return failures


class RuffParser(BaseOutputParser):
    """Parser for Ruff linter output."""

    # Matches: path/to/file.py:12:1: F401 `os` imported but unused
    _RUFF_PATTERN = re.compile(
        r"^(.*?):(\d+):\d+:\s+([A-Z]\d+)\s+(.*)$",
        re.MULTILINE,
    )

    def parse(self, stdout: str, stderr: str, exit_code: int) -> list[GateFailure]:
        if exit_code == 0:
            return []

        text = f"{stdout}\n{stderr}"
        failures: list[GateFailure] = []

        for match in self._RUFF_PATTERN.finditer(text):
            file_path = match.group(1).strip()
            line_num = int(match.group(2))
            rule = match.group(3).strip()
            msg = match.group(4).strip()

            failures.append(
                GateFailure(
                    file=file_path,
                    line=line_num,
                    rule=rule,
                    message=msg,
                )
            )

        if not failures:
            failures.append(
                GateFailure(
                    file=None,
                    line=None,
                    rule="ruff",
                    message=f"Ruff linter failed with code {exit_code}",
                )
            )

        return failures


class NoneParser(BaseOutputParser):
    """Fallback parser that emits a generic failure when exit code is non-zero."""

    def parse(self, stdout: str, stderr: str, exit_code: int) -> list[GateFailure]:
        if exit_code == 0:
            return []
        msg = (stderr.strip() or stdout.strip() or f"Command failed with exit code {exit_code}")
        first_line = msg.splitlines()[0] if msg else f"Exit code {exit_code}"
        return [GateFailure(file=None, line=None, rule=None, message=first_line)]


_PARSERS: dict[str, BaseOutputParser] = {
    "pytest": PytestParser(),
    "tsc": TscParser(),
    "eslint": EslintParser(),
    "ruff": RuffParser(),
    "none": NoneParser(),
}


def get_parser(name: str) -> BaseOutputParser:
    """Get parser by name, defaulting to NoneParser."""
    return _PARSERS.get(name.lower(), _PARSERS["none"])
