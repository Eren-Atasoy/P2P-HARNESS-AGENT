# Product

<!-- impeccable:product-schema 1 -->

> Language: agent-facing files in this repo are English (`AGENTS.md`,
> `CLAUDE.md`, `GEMINI.md`, `prompts/`); human-facing `docs/**` is Turkish
> until the open-source release. PRODUCT.md follows the agent-facing convention.
>
> Scope: this record targets **Prompt2Product's own web UI** (Phase 10+,
> `docs/08-roadmap.md`) and the design system that governs it plus the
> reference frontend blueprint (`docs/12-design-system.md`). No frontend exists
> today; the product ships as a CLI. Product truth here is drawn from the
> reviewed specification, not invented.

## Platform

web

## Stack

**delegated** — the user left this choice to the design work, then pinned it
further with a brief naming React Flow-style graph visualisation and
Radix/shadcn primitives. The brief wins; recorded so later work knows the
decision was offered and on what basis it landed.

Chosen: **Vite + React + TypeScript, compiled to static assets, served by the
Python CLI over a local HTTP server, with Server-Sent Events for live run
state.**

Why:

- The UI ships *inside a Python package*. It must build to plain static files
  Python can serve with **no Node at runtime**. Contributors who only touch the
  CLI never need a JS toolchain; prebuilt assets ship in the package.
- The screen is a live view of an autonomous run, not a document. Static-site
  tooling is right for the eventual marketing surface and wrong here.
- State already lives in an append-only event log (`ADR-002`). Tailing
  `.p2p/events.jsonl` and pushing SSE is the natural transport: no polling, no
  client store to keep in sync with the server's truth.
- React over a lighter framework is a **deliberate trade**. On bundle size alone
  Svelte would win for a local dashboard. It loses on the thing that matters
  more: the dashboard and the generated blueprint (`docs/12 §2`) then share one
  token layer, one primitive set, and one accessibility baseline. Two design
  systems for one product is the expensive outcome.

Accepted cost: contributors touching the UI need a Node build step, and the
dashboard carries a framework runtime it could technically avoid.

## Users

**Primary:** the developer operating a Prompt2Product run on their own machine.
They started an autonomous build (`p2p run`), stepped away, and came back —
often the next morning — to answer what the system could not decide alone.

Their situation shapes everything: they were **absent while decisions were made
on their behalf**. Their first question is never "what is this?" but
*"what happened, and what did it decide without me?"*

**Secondary:** the same person mid-run, deciding whether to intervene.

Confirmed audience for the product overall (`docs/00 §7`): a solo developer who
reads code and wants to own the output — someone who may delete Prompt2Product
tomorrow and keep the repository as an ordinary project.

## Product Purpose

Prompt2Product turns a natural-language product request into a working,
automatically verified software product by autonomously coordinating whatever
AI runtimes the user has access to.

The web UI exists to make an autonomous run **legible and answerable**: what was
built, what was verified, what is blocked, what waits on the human, and —
critically — which decisions were made automatically on their behalf.

Success for this surface: a developer returning to a finished or stalled run
understands its state and can act, without reading a log file.

## Positioning

The differentiator is **verification, not generation** (`docs/00 §3`). A task is
not complete because a model says so; it is complete when a quality gate's exit
code says so (`ADR-004`). Competitors optimise for producing code; this product
optimises for proving the code does what was asked.

Two structural commitments a neighbouring product could not truthfully copy
without rebuilding:

- **Autonomy never reduces transparency.** Every gate passed automatically is
  recorded as `decided_by=default` and reported separately (`ADR-010`). The
  system runs unattended but never hides what it decided alone.
- **The output is disownable.** Deleting `.p2p/` leaves a normal repository that
  works. The user is never locked in by the tool that built their product.

## Operating Context

- Runs locally; the user's code never has to leave their machine.
- Started from a terminal. The UI is a local dashboard the CLI serves — not a
  hosted service, no login, no account.
- Runs are **long**: hours, often overnight. The UI is frequently opened after
  the fact rather than watched continuously.
- The user brings their own AI access (BYOC): subscription CLIs, API keys, local
  models, or a gateway — all represented uniformly as `Connection` (`docs/04 §2`).
- Quota exhaustion mid-run is expected, not exceptional (`docs/03 §3.4`).
- The ambient scene is a developer's own machine, frequently at night or first
  thing in the morning, next to a terminal. This is why the theme decision in
  `docs/12` is dark-first — the use scene, not the category.

## Capabilities and Constraints

Confirmed from the specification:

- Runs are described by a dependency-aware **task graph**; independent tasks run
  in parallel in isolated git worktrees (`ADR-006`), scheduled in waves whose
  `allowed_paths` are disjoint (`docs/03 §2`).
- Task states: `PENDING`, `READY`, `IMPLEMENTING`, `VERIFYING`, `REVIEWING`,
  `BLOCKED`, `PAUSED`, `ESCALATED`, `UNROUTABLE`, `DONE` (`docs/03 §1`).
- Three autonomy levels: `supervised`, `guarded` (default), `full` (`ADR-010`).
  `high` risk tasks are never auto-approved at any level.
- Four project gates: ambiguity (G1), architecture (G2), scope (G3), release (G4).
- The event log is append-only and is the source of truth; displayed state is
  derived from it (`ADR-002`). **The UI reads; it never writes orchestration
  state** (`ADR-003`).
- Partial success is a legitimate outcome. A run ending with some tasks done,
  some escalated and some paused is normal and must display as such, not as
  failure (`docs/03 §7.3`).
- No provider or model name may appear in core code (`ADR-009`). The UI must not
  hardcode them either — connections are user data, not design constants.

Explicitly undecided:

- Product name and domain (`docs/10 D5`) — see Brand Commitments.
- Default autonomy level (`docs/10 D9`); risk-rule ownership (`docs/10 D12`).
- Whether the UI is read-only or may also answer gates and steer escalated tasks.
  `p2p steer` exists as a CLI verb (`docs/03 §3.5`); whether the UI invokes it is
  not decided. `docs/12 §2.A` specifies the approval surface on the assumption it
  will, and flags the dependency.

## Brand Commitments

- **The name is a working title, not a decision.** `Prompt2Product` / `P2P` is a
  code name; the final name must be settled before the open-source release
  (`docs/10 D5`). No logo or wordmark should be built on it yet, and no visual
  work may treat it as permanent.
- **Voice**, established across the specification and binding: direct,
  evidence-led, unembellished. States what is verified and what is not. Never
  claims a result it has not measured — the same standard the product applies to
  generated code. UI copy inherits this: labels name actions, errors name the
  problem and the recovery.
- **Pinned visual direction** (user brief, 2026-09-10): modern developer-tool
  aesthetic in the Linear / Vercel / Supabase / Raycast line; dark-first with a
  high-contrast light mode; Geist or Inter with a monospace pairing. Recorded as
  binding, expanded in `docs/12-design-system.md`.
- No existing logo, wordmark, or colour commitment beyond the above.

## Evidence on Hand

Real and referenceable:

- A complete reviewed specification: 14 documents, 10 ADRs, 10 master prompts,
  including an architecture review recording 16 findings and their resolutions
  (`docs/architecture-review.md`).
- A feasibility harness with real run artifacts (`experiments/faz0/`).
- Git history showing decisions and their revisions.

**Absences that must not be filled with invention:**

- **The product does not run yet.** No core implementation exists. Phase 0
  Test 3 — the autonomous loop — has **not passed**; its first run failed on an
  unauthenticated runtime (`docs/11 V1`).
- No users, adoption, testimonials, case studies, benchmarks, performance
  numbers, or generated-product examples.
- No pricing, licensing, deployment, or availability claims. The license is an
  open decision (`docs/10 D4`).
- Screenshots of the UI cannot come from a running product. Any interface imagery
  is by definition a design artifact and must never be presented as a product
  photograph or a real run.

## Product Principles

1. **Verified beats generated.** Nothing is reported done that a gate has not
   proven. This applies to the product's own claims as strictly as to the code
   it writes.
2. **Autonomy without opacity.** The more the system decides alone, the more
   visible those decisions must be. A decision made in the user's absence is
   surfaced, never buried.
3. **The user owns the output.** No lock-in, no proprietary artifact in their
   source tree, no dependency on this tool to keep working.
4. **Capability, not vendor.** Roles bind to capabilities, never to a named model
   or provider. The user's own AI access is the substrate.
5. **Partial truth over false completion.** A stalled run reported honestly is
   more useful than a green checkmark that is wrong.

## Accessibility & Inclusion

No product-specific standard was previously established. `docs/12 §4` now sets
one (`G_UI_3`: axe-core clean, Lighthouse a11y ≥ 90). Two facts constrain it:

- The surface is a long-running monitoring view returned to after absence. State
  must be legible **without relying on colour alone** — every status carries a
  shape, label or position in addition to hue — and must survive a screen reader.
- Documentation is currently Turkish and moves to English at the open-source
  release (`docs/08` Phase 9). UI copy should be written with that transition in
  mind rather than assuming a single language.
