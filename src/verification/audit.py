"""Project Auditor for security, secret leaks, tautological tests, and vendor independence (docs/08 Faz 9)."""
import os
import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from src.verification.tautology import TautologyScanner
from src.verification.a11y import A11yScanner


class AuditIssue(BaseModel):
    """Single finding produced by project audit."""
    severity: str = Field(description="'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'")
    category: str = Field(description="'SECRET_LEAK', 'TAUTOLOGY', 'VENDOR_LEAK', 'A11Y', 'HYGIENE'")
    file: str
    line: int
    message: str


class AuditReport(BaseModel):
    """Aggregated audit results for the repository or project workspace."""
    passed: bool
    files_scanned: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    issues: list[AuditIssue] = Field(default_factory=list)


class ProjectAuditor:
    """Performs security, vendor-independence, tautology, and hygiene scans."""

    # Secret scanning patterns
    _SECRET_PATTERNS = [
        (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "OpenAI API key pattern detected", "CRITICAL"),
        (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google API key pattern detected", "CRITICAL"),
        (re.compile(r"ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token detected", "CRITICAL"),
        (re.compile(r"(?:password|secret|api_key)\s*[:=]\s*[\"']([a-zA-Z0-9_\-!@#$%^&*]{8,})[\"']", re.IGNORECASE), "Hardcoded credential/password detected", "HIGH"),
    ]

    # Vendor leakage patterns (Only forbidden in CORE modules: orchestration, planning, workspace, models)
    _CORE_VENDOR_PATTERNS = [
        (re.compile(r"\b(gpt-4o?|claude-3|gemini-1\.5|llama3)\b", re.IGNORECASE), "Direct model name found in core package (violates ADR-009 vendor independence)", "HIGH"),
    ]

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.tautology_scanner = TautologyScanner()
        self.a11y_scanner = A11yScanner()

    def audit(self) -> AuditReport:
        """Runs full audit suite over the project workspace."""
        issues: list[AuditIssue] = []
        files_scanned = 0

        # Scan all non-ignored files
        ignored_parts = {".git", ".venv", "venv", "__pycache__", "node_modules", ".p2p", ".pytest_cache"}

        for p in self.root_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(ign in p.parts for ign in ignored_parts):
                continue

            files_scanned += 1
            rel_path = str(p.relative_to(self.root_dir)).replace("\\", "/")

            # 1. Secret Scanning
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for idx, line in enumerate(content.splitlines(), 1):
                # Ignore test fixture / mock files for secret checks if marked with dummy
                if "dummy" in line.lower() or "mock" in line.lower() or "example" in line.lower():
                    continue

                for pattern, msg, severity in self._SECRET_PATTERNS:
                    if pattern.search(line):
                        issues.append(
                            AuditIssue(
                                severity=severity,
                                category="SECRET_LEAK",
                                file=rel_path,
                                line=idx,
                                message=msg,
                            )
                        )

            # 2. Core Vendor Independence Check (Only within src/orchestration, src/planning, src/models, src/workspace)
            in_core = any(
                p.is_relative_to(self.root_dir / "src" / core_dir)
                for core_dir in ["orchestration", "planning", "models", "workspace"]
                if (self.root_dir / "src" / core_dir).exists()
            )
            if in_core:
                for idx, line in enumerate(content.splitlines(), 1):
                    # Comments or docstrings with ADR explanations are allowed
                    if line.strip().startswith("#") or '"""' in line:
                        continue
                    for pattern, msg, severity in self._CORE_VENDOR_PATTERNS:
                        if pattern.search(line):
                            issues.append(
                                AuditIssue(
                                    severity=severity,
                                    category="VENDOR_LEAK",
                                    file=rel_path,
                                    line=idx,
                                    message=msg,
                                )
                            )

            # 3. Tautology Scanning (for Python test files)
            if (p.name.startswith("test_") or p.name.endswith("_test.py")) and p.suffix == ".py":
                tautologies = self.tautology_scanner.scan_file(p)
                for t in tautologies:
                    issues.append(
                        AuditIssue(
                            severity="HIGH" if (t.rule and "tautology" in t.rule) else "MEDIUM",
                            category="TAUTOLOGY",
                            file=rel_path,
                            line=t.line or 1,
                            message=f"{t.rule}: {t.message}",
                        )
                    )

            # 4. Accessibility Check (for HTML/JSX templates)
            if p.suffix.lower() in {".html", ".htm", ".jsx", ".tsx"}:
                a11y_errs = self.a11y_scanner.scan_file(p)
                for err in a11y_errs:
                    issues.append(
                        AuditIssue(
                            severity="MEDIUM",
                            category="A11Y",
                            file=rel_path,
                            line=err.line or 1,
                            message=err.message,
                        )
                    )

        # Calculate summaries
        crit = sum(1 for i in issues if i.severity == "CRITICAL")
        high = sum(1 for i in issues if i.severity == "HIGH")
        med = sum(1 for i in issues if i.severity == "MEDIUM")
        low = sum(1 for i in issues if i.severity == "LOW")

        passed = (crit == 0 and high == 0)

        return AuditReport(
            passed=passed,
            files_scanned=files_scanned,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            issues=issues,
        )
