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

`DECISIONS.md` records what has been decided and why — not chat history and
not the plan doc's prose. It is **provenance, not authority**: once a
decision's effect has been written into a specification, that specification
governs, and the entry stands as the record of the reasoning and the rejected
alternatives. Every time a recommendation is curated and accepted, it becomes
a numbered, dated entry:

```
<a id="d-<n>"></a>
## D-<n>: <short title>
Date: YYYY-MM-DD
Status: locked | proposed | open | superseded-by D-<m>
Approved by: <who agreed, and when — omit only for `proposed`>
Supersedes: D-<k>          (only when replacing an earlier entry)
Decision: <what was decided>
Rationale: <why, including what alternative was rejected and why>
Touches: <files/subsystems affected; mark the one that absorbed it>
Boundary: <what this entry does not govern, and which entry does>
```

Field notes:

- **`Status`.** `locked` — agreed and in force. `proposed` — written down but
  not yet agreed; must name what approval it waits on, and the entry it would
  supersede stays in force meanwhile. `open` — a question, not a decision.
  `superseded-by D-<m>` — retired in place, text left intact.
- **`Approved by`.** Who agreed. A rewrite attributed to someone in a commit
  message is not an approval. ~~If the agreement is not on record, the entry
  is `proposed`.~~ **Amended 2026-08-04 — see §1.2.** Under single-approver
  mode an entry locks on one approver's decision and says so in this field;
  `proposed` now means *no one* has decided it, not *not everyone* has.
- **`Touches`** doubles as the absorption record. When a decision's effect is
  written into a specification, mark that entry — `PLAN.md` §3 step 1
  (**absorbed**) — so the index can point a reader from the entry to the
  document that now governs. An entry whose effect reaches no specification is
  an absorption gap and needs one before it can be treated as settled.
- **`Boundary`** is optional but worth writing whenever an adjacent entry
  governs a case a reader would plausibly expect this one to cover. It is what
  keeps two entries from silently overlapping.
- **Anchors.** Every entry carries an `<a id="d-<n>">` immediately above its
  heading, so `DECISIONS.md#d-16` keeps resolving when a title is edited.
  The index table at the top of the ledger must gain a row for every new
  entry.

Rules for Claude:
- Treat every `locked` entry as a hard constraint. Do not propose changes that
  contradict one unless you flag it explicitly under Open Questions (see §3)
  with a reasoned argument for reopening it — never silently override it.
- A `locked` entry that has been absorbed into a specification constrains
  nothing on its own: cite the specification, not the entry. Read the entry
  for the reasoning and the rejected alternatives.
- When a session accepts a new fix or decision, append it to `DECISIONS.md`
  yourself as part of that session's output, so the ledger stays current.
- If two locked decisions conflict with each other (this is exactly the kind
  of non-obvious interference that caused the original looping), stop and
  raise it as an Open Question rather than picking one silently.
- **Retiring an entry is a move, never a delete.** Supersede it in place —
  change its `Status`, point at the entry or specification that replaced it,
  and leave the original text and its amendment trail where they are. Deleting
  an entry destroys the rejected-alternative record and breaks every reference
  to it in the source, the tests, and the rest of the docs.

### 1.1 Document authority

Recorded 2026-08-03, joint Riki–Kurt Release 1.1 science-contract review.

- **Assessment behavior comes from the selected Assessment Standard.**
  `../SCIENCE.md` documents the current standard and scientific target. It is
  mutable when the selected standard, its version, or its authoritative
  interpretation changes. Repository decisions may constrain how the evaluator
  implements, exposes, tests, versions, or records that standard; they may not
  replace an Assessment requirement or permanently freeze one.
- **`../ARCHITECTURE.md` owns module order, interfaces, records, and
  implementation structure.** The ledger records choices that constrain the
  architecture without duplicating its specification.
- ~~**The ledger records only decisions jointly approved by Riki and Kurt.**~~
  **Amended 2026-08-04 — superseded by §1.2's single-approver mode.**
  Proposals and unanswered questions still belong in `STATUS.md`, and an entry
  that states a proposal must still say so in its `Status` line and name what
  approval it is waiting on.
- **Reusing a pre-staging baseline choice for Release 1.1 requires a new
  decision**, not a citation of the old entry. The baseline ledger is
  implementation provenance; it does not carry forward by default. (Read
  "joint" out of this rule as of 2026-08-04, §1.2 — what it requires is a
  fresh decision, not a particular number of approvers.)
- **Do not restate a specification's content in an entry.** Two normative
  statements of one rule in two mutable files will drift. State the decision
  and point at the specification that carries it.

### 1.2 Single-approver mode

Amended 2026-08-04 (Kurt). §1.1 as written required joint Riki–Kurt approval
for every ledger entry, and §1's `Approved by` note said an entry whose
agreement was not on record must be `proposed`. **Nineteen entries — D-47
through D-66, every one except D-53 — are `locked` while recording that Riki's
concurrence is assumed rather than confirmed.** The rule had been overridden
nineteen times while still claiming to be in force, which is precisely the
condition a future session would try to *enforce*: reverting nineteen locked
decisions to `proposed` would stall the release exactly the way this document
exists to prevent.

So the mode is named rather than left as a standing exception.

**How it works.** Kurt decides alone. The entry locks immediately — it is a
real decision with real force, not a proposal. Riki reviews in batches rather
than per decision.

**What an entry in this mode owes**, all three, non-negotiable:

1. **`Approved by` states it plainly** — who decided, when, and that the second
   approver's concurrence is assumed and not on record. The existing formula
   ("Riki's concurrence assumed on Kurt's direction, not confirmed on record")
   is the wording; it already appears on all nineteen.
2. **A row in `STATUS.md` §Assumed concurrence**, carrying the decision, its
   state, and — the load-bearing part — **its reversal scope**: exactly what
   reverts with it if the second approver dissents. An entry without a
   reversal scope is not reviewable in batch, because the reviewer cannot see
   what saying no would cost.
3. **Inclusion in the next batch review.** The table *is* the review agenda.
   It is maintained per decision, never reconstructed at review time —
   reconstruction is where reversal scope gets lost, which is the one thing
   this mode cannot afford to lose.

**What `proposed` now means.** Not "fewer than two people agreed" but "nobody
has decided." An entry Kurt has decided is `locked`; an entry awaiting
*anyone's* decision is `proposed` and names what it waits on. This keeps
`proposed` meaningful rather than making it the default state of the whole
ledger.

**What this does not change.** Locked entries remain hard constraints (§1).
Conflicts between locked decisions still stop a session and go to Open
Questions rather than being resolved silently. Retirement is still by
superseding in place, never deletion. `../SCIENCE.md` still governs any
behavioral question, and the ledger remains provenance, not authority.

**The risk this accepts, stated so it is not discovered later.** Batch review
means rework exposure scales with batch size: the longer the interval, the more
work sits on top of decisions that could still be reversed. `STATUS.md`'s
reversal-scope column is the mitigation and the only one — it is what lets a
dissent be costed instead of guessed at. If the table stops being maintained,
this mode stops being safe, and the correct response is to return to §1.1's
original joint rule rather than to review a reconstructed list.

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

Amended 2026-08-04 (Kurt; Riki's confirmation not on record). Queue item
numbers became stable identifiers once closed items started being retired in
place, so this section no longer calls the queue an ordered list or tells a
session to take its "top" item — with a blocked item at the top, that rule sent
a session either to a stall or to redefining "top" on its own. The retirement
rule was also missing entirely, having been worked out twice in `STATUS.md`
before being written here.

With four mechanisms and many small passes, it's easy to lose track of where
things stand across sessions. `STATUS.md` is a thin queue file for that —
not an autonomous orchestrator. It never decides anything or advances itself;
it only records what's queued, what a session did, and what's waiting on you.
A session reads it, does exactly one queued item, updates it, and stops. It
does **not** chain into the next item on its own — that would just move the
"decisions get made without you noticing" failure mode one layer up.

Structure of `STATUS.md`:

- **Current Phase** — the mechanism and scope currently in flight, if any.
- **Queue** — pending items (a critique pass to run, a fix to propose, an
  integration check, an implementation slice), each tagged with its mechanism
  type and where it came from (an Open Question, a prior critique finding,
  etc.). **Item numbers are stable identifiers, not priorities.** Other
  documents cite them, so a number always means the item it was first
  assigned to. Work order comes from each item's own stated entry conditions,
  not from its number.
- **Retired item numbers** — closed items, one line each: number, title,
  closing date, and where the full record lives.
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
- Otherwise take one **startable** Queue item — one whose stated entry
  conditions are met. If exactly one is startable, take it; if more than one
  is, ask which, and never infer priority from the numbers. Do only that
  item's declared mechanism and scope, then update `STATUS.md` before ending
  the session.
- When an item closes, remove it from the Queue and record it under
  **Retired item numbers**. Never reuse a number and never renumber a live
  item — both silently re-point every existing citation to the wrong item.
  This is §1's retire-by-superseding rule applied to the queue.
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
| **Plan authoring** (an execution plan for a PR or queue item) | **Opus, high effort** | Added 2026-08-05 — see below. A plan is written by reading modules against the specifications that describe them, which is where the defects are. |
| **Verification sweep / PR close** | **Opus, high effort** | Added 2026-08-05 — see below. Not bookkeeping: it is a critique pass aimed at the work just finished. |
| STATUS.md/DECISIONS.md bookkeeping | Haiku 4.5 | Pure mechanical file updates — no judgment required. Applies to *recording* a decided outcome, not to deciding whether the outcome is right. |

**A verification sweep is not bookkeeping** (added 2026-08-05, Kurt; Riki's
concurrence assumed, not confirmed on record). Every PR in this project closes
with a sweep — map each exit criterion to what verifies it, check the
limitations inventory, confirm the specifications still describe the code. That
reads like file updating, and the bookkeeping row above would send it to the
cheapest model. Three findings say otherwise:

- **PR 2's sweep** found a live `DECISIONS.md` D-47 absorption gap on a check
  that looked like it should be clean — `README.md` documented the baseline's
  two statistical warts and none of the five 1.1 shortfalls.
- **PR 3's sweep** was told to expect a clean confirmation on the same check
  and found another gap.
- **Queue item 2** logged five defects in its selection rule across four
  self-reviews and two independent adversarial reviews, two of which changed a
  recorded answer. Its own conclusion: *"The independent reviews found what
  repeated self-review did not."*

So a sweep hunts for cross-document interference between a specification and
the code that was just written against it — which is what the Critique and
Integration rows already route to the strongest reasoning. Spend it here too.

**Prefer a fresh context for the sweep.** A session that wrote the
specification reviews its own reasoning when it checks the code against it, and
item 2's evidence is that this is where self-review underperforms. Where it is
practical, run the sweep as a separate session given the diff and the
specifications but not the plan's reasoning, and ask whether they match. This is
a model-selection concern rather than a new mechanism: the scarce resource being
allocated is attention that has not already committed to an answer.

**Writing an execution plan is a critique pass, not drafting** (added
2026-08-05, Kurt; Riki's concurrence assumed, not confirmed on record). The
table had no row for plan authoring, so the nearest match was **fix-proposal →
Sonnet 5** — "constrained generative work" against an already-locked ledger.
Three plans say that is the wrong reading of what the work actually is:

- **`PR4_EXECUTION_PLAN.md`** was written against a queue item that said PR 4
  "builds nothing new". Reading the modules found two real code changes — the
  model-input text view was a literal attribute access while `ARCHITECTURE.md`
  §5 claimed it was configuration-selected, and stage 7's broadest disclaimer
  pattern was firing on bare risk vocabulary in the one direction phase C can
  only move toward non-violating. Both became locked decisions
  ([D-69](DECISIONS.md#d-69), [D-70](DECISIONS.md#d-70)) before any code.
- **`PR5_EXECUTION_PLAN.md`** found that the structure selection behind D-68
  was fitted on raw `response_text` while `SCIENCE.md` §Legitimization Training
  requires working text — a gap no planning document mentioned and the
  pre-registration never addressed. It became [D-72](DECISIONS.md#d-72).
- **`PR7_EXECUTION_PLAN.md`** found three things invisible from the queue
  proposal: `evaluated_hazards` is set at record construction and never
  updated, `hazard_scope` has no default anywhere, and `schema.py`'s columns
  are the baseline's and carry neither 1.1 identity field.

The common shape is the same one the Critique and sweep rows already spend
strong reasoning on: **reading modules against the sentences that claim to
describe them.** A plan written without that check is a restatement of the
work list, which is precisely the failure this document opens by describing —
and every one of the six findings above would have been missed by a pass that
took the queue proposal at its word.

The same fresh-context preference does *not* apply here, and for the opposite
reason: plan authoring benefits from having read the surrounding code and
decisions in the same session, because the findings come from holding a
specification and a module in view at once.

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
