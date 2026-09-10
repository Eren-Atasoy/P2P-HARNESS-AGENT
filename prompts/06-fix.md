# Master Prompt 06 — Fix Round

**Runtime:** gemini · **Writes:** code inside `allowed_paths`, plus `result_path`

---

Your previous attempt did not pass. Address **only** what is listed below.

```
<task_contract>{{ TASK_CONTRACT_JSON }}</task_contract>
<your_previous_summary>{{ PREVIOUS_SUMMARY }}</your_previous_summary>
<failures>{{ GATE_FAILURES }}</failures>
<review_findings>{{ FINDINGS }}</review_findings>
```

Attempt {{ ATTEMPT }} of {{ MAX_ATTEMPTS }}.

## Rules for this round — stricter than implementation

1. Fix the listed items. Nothing else.
2. **No refactoring.** No renaming, reorganizing, optimizing, or cleanup. The
   surrounding code is already verified; every extra change risks breaking
   something that currently works.
3. Never weaken, skip, delete, or special-case a test to make it pass. If a
   test seems wrong, fix the code and object in `assumptions[]`.
4. If a finding appears incorrect, implement it anyway and record your objection
   in `assumptions[]`. The reviewer sees it next round.
5. If two items conflict, implement neither. Report the conflict and set
   `outcome` to `blocked`.
6. For each failure, state the **root cause** in your summary, not the symptom.
   Fixing a symptom reproduces the same failure next round.

## Before reporting

- The listed failures now pass
- Everything that passed before still passes
- Nothing outside `allowed_paths` changed
- `files_changed` matches git exactly

If you cannot fix an item without violating a rule above, report blocked rather
than working around it. Escalation is cheap; a quietly broken invariant is not.
