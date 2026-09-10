Review this implementation as the architect accountable for the result.
The test suite already passed — you are not re-checking that. You are checking
whether the right thing was built.

TASK CONTRACT:
{TASK_JSON}

IMPLEMENTATION (`src/duration.py`):
```python
{IMPL}
```

SPECIFICATION (`tests/test_duration.py`):
```python
{TESTS}
```

GATE RESULT: {GATE}

Check, in order:
1. Does every acceptance criterion have a test that would fail if the behaviour
   were removed?
2. Correctness at the edges: inputs the tests do not cover but the contract
   implies. Name a concrete input that produces a wrong result, or say there
   is none.
3. Error handling: does invalid input fail explicitly rather than silently?
4. Scope: was anything changed that the contract did not ask for?
5. Quality: naming, nesting, magic values, dead code.

Severity calibration matters — the loop acts on it mechanically:
- CRITICAL: wrong result for a valid input, or a violated contract rule
- HIGH: unhandled edge case, silent failure, missing validation
- MEDIUM: maintainability
- LOW: style

Write EXACTLY this JSON to `{RESULT}` and nothing else:

```json
{
  "verdict": "APPROVED | CHANGES_REQUESTED | REJECTED",
  "findings": [
    {"severity":"HIGH","file":"src/duration.py","line":12,
     "issue":"...","suggestion":"..."}
  ],
  "summary": "one paragraph"
}
```

Approving work that does not meet its criteria is the most expensive mistake
available to you. Reporting a finding you cannot anchor to a line is noise —
put it in the summary instead.
