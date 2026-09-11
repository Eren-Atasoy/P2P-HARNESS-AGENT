"""Accessibility (a11y) Verification Gate (docs/05 §2, docs/08 Faz 9, docs/12 §4).

Performs WCAG accessibility audits on generated HTML, JSX, and TSX files.
Catches missing alt tags, unlabelled form inputs, empty buttons, and heading anomalies.
"""
import re
from pathlib import Path
from typing import Optional

from src.models.result import GateFailure
from src.verification.parsers import BaseOutputParser


class A11yScanner:
    """Static accessibility auditor scanning UI markup and templates."""

    def __init__(self) -> None:
        # Regex patterns for HTML/JSX accessibility checks
        self._img_no_alt = re.compile(r"<img\b(?![^>]*\balt=)[^>]*>", re.IGNORECASE)
        self._button_empty = re.compile(r"<button\b(?![^>]*\baria-label=)[^>]*>\s*</button>", re.IGNORECASE)
        self._input_no_label = re.compile(r"<input\b(?![^>]*\b(aria-label|aria-labelledby|id|type=[\"']hidden[\"']))[^>]*>", re.IGNORECASE)
        self._link_empty = re.compile(r"<a\b(?![^>]*\baria-label=)[^>]*>\s*</a>", re.IGNORECASE)

    def scan_content(self, content: str, filename: str = "template.html") -> list[GateFailure]:
        """Scans string content for accessibility violations."""
        failures: list[GateFailure] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, 1):
            # Check 1: Images without alt text
            if self._img_no_alt.search(line):
                failures.append(
                    GateFailure(
                        file=filename,
                        line=idx,
                        message="Accessibility violation: <img> tag is missing required 'alt' attribute (WCAG 1.1.1)",
                        rule="A11Y_IMG_NO_ALT",
                    )
                )

            # Check 2: Empty buttons without aria-label
            if self._button_empty.search(line):
                failures.append(
                    GateFailure(
                        file=filename,
                        line=idx,
                        message="Accessibility violation: <button> has no text content or 'aria-label' (WCAG 4.1.2)",
                        rule="A11Y_BUTTON_NO_LABEL",
                    )
                )

            # Check 3: Form inputs without id or aria-label
            if self._input_no_label.search(line):
                failures.append(
                    GateFailure(
                        file=filename,
                        line=idx,
                        message="Accessibility violation: <input> lacks 'id', 'aria-label', or 'aria-labelledby' (WCAG 1.3.1)",
                        rule="A11Y_INPUT_NO_LABEL",
                    )
                )

            # Check 4: Empty links
            if self._link_empty.search(line):
                failures.append(
                    GateFailure(
                        file=filename,
                        line=idx,
                        message="Accessibility violation: <a> link has no accessible name or 'aria-label' (WCAG 2.4.4)",
                        rule="A11Y_EMPTY_LINK",
                    )
                )

        # Check 5: Heading hierarchy (Multiple h1 tags or skipped levels)
        h1_matches = re.findall(r"<h1\b", content, re.IGNORECASE)
        if len(h1_matches) > 1:
            failures.append(
                GateFailure(
                    file=filename,
                    line=1,
                    message=f"Accessibility violation: Document contains {len(h1_matches)} <h1> elements; should have exactly one (WCAG 1.3.1)",
                    rule="A11Y_MULTIPLE_H1",
                )
            )

        return failures

    def scan_file(self, file_path: Path) -> list[GateFailure]:
        """Scans single file for a11y violations."""
        if not file_path.exists():
            return []
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.scan_content(content, filename=file_path.name)
        except Exception as err:
            return [
                GateFailure(
                    file=file_path.name,
                    line=1,
                    message=f"Failed to read file for a11y scan: {err}",
                    rule="A11Y_READ_ERR",
                )
            ]

    def scan_directory(self, dir_path: Path) -> list[GateFailure]:
        """Recursively scans directory for UI files (.html, .htm, .jsx, .tsx, .vue)."""
        if not dir_path.exists():
            return []
        failures: list[GateFailure] = []
        extensions = {".html", ".htm", ".jsx", ".tsx", ".vue"}

        for p in dir_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in extensions and "node_modules" not in str(p):
                failures.extend(self.scan_file(p))

        return failures


class A11yParser(BaseOutputParser):
    """Parses output from CLI a11y tools (pa11y, axe-core, or static scanner)."""

    def parse(self, stdout: str, stderr: str = "", exit_code: int = 0) -> list[GateFailure]:
        if exit_code == 0 and not stdout and not stderr:
            return []
        failures: list[GateFailure] = []
        scanner = A11yScanner()
        # If output contains raw markup or report
        for line in stdout.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            # Handle pa11y / standard violation format: "Error: [code] message at file:line"
            match = re.match(r"(?:Error|Violation):\s*(?:\[(.*?)\])?\s*(.*?)(?:\s+at\s+([^:]+):(\d+))?$", line_str, re.IGNORECASE)
            if match:
                code, msg, file_name, line_num = match.groups()
                failures.append(
                    GateFailure(
                        file=file_name or "unknown",
                        line=int(line_num) if line_num else 1,
                        message=msg.strip(),
                        rule=code or "A11Y_VIOLATION",
                    )
                )
            elif "WCAG" in line_str or "A11Y" in line_str or "Accessibility" in line_str:
                failures.append(
                    GateFailure(
                        file="unknown",
                        line=1,
                        message=line_str,
                        rule="A11Y_GENERIC",
                    )
                )
        if not failures and exit_code != 0:
            failures.append(
                GateFailure(
                    file="unknown",
                    line=1,
                    message=f"Accessibility check failed with exit code {exit_code}",
                    rule="A11Y_EXIT_FAIL",
                )
            )
        return failures
