Your previous attempt did not pass. Address ONLY what is listed below.

TASK CONTRACT:
{TASK_JSON}

FAILURES:
{FAILURES}

Working directory: {WORKSPACE}
Attempt {ATTEMPT} of {MAX}.

Rules for this round — stricter than implementation:
- Fix the listed items. Nothing else.
- NO refactoring, renaming, reorganising, or cleanup. The surrounding code is
  already verified; every extra change risks breaking something that works.
- NEVER weaken, skip, or delete a test to make it pass. `tests/` is forbidden.
- State the ROOT CAUSE in your summary, not the symptom.
- You may run `python -m pytest tests/ -q`. Nothing else.

Write your result to `{RESULT}` in the same JSON shape as before.
If you cannot fix an item without violating a rule above, set
`"outcome": "blocked"` and explain. Escalation is cheap; a quietly broken
invariant is not.
