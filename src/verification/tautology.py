"""Tautology Scanner: Detects fake, vacuous, and tautological tests using AST analysis (docs/05 §7).

Prevents AI models from producing self-fulfilling or meaningless tests:
- 'assert True', 'assert 1 == 1', 'assert not False'
- Empty test bodies ('def test_...(): pass')
- Tests with zero assertion statements or verify calls
"""
import ast
from pathlib import Path
from typing import Optional

from src.models.result import GateFailure


class TautologyVisitor(ast.NodeVisitor):
    """AST visitor identifying fake or vacuous test patterns."""

    def __init__(self, filename: str):
        self.filename = filename
        self.failures: list[GateFailure] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not node.name.startswith("test_"):
            self.generic_visit(node)
            return

        # 1. Check for empty test body (pass, docstring only, or ellipsis)
        real_stmts = []
        for stmt in node.body:
            if isinstance(stmt, ast.Pass):
                continue
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Ellipsis)):
                continue
            real_stmts.append(stmt)

        if not real_stmts:
            self.failures.append(
                GateFailure(
                    file=self.filename,
                    line=node.lineno,
                    rule="tautology/empty-test",
                    message=f"Test function '{node.name}' has an empty body without assertions.",
                )
            )
            return

        # 2. Check for presence of assertions or verify calls
        has_assertion = False
        for stmt in node.body:
            if isinstance(stmt, ast.Assert):
                has_assertion = True
                self._check_assert_tautology(stmt, node.name)
            else:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Assert):
                        has_assertion = True
                        self._check_assert_tautology(sub, node.name)
                    elif isinstance(sub, ast.Call):
                        fn = sub.func
                        fn_name = ""
                        if isinstance(fn, ast.Name):
                            fn_name = fn.id
                        elif isinstance(fn, ast.Attribute):
                            fn_name = fn.attr
                        if any(k in fn_name.lower() for k in ["assert", "expect", "verify", "check", "tobe", "toequal"]):
                            has_assertion = True

        if not has_assertion:
            self.failures.append(
                GateFailure(
                    file=self.filename,
                    line=node.lineno,
                    rule="tautology/no-assertions",
                    message=f"Test function '{node.name}' contains no assertions or verification calls.",
                )
            )

        self.generic_visit(node)

    def _check_assert_tautology(self, node: ast.Assert, func_name: str):
        test = node.test

        # Pattern 1: assert True / assert 1 / assert "truthy literal"
        if isinstance(test, ast.Constant):
            if bool(test.value) is True:
                self.failures.append(
                    GateFailure(
                        file=self.filename,
                        line=node.lineno,
                        rule="tautology/literal-assert",
                        message=f"Vacuous literal 'assert {test.value}' detected in '{func_name}'.",
                    )
                )
                return

        # Pattern 2: assert not False / assert not None
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            if isinstance(test.operand, ast.Constant):
                if not bool(test.operand.value):
                    self.failures.append(
                        GateFailure(
                            file=self.filename,
                            line=node.lineno,
                            rule="tautology/literal-not-assert",
                            message=f"Vacuous literal 'assert not {test.operand.value}' detected in '{func_name}'.",
                        )
                    )
                    return

        # Pattern 3: assert literal == literal (e.g. 1 == 1, "a" == "a")
        if isinstance(test, ast.Compare):
            if len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                left = test.left
                right = test.comparators[0]
                if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                    if left.value == right.value:
                        self.failures.append(
                            GateFailure(
                                file=self.filename,
                                line=node.lineno,
                                rule="tautology/identical-compare",
                                message=f"Tautological comparison 'assert {left.value} == {right.value}' detected in '{func_name}'.",
                            )
                        )
                        return


class TautologyScanner:
    """Scans test source code or directories for vacuous test patterns."""

    @staticmethod
    def scan_code(source_code: str, filename: str = "test_source.py") -> list[GateFailure]:
        try:
            tree = ast.parse(source_code, filename=filename)
        except SyntaxError as e:
            return [
                GateFailure(
                    file=filename,
                    line=e.lineno,
                    rule="syntax-error",
                    message=f"Syntax error during tautology scan: {e.msg}",
                )
            ]
        visitor = TautologyVisitor(filename)
        visitor.visit(tree)
        return visitor.failures

    @staticmethod
    def scan_file(filepath: Path) -> list[GateFailure]:
        path = Path(filepath)
        if not path.exists() or not path.name.endswith(".py"):
            return []
        content = path.read_text(encoding="utf-8")
        return TautologyScanner.scan_code(content, filename=str(path))

    @staticmethod
    def scan_directory(dirpath: Path) -> list[GateFailure]:
        path = Path(dirpath)
        all_failures: list[GateFailure] = []
        if not path.exists():
            return all_failures

        for p in path.rglob("test_*.py"):
            all_failures.extend(TautologyScanner.scan_file(p))
        return all_failures
