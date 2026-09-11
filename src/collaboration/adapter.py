"""ReviewToIssueAdapter bridging code review findings to GitHub Issues and Repair Tasks (docs/07 §7).

Implements the autonomous cycle:
Review finding (CRITICAL/HIGH) -> GitHub/Local Issue -> Repair TaskContract -> PR -> Merge -> Close Issue.
"""
from typing import Optional

from src.collaboration.issues import IssueProvider
from src.collaboration.models import Issue, IssueSeverity
from src.collaboration.pull_requests import PRProvider
from src.models.enums import Capability, EstimatedSize, FindingSeverity, RiskLevel, VerifiedBy
from src.models.result import ReviewFinding, ReviewResult
from src.models.task import AcceptanceCriterion, TaskContract


class ReviewToIssueAdapter:
    """Transforms review findings into tracked issues and repair task contracts."""

    def __init__(self, issue_provider: IssueProvider, pr_provider: PRProvider):
        self.issue_provider = issue_provider
        self.pr_provider = pr_provider

    def process_review_findings(
        self,
        review_result: ReviewResult,
        task: TaskContract,
    ) -> list[tuple[Issue, TaskContract]]:
        """
        Processes ReviewResult findings. For every CRITICAL or HIGH finding,
        creates an Issue and generates a paired repair TaskContract.
        Returns a list of (Issue, repair_TaskContract) pairs.
        """
        pairs: list[tuple[Issue, TaskContract]] = []

        actionable_findings = [
            f for f in review_result.findings
            if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)
        ]

        for i, finding in enumerate(actionable_findings, 1):
            severity = (
                IssueSeverity.CRITICAL
                if finding.severity == FindingSeverity.CRITICAL
                else IssueSeverity.HIGH
            )
            category = finding.title or f"Issue in {finding.file}"
            title = f"[{finding.severity.value}] {category}: {finding.issue[:80]}"
            body = f"""## Problem
{finding.issue}

## Suggestion
{finding.suggestion}

## Severity
{finding.severity.value}

## Evidence
File: {finding.file or 'unspecified'} (Line: {finding.line or 'unspecified'})

## Acceptance Criteria
- [ ] Finding is resolved: {finding.suggestion}
- [ ] All quality gates pass without regression
- [ ] No unauthorized files modified

## Source
Task: {task.id} | Reviewer: Claude
"""
            labels = [
                "p2p:bug",
                f"priority:{severity.value.lower()}",
                "agent:gemini",
                f"task:{task.id}",
            ]
            issue = self.issue_provider.create_issue(
                title=title,
                body=body,
                severity=severity,
                labels=labels,
                task_id=task.id,
            )

            # Generate Repair TaskContract (docs/07 §7)
            fix_id = f"FIX-{i:03d}"

            repair_task = TaskContract(
                id=fix_id,
                title=f"Resolve issue {issue.id}: {category[:40]}",
                capabilities=[Capability.BACKEND],
                risk=RiskLevel.HIGH if finding.severity == FindingSeverity.CRITICAL else task.risk,
                depends_on=[task.id],
                intent=f"Fix review finding reported in {issue.id}: {finding.issue}. Suggestion: {finding.suggestion}. Strictly apply fix without refactoring.",
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-1",
                        statement=f"Finding from {issue.id} is resolved and verified.",
                        verified_by=VerifiedBy.GATE,
                        gate_ref="pytest",
                    )
                ],
                inputs=task.inputs + [f".p2p/issues/{issue.id}.json"],
                allowed_paths=task.allowed_paths,
                forbidden_paths=task.forbidden_paths,
                gates=task.gates,
                estimated_size=EstimatedSize.S,
                max_attempts=3,
                human_approval=False,
                result_path=task.result_path,
                acr_path=f".p2p/acr/ACR-{fix_id}.md",
                notes=f"Linked to {issue.id}",
            )
            pairs.append((issue, repair_task))

        return pairs

    def close_issue_on_merge(
        self,
        task: TaskContract,
        pr_number: int,
        issue_id: Optional[str] = None,
    ) -> bool:
        """Closes the issue and marks the PR merged when the repair task is merged."""
        self.pr_provider.merge_pr(pr_number)

        target_issue_id = issue_id
        if not target_issue_id and task.notes and "Linked to" in task.notes:
            # Extract issue ID from task notes e.g. "Linked to ISSUE-001"
            parts = task.notes.split("Linked to")
            if len(parts) > 1:
                target_issue_id = parts[1].strip()

        if target_issue_id:
            comment = f"Resolved and verified by repair task {task.id} merged in PR #{pr_number}."
            return self.issue_provider.close_issue(target_issue_id, comment=comment)
        return False
