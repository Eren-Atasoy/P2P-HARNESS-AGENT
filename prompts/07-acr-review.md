# Master Prompt 07 — Evaluate an Architecture Change Request

**Runtime:** claude · **Writes:** ACR decision, updated architecture docs, new task contracts

---

An implementer has blocked on an architectural obstacle. Decide.

```
<acr>{{ ACR_CONTENT }}</acr>
<task_contract>{{ TASK_CONTRACT_JSON }}</task_contract>
```

## Evaluate

1. Is the observation **factually correct**? Verify against the code and the
   architecture documents. Implementers sometimes report a limitation that does
   not exist, or misread an existing mechanism.
2. If correct: is it a genuine architectural gap, or solvable within the current
   design by someone who understands it better?
3. If a genuine gap: what is the **smallest** change that closes it? Resist
   redesigning adjacent areas while you are here.
4. What else does that change affect? Which completed tasks become invalid?

## Decide

| Verdict | When | Then |
|---|---|---|
| `REJECTED` | Solvable as designed | Explain **how**, concretely; add to task notes; task returns to READY |
| `ACCEPTED` | Real gap | Update the architecture doc, write an ADR, create the new task(s), make the blocked task depend on them |
| `DEFERRED` | Real but not blocking | Approve a specific workaround, record the debt and the cost of deferring |

A `REJECTED` verdict must contain the actual solution. "This is achievable"
without showing how produces the identical ACR on the next attempt.

## Consequence check

If `ACCEPTED`, list every completed task whose assumptions this invalidates.
Those tasks must be reopened. Accepting an architecture change while leaving
earlier work built on the old assumption is how a codebase forks into two
incompatible designs.

## Output

The verdict, the reasoning, updated documents, and any new task contracts.
Keep the reasoning short enough that the implementer will actually read it.
