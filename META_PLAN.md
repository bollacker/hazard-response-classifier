# Meta-Plan: How to Iterate on This Project's Design with Claude

**Purpose.** Previous attempts to productionize a classifier system via repeated
"analyze the plan / find problems / fix them" cycles went in circles: the list of
critical problems never shrank, because fixes compounded against each other in
non-obvious ways and each new session re-derived (and sometimes re-litigated)
ground already covered. This document is the process contract for avoiding that.
Point Claude at this file at the start of any planning or review session in this
repo.

Every session that touches the design should follow one of the four mechanisms
below. Don't run an open-ended "review everything and fix what you find" pass —
that is the pattern that failed.

---

## 1. Decision Ledger (`DECISIONS.md`)

`DECISIONS.md` in this repo is the single source of truth for what has been
decided, not chat history and not the plan doc's prose. Every time a
recommendation is curated and accepted, it becomes a numbered, dated entry:

```
## D-<n>: <short title>
Date: YYYY-MM-DD
Status: locked | open | superseded-by D-<m>
Decision: <what was decided>
Rationale: <why, including what alternative was rejected and why>
Touches: <files/subsystems affected>
```

Rules for Claude:
- Treat every `locked` entry as a hard constraint. Do not propose changes that
  contradict one unless you flag it explicitly under Open Questions (see §3)
  with a reasoned argument for reopening it — never silently override it.
- When a session accepts a new fix or decision, append it to `DECISIONS.md`
  yourself as part of that session's output, so the ledger stays current.
- If two locked decisions conflict with each other (this is exactly the kind
  of non-obvious interference that caused the original looping), stop and
  raise it as an Open Question rather than picking one silently.

## 2. Scoped, Separated Passes

Never combine "find problems" and "propose fixes" in a single unscoped pass —
that's what let unrelated recommendations pile up and interact unpredictably.
Use three distinct pass types, each with a narrow, explicit scope (a
subsystem, a boundary, a single decision) rather than "the whole plan":

- **Critique pass** — input is the current plan + `DECISIONS.md`, scoped to
  one named subsystem or concern. Output is a list of issues only, each
  tagged with severity (blocks-correctness / quality / nice-to-have). No
  fixes proposed in this pass.
  
  **Critique output format:** each critique is written to
  `critiques/YYYY-MM-DD-<descriptive-scope>.md` (e.g.
  `critiques/2026-07-23-deliverable-1.md`). Structure:
  - Header: title, date, mechanism, scope, and a ledger check against
    `DECISIONS.md` (confirm no locked decision already addresses this).
  - Organized by severity (blocks-correctness first, then quality,
    nice-to-have).
  - Numbered findings within each severity band (C-1, C-2, etc. for
    correctness; Q-1, Q-2 for quality; etc.), each stating the issue plainly
    without proposing a fix.
  - Science/math/engineering problems only — no design opinions or style
    critique unless they affect behavior.
  - Each critique file is self-contained; a reader should understand the scope
    and findings without referring back to chat history.
  - **User Responses** (added after user replies) — answers to open questions
    posed in the critique. Responses that constrain future work are moved to
    `DECISIONS.md` entries; clarifications that don't require a locked decision
    go here inline with the question, so the critique is a complete record.

- **Fix-proposal pass** — input is exactly one issue from a critique pass
  (or from you) plus the full `DECISIONS.md`. Output is a proposed fix and,
  critically, an explicit check of whether it conflicts with any locked
  decision. If it does, that conflict is surfaced, not resolved unilaterally.
- **Integration pass** — after you curate and accept a fix, this pass checks
  the accepted fix against the *entire* current `DECISIONS.md` for
  second-order conflicts before it's appended as a new locked entry.

Run these as separate prompts/sessions, not folded together. A session that
mixes critique and fix-generation across a broad scope is the failure mode
this whole document exists to prevent.

## 3. Uncertainty Protocol

Every critique, fix-proposal, or integration pass must end with an explicit
**Open Questions** section (present even if empty — say "none"). An item goes
there instead of the main output whenever:
- Confidence in the recommendation is below ~90%, or
- It conflicts with an existing locked decision, or
- It depends on a tradeoff only you can make (cost, timeline, risk appetite,
  domain judgment about the classifier's behavior).

Claude should stop at that point rather than resolving the question itself.
Do not let a "best guess" quietly become a plan-doc edit.

## 4. Convergence Through Implementation, Not More Paper Review

Paper-plan review cycles have no ground truth to falsify against — two
critics can disagree forever with no way to tell who's right. As soon as the
core architecture has a couple of locked decisions in place, shift from
"review the plan" to **small vertical slices of real code with tests**. A
failing test is a forcing function that a review pass isn't: it proves
whether two decisions actually conflict instead of leaving it as an opinion.

Guideline: if a critique pass raises a concern that implementation-and-test
would resolve faster than more analysis, say so explicitly and propose the
smallest slice that would settle it, rather than continuing to reason about
it in the abstract.

## 5. State Tracking (`STATUS.md`)

With four mechanisms and many small passes, it's easy to lose track of where
things stand across sessions. `STATUS.md` is a thin queue file for that —
not an autonomous orchestrator. It never decides anything or advances itself;
it only records what's queued, what a session did, and what's waiting on you.
A session reads it, does exactly one queued item, updates it, and stops. It
does **not** chain into the next item on its own — that would just move the
"decisions get made without you noticing" failure mode one layer up.

Structure of `STATUS.md`:

- **Current Phase** — the mechanism and scope currently in flight, if any.
- **Queue** — ordered list of pending items (a critique pass to run, a fix
  to propose, an integration check, an implementation slice), each tagged
  with its mechanism type and where it came from (an Open Question, a prior
  critique finding, etc.).
- **Awaiting User** — items a session stopped on because they need your
  judgment (per §3's uncertainty protocol) before anything else touching
  that area should proceed. This is the explicit "judge these critiques" /
  "make this decision" / "accept this recommendation" list.
- **Recently Completed** — a short trailing log of resolved items, each
  pointing at the `DECISIONS.md` entry it produced, if any.

Rules for Claude:
- Always read `STATUS.md` before doing anything else.
- If **Awaiting User** is non-empty, do not start new queue work in that
  scope — surface those items to the user and stop.
- Otherwise, take only the top **Queue** item, do only that item's declared
  mechanism and scope, then update `STATUS.md` (move the item to Awaiting
  User or Recently Completed, and leave the rest of the queue untouched)
  before ending the session.
- Never pop more than one queue item per session, and never silently
  reorder or drop queue items — if the queue looks wrong, say so under Open
  Questions instead of fixing it yourself.

## 6. Model Selection

Because each pass is narrowly scoped by design, most steps don't need the
top-tier model — but critique and integration passes are exactly where
subtle cross-decision interference hides (the original failure mode this
whole process exists to prevent), so spend the strongest reasoning there.

| Mechanism | Model | Why |
|---|---|---|
| Critique pass | Opus | Non-obvious problems and cross-decision interference live here. |
| Integration check | Opus | Checking a fix against the *whole* ledger for second-order conflicts is the other place interference hides. |
| Fix-proposal | Sonnet 5 | Scope is one issue against an already-locked ledger — constrained generative work. |
| Implementation-slice | Sonnet 5 | Standard coding + test writing for a small, scoped slice. |
| STATUS.md/DECISIONS.md bookkeeping | Haiku 4.5 | Pure mechanical file updates — no judgment required. |

---

## Session Checklist (paste this into a new session)

1. Read `META_PLAN.md` (this file), `STATUS.md`, `DECISIONS.md`, and the
   current plan document (e.g. `PLAN.md`) in full first.
2. If `STATUS.md` has items under **Awaiting User**, stop and present them —
   do not start new work in that scope.
3. Otherwise, take the top item in `STATUS.md`'s **Queue** and state which
   mechanism it is (critique / fix-proposal / integration /
   implementation-slice) and its scope.
4. Do the work within that scope only.
5. End with an **Open Questions** section per §3.
6. Update `STATUS.md`: move the item just worked to Awaiting User or
   Recently Completed. If anything was accepted as a new decision, append it
   to `DECISIONS.md` too.
