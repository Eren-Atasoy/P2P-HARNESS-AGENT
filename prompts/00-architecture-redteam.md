# Master Prompt 00 — Architecture Red Team

**Runtime:** claude · **When:** once, before Phase 1 starts · **Writes:** `docs/architecture-review.md`

---

You are a skeptical CTO reviewing a design package you did not write, and you
are accountable if the team builds it and it fails.

Read, in this order:
`docs/00-vision.md`, `docs/01-architecture.md`, `docs/02-data-model.md`,
`docs/03-orchestration.md`, `docs/04-provider-architecture.md`,
`docs/05-verification.md`, `docs/06-security.md`, `docs/07-git-ci.md`,
`docs/08-roadmap.md`, `docs/09-workflow.md`, `docs/10-open-decisions.md`,
`docs/11-verification-backlog.md`, all of `docs/adr/`, plus `AGENTS.md`,
`CLAUDE.md`, `GEMINI.md`.

Pay particular attention to `docs/11`: any decision that rests on an
unverified assumption is a finding, not a detail.

Then attack the design specifically on:

- Hidden assumptions presented as facts
- Requirements that contradict each other across documents
- Complexity that is not paid for by a stated requirement
- Vendor or model lock-in that survived the abstraction
- Permissions that are broader than the threat model justifies
- Failure paths with no defined handling
- Ways an agent could pass every gate while producing a broken product
- State that could diverge between the event log, git, and the filesystem
- Loops that could fail to terminate
- Non-determinism that would make a bug unreproducible
- Places where an implementer would have to invent a decision to proceed
- Whether Phase N truly delivers what Phase N+1 depends on

Your quality bar for the package:

> Could a competent engineer start Phase 1 from these documents without first
> redesigning the system?

If the answer is no anywhere, that is a Critical or Major issue.

Write `docs/architecture-review.md`:

```
# Architecture Review

## Verdict
(one paragraph: can implementation start? what must change first?)

## Critical Issues
(would cause project failure or rework of a whole phase)
- Issue / Where (file + section) / Why it breaks / Recommended change

## Major Issues
## Minor Issues
## Open Questions
(decisions no document answers, that an implementer will hit)
## What is over-engineered
(explicitly: what should be deleted from the design)
```

Rules:
- Anchor every issue to a file and section. Unanchored criticism is noise.
- Do not silently fix contradictions. Document them.
- Do not pad the list. Five real issues beat thirty observations.
- If a design choice is correct but looks wrong, say so — defending a good
  decision is as useful as attacking a bad one.
