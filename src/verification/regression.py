"""Impact-based regression selector (docs/05 §2, docs/08 §Faz 8).

Analyzes git diff or changed files to select only the affected test suites,
avoiding expensive full regression runs when changes are localized.
"""
from pathlib import Path
import re


class ImpactAnalyzer:
    """Analyzes file changes and identifies the minimal necessary regression test set."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.tests_dir = self.workspace_root / "tests"

    def select_affected_tests(self, changed_files: list[str]) -> list[Path]:
        """
        Selects test files affected by the given list of changed files.
        Falls back to full test suite if core configs or common definitions change.
        """
        all_tests = list(self.tests_dir.rglob("test_*.py")) if self.tests_dir.exists() else []
        if not changed_files:
            return all_tests

        # 1. Global triggers that require running all tests
        global_triggers = [
            "pyproject.toml",
            "requirements.txt",
            "conftest.py",
            "config.py",
            ".p2p/project.json",
        ]
        for f in changed_files:
            if any(gt in f for gt in global_triggers):
                return all_tests

        selected_tests: set[Path] = set()

        # 2. Direct test modifications
        for f in changed_files:
            p = self.workspace_root / f
            if p in all_tests or (p.name.startswith("test_") and p.name.endswith(".py")):
                selected_tests.add(p)

        # 3. Component mapping (e.g. backend/app/auth.py -> test_auth.py or test_api.py)
        for f in changed_files:
            stem = Path(f).stem  # e.g. "auth", "crud", "models"
            if stem.startswith("test_"):
                continue

            for test_file in all_tests:
                test_content = ""
                try:
                    test_content = test_file.read_text(encoding="utf-8")
                except Exception:
                    pass

                # If test imports the module or matches component stem name
                if stem in test_file.stem or re.search(r"\b" + re.escape(stem) + r"\b", test_content):
                    selected_tests.add(test_file)

        # If nothing specifically matched but changes exist, return all tests to be safe
        return sorted(list(selected_tests or set(all_tests)))
