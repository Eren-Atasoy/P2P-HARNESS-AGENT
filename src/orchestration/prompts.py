"""Prompt compiler for implementer, fix, and review roles (docs/03 §3.1, ADR-008)."""
from typing import Optional

from src.models.result import AgentResult, Failure, ReviewResult
from src.models.task import TaskContract


class PromptCompiler:
    """Compiles structured, scoped prompts adhering to trust boundaries and narrow shell policies."""

    @staticmethod
    def truncate_lines(text: str, max_head: int = 50, max_tail: int = 50) -> str:
        """Truncates long output to first N lines and last N lines (docs/03 §3.1)."""
        lines = text.splitlines()
        if len(lines) <= max_head + max_tail:
            return text
        head = lines[:max_head]
        tail = lines[-max_tail:]
        omitted = len(lines) - (max_head + max_tail)
        return "\n".join(head + [f"\n... [TRUNCATED {omitted} LINES OF OUTPUT] ...\n"] + tail)

    @classmethod
    def compile_implementer_prompt(cls, contract: TaskContract) -> str:
        """Builds implementation prompt strictly bound to TaskContract and allowed paths."""
        ac_lines = "\n".join([f"- [{ac.id}] {ac.statement}" for ac in contract.acceptance_criteria])
        allowed = "\n".join([f"- {p}" for p in contract.allowed_paths])
        forbidden = "\n".join([f"- {p}" for p in contract.forbidden_paths]) if contract.forbidden_paths else "- (None)"

        return f"""# TASK IMPLEMENTATION CONTRACT: {contract.id}
Title: {contract.title}
Risk: {contract.risk.value}

## Intent
{contract.intent}

## Scope Boundaries (HARD ENFORCEMENT)
Allowed paths (You MAY edit only these):
{allowed}

Forbidden paths (NEVER touch these):
{forbidden}

Result path: {contract.result_path}
ACR path: {contract.acr_path}

## Acceptance Criteria
{ac_lines}

## Instructions & Shell Policy (ADR-008)
1. Write the code satisfying all acceptance criteria within allowed paths.
2. Shell Access: You may run ONLY the test runner (e.g. `pytest`, `npm test`) to prove your work. Any other command will be rejected.
3. Write your final structured result in JSON format to: `{contract.result_path}`.
"""

    @classmethod
    def compile_fix_prompt(
        cls,
        contract: TaskContract,
        previous_result: Optional[AgentResult] = None,
        failures: Optional[list[Failure]] = None,
        raw_gate_output: Optional[str] = None,
        review: Optional[ReviewResult] = None,
    ) -> str:
        """Builds focused repair prompt (docs/03 §3.1).

        Includes:
        1. Original TaskContract summary & scope
        2. Previous attempt summary
        3. Truncated failure output (first 50 + last 50 lines)
        4. Structured review findings if present
        5. Strict instruction: 'Sadece bu bulguları gider. Başka refactor yapma.'
        """
        prompt_parts = [
            f"# FIX ATTEMPT FOR TASK: {contract.id} ({contract.title})",
            "\n## CRITICAL DIRECTIVE\n"
            "> **Sadece bu bulguları gider. Başka refactor yapma.**\n"
            "> Do NOT refactor or touch unrelated code. Fix only the specific failures identified below.",
        ]

        if previous_result and previous_result.summary:
            prompt_parts.append(f"\n## Previous Attempt Summary\n{previous_result.summary}")

        if failures:
            failure_lines = []
            for f in failures:
                loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or "general")
                rule = f" [{f.rule}]" if f.rule else ""
                failure_lines.append(f"- {loc}{rule}: {f.message}")
            prompt_parts.append("\n## Quality Gate Failures\n" + "\n".join(failure_lines))

        if raw_gate_output:
            truncated = cls.truncate_lines(raw_gate_output, 50, 50)
            prompt_parts.append(f"\n## Raw Gate Output (Truncated First 50 + Last 50 lines)\n```text\n{truncated}\n```")

        if review and review.findings:
            review_lines = [
                f"- [{finding.severity.value}] {finding.file}:{finding.line or ''} {finding.issue}"
                for finding in review.findings
            ]
            prompt_parts.append("\n## Architect Review Findings\n" + "\n".join(review_lines))

        allowed = "\n".join([f"- {p}" for p in contract.allowed_paths])
        prompt_parts.append(f"\n## Allowed Paths\n{allowed}\nResult Path: {contract.result_path}")
        prompt_parts.append("\nFix the issues, run tests to verify, and write updated result JSON to result_path.")

        return "\n".join(prompt_parts)

    @classmethod
    def compile_review_prompt(cls, contract: TaskContract, git_diff: str) -> str:
        """Builds code review prompt for architect role."""
        ac_lines = "\n".join([f"- [{ac.id}] {ac.statement}" for ac in contract.acceptance_criteria])
        truncated_diff = cls.truncate_lines(git_diff, 100, 100)

        return f"""# ARCHITECT REVIEW: {contract.id} ({contract.title})

## Acceptance Criteria to Verify
{ac_lines}

## Git Diff
```diff
{truncated_diff}
```

## Review Instructions
Review the diff against the acceptance criteria, security guidelines, and architectural integrity.
Report your verdict (APPROVED, CHANGES_REQUESTED, or REJECTED) with structured findings.
"""
