# Master Prompt 08 — Implement a P2P Phase

**Runtime:** gemini · **Target:** Prompt2Product itself, not a generated product

---

You are implementing a phase of Prompt2Product. Unlike a generated product,
this codebase already has a complete, reviewed specification. Your job is to
realise it — not to redesign it.

## Read first, in this order

1. `AGENTS.md` — engineering rules that bind you
2. `GEMINI.md` — your role and hard boundaries
3. `docs/01-architecture.md` §3 — module boundaries and dependency direction
4. `docs/02-data-model.md` — **every field name here is binding**
5. The phase you are implementing in `docs/08-roadmap.md`
6. Any ADR referenced by that phase

Do not read the whole `docs/` tree. Read what the phase needs. If you cannot
tell what it needs, that is a planning defect — report it, do not guess.

## Binding constraints

These are not style preferences. Violating one is a defect regardless of
whether the tests pass.

| Rule | Source |
|---|---|
| Only the orchestrator writes orchestration state | ADR-003 |
| Quality decisions come from exit codes, never from a model | ADR-004 |
| No provider or model name anywhere in core code | ADR-009 |
| `high` risk is never auto-approved at any autonomy level | ADR-010 |
| Field names match `docs/02` exactly — no renaming, no "improvements" | `docs/02` |
| No `os.getcwd()`, no absolute local paths; every path comes from `Workspace` | `docs/01 §9` |
| No microservices, queues, Kubernetes, CQRS, event sourcing | ADR-001 |

## Definition of done for a phase

The roadmap gives each phase an explicit exit criterion. That criterion is the
specification — not your judgement that the code "looks complete".

Additionally:

- [ ] Every public type in `docs/02` that the phase covers exists with the
      documented fields, validated at the boundary
- [ ] Tests do not call a real model. `MockRuntime` exists from Phase 1 for
      exactly this reason; a test that spends quota is a broken test
- [ ] The phase's exit criterion is demonstrated by a test or a command whose
      output you can paste
- [ ] `docs/` is unchanged. If the implementation revealed a specification
      problem, that is an ACR, not an edit

## Order of work within a phase

1. Types first (`docs/02`), with boundary validation
2. The narrowest slice that makes the exit criterion demonstrable
3. Tests against the exit criterion, not against your implementation
4. Everything else the phase lists

Resist building infrastructure the phase does not name. Phase N+1 exists.

## When the specification is wrong

You will find gaps — a specification this size always has them. Two kinds:

**Small and local** (a field type is ambiguous, an error case is unstated):
pick the reading most consistent with the surrounding design, implement it, and
record it in `assumptions[]`. Do not stop for these.

**Structural** (two documents contradict; the design cannot express something
the exit criterion requires): stop and write an ACR
(`prompts/acr-template.md`). Do not route around it.

The difference is whether a future reader would call your choice a detail or
a decision.

## Known open items

Before starting, check `docs/11-verification-backlog.md`. If your phase rests
on an item that is not `DOĞRULANDI`, say so and stop. Building on an unverified
assumption is the one failure mode this project has explicitly ruled out.

Also check `docs/10-open-decisions.md` for decisions marked as blocking your
phase. An unanswered blocking decision is a stop condition, not a guess.
