Implement the task below. You are the implementer; the architecture and the
tests are already decided.

TASK CONTRACT:
{TASK_JSON}

Working directory: {WORKSPACE}

Rules — these are absolute:
- Write ONLY inside: {ALLOWED}
- NEVER modify: {FORBIDDEN}. The tests are the specification. If a test looks
  wrong, implement to satisfy it anyway and say so in `assumptions`.
- Do not run git. Do not install packages. Do not deploy.
- You MAY run the test suite: `python -m pytest tests/ -q`. Nothing else.

Steps:
1. Read `tests/test_duration.py`. It is the complete specification.
2. Create `src/duration.py` (and `src/__init__.py` if missing).
3. Run the tests. Iterate until they pass.
4. Write your result to `{RESULT}` as exactly this JSON object:

```json
{
  "task_id": "DUR-001",
  "outcome": "completed | blocked | failed",
  "summary": "max 3 lines",
  "files_changed": ["src/duration.py"],
  "criteria_addressed": ["AC-1"],
  "assumptions": [],
  "tests_run": true,
  "tests_passed": true
}
```

`files_changed` is checked against git. List exactly what you changed.
Report honestly: if the tests do not pass, say so rather than claiming success.
