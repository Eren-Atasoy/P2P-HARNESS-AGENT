# Master Prompts

Each file is one stage of the pipeline. `{{ PLACEHOLDER }}` values are filled by
the orchestrator (or by you, by hand, during Phases 0-5).

| File | Runtime | Stage | Writes |
|---|---|---|---|
| `00-architecture-redteam.md` | claude | one-off | `docs/architecture-review.md` |
| `01-discovery.md` | claude | Discovery | product spec, open questions |
| `02-architecture.md` | claude | Architecture | architecture, data model, API contract |
| `03-task-planning.md` | claude | Planning | task contracts, task graph |
| `04-implement.md` | gemini | Implementation | code + result |
| `05-review.md` | claude | Review | review result |
| `06-fix.md` | gemini | Repair | code + result |
| `07-acr-review.md` | claude | Architecture change | verdict, docs, new tasks |
| `acr-template.md` | — | template | filled by the implementer |

## Rules for editing these

- Prompts are **versioned files**, never strings embedded in code. A prompt you
  cannot diff is a prompt you cannot improve.
- Durable rules belong in `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`, not here.
  Those load automatically on every run and cost nothing to repeat; a sentence
  added to a prompt is forgotten the next time someone writes a new one.
- When a prompt change fixes a recurring failure, note it in the commit message.
  That log becomes the empirical record of what actually works.
