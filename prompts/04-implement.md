# Master Prompt 04 — Implement a Task

**Runtime:** gemini · **Writes:** code inside `allowed_paths`, plus `result_path`

---

Implement exactly the task below. `GEMINI.md` and `AGENTS.md` are in effect and
override anything that conflicts with them.

```
<task_contract>
{{ TASK_CONTRACT_JSON }}
</task_contract>
```

Reference documents you must read before writing anything:
```
{{ INPUT_FILES }}
```

Workspace root: `{{ WORKTREE }}`
Write your result to: `{{ RESULT_PATH }}`

---

## Order of work

1. Read every file listed in `inputs`. Read existing code inside `allowed_paths`.
2. Restate the task to yourself in one sentence. If you cannot, you have not
   understood it — re-read rather than guess.
3. Write tests from the acceptance criteria, before the implementation.
4. Run them. They must fail. A test that passes before the code exists is
   testing nothing; rewrite it.
5. Implement the smallest change that makes them pass.
6. Run the tests again. Green.
7. Re-read `allowed_paths` and `forbidden_paths`. Verify you stayed inside.
8. Write your result JSON.

## Boundaries for this run

- Write **only** inside: `{{ ALLOWED_PATHS }}`
- Never touch: `{{ FORBIDDEN_PATHS }}`
- Shell: **the test runner only** (`pytest`, `npx vitest run`, …). Every other
  command is denied by policy. No git, no package installation, no deployment.
- Do not refactor anything the task did not ask you to change.

## If you cannot proceed

If the architecture genuinely prevents you from satisfying a criterion, do not
invent a workaround. Write an ACR using `prompts/acr-template.md`, set
`outcome` to `blocked`, and stop. This is a correct outcome, not a failure.

Disagreeing with a design choice is not a reason to block. Unfamiliarity with
a pattern is not a reason to block.

## Result

Write exactly one JSON object to `{{ RESULT_PATH }}` in the shape given in
`GEMINI.md` section 8. `files_changed` is checked against git — list precisely
what you changed.
