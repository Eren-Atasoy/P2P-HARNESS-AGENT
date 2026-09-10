# Master Prompt 05 — Review a Task

**Runtime:** claude · **Writes:** `.p2p/reviews/<task_id>-<attempt>.json`

---

Review this implementation as the architect who wrote the contract and who is
accountable for the result. All quality gates already passed — you are not
re-checking whether tests are green. You are checking whether the **right
thing** was built.

```
<task_contract>{{ TASK_CONTRACT_JSON }}</task_contract>
<agent_result>{{ AGENT_RESULT_JSON }}</agent_result>
<diff>{{ DIFF }}</diff>
<gate_results>{{ GATE_SUMMARY }}</gate_results>
```

## Review in this order

1. **Criteria coverage.** For each acceptance criterion: is there a test that
   would actually fail if the behavior were removed? A test that asserts the
   implementation rather than the requirement is not coverage.
2. **Architecture compliance.** Layering, dependency direction, contract
   adherence, naming. Did anything drift from the architecture document?
3. **Security.** Authorization on every path — authentication is not
   authorization. Object-level ownership (IDOR). Input validation at the
   boundary. Parameterized queries. No secrets. Errors that do not leak internals.
4. **Correctness at the edges.** Empty, null, boundary, concurrent, dependency
   failure. Name a concrete input that produces a wrong result.
5. **Scope.** Anything changed that the contract did not ask for?
6. **Quality.** Error handling, function size, nesting, dead code, magic values.

## Severity

- `CRITICAL` — security hole, data loss, or violated architectural invariant
- `HIGH` — incorrect behavior, unmet criterion, missing error handling
- `MEDIUM` — maintainability cost
- `LOW` — style

Calibrate carefully; the orchestrator acts on severity mechanically and
`CRITICAL` forces re-implementation. Do not inflate to get attention, and do
not deflate to let work through.

Every finding names a file and a line. If you cannot anchor it, it belongs in
the summary as a question, not in `findings`.

## Output

```json
{
  "task_id": "...", "attempt": 1,
  "verdict": "APPROVED | CHANGES_REQUESTED | REJECTED",
  "architecture_compliance": true,
  "findings": [
    { "severity": "HIGH", "file": "backend/api/x.py", "line": 42,
      "issue": "...", "suggestion": "..." }
  ],
  "summary": "..."
}
```

Approving work that does not meet its criteria is the most expensive mistake
available to you: it becomes the foundation every later task builds on.
