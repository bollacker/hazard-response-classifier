# PR 2 execution plan — empty responses, decoding, and prompt repetition

Written 2026-08-04, after PR 1 closed. This is the working plan for
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2, the second slice of `STATUS.md` queue
item 4. Written to be run from a clean session: everything a session needs is
either here or named here.

**Goal (from PR 2):** ensure that later scoring receives readable
response-authored text and an honest record of exclusions and failures.

---

## 0. Read first

In this order. Do not skip — this project's failure mode is sessions
re-deriving settled ground.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §3 (uncertainty) and §5 (queue) govern this work |
| `STATUS.md` — header, Queue, Awaiting User | Live state; eight items sit under assumed concurrence |
| `../SCIENCE.md` §Empty-response detection, §Decoding, §Prompt-repetition detection, §Per-hazard finalization | **Behavior. Governs on any conflict** |
| `../ARCHITECTURE.md` §3.1, §3.2, §4, §5, §6, §7, §7.1 | The structure this builds inside. §7.1 is specifically about stage 4 |
| `PR1_EXECUTION_PLAN.md` | What PR 1 built and what it deliberately left |
| `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2 | The work items and exit criteria this plan implements |
| `DECISIONS.md` D-48, D-49 | The two most recent calls; D-48 governs what parity means here |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions — all met as of 2026-08-04

- PR 1 is complete and pushed: slices 0, 1A, 1B, 1C plus D-48/D-49
  (`9bfa845`). `origin/main` is in sync.
- Baseline is green: **273 tests**, `pytest` from the repo root.
- Environment: `pyenv activate airr` (or `~/.pyenv/versions/airr/bin/python`).
- The 1.1 pipeline runs end to end against the real BGE model
  (`tests/integration/test_evaluator_real_bge.py`).

**Standing constraint for all of PR 2 — read this before touching any file.**
The baseline CLIs' output must not change (D-48). The three baseline
preprocessing modules — `src/hazard_classifier/preprocess/decode.py`,
`segment.py`, and `flags.py` — are **shared with the baseline**, so editing
any of them changes baseline scores and breaks
`tests/integration/test_baseline_parity.py`. **PR 2's new behavior belongs in
`src/hazard_classifier/evaluator/`**, wrapping or reimplementing rather than
modifying the shared modules. If a change to `preprocess/*` looks genuinely
unavoidable, that is an Awaiting User item, not a judgment call — it trades
away the parity guarantee PR 1 exists to establish.

## 2. Entry-gate questions — three, and they gate real slices

Each is a specification conflict or a genuine gap, not a confidence problem,
so per `META_PLAN.md` §3 a session **must not** resolve one on its own.
Surface them, get an answer, then build. **Slice A below is ungated and can
proceed while these are open.**

### Q1 — Does 1.1 ship summarized and closely-paraphrased repetition detection?

**The conflict.** Three documents disagree:

- `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2 work: "Detect exact, summarized, and
  closely paraphrased prompt repetition."
- `../ARCHITECTURE.md` §7.1: "Scoped by Kurt, 2026-08-04: **exact substring
  matching is sufficient for 1.1**," with the shortfall recorded as a
  deliberate gap that makes the component `partial` and must appear in the
  release's limitations document (D-47 narrowing 2).
- `PR1_EXECUTION_PLAN.md` §4: "Summarized or closely-paraphrased prompt
  repetition — PR 2, and `SCIENCE.md` wants all three eventually; **1.1 ships
  exact-only as partial**." This line is internally inconsistent: it assigns
  the work to PR 2 *and* says 1.1 does not ship it, while PR 2 is a 1.1 PR.

`../SCIENCE.md` §Prompt-repetition detection requires all three, and governs
behavior — but §7.1's scoping was a later, explicit decision to ship one of
three and disclose the gap.

**Recommendation: keep exact-only for 1.1** (i.e. §7.1 stands, and PR 2's work
item is the thing that moves). Reasons: §7.1 is the most recent explicit call
and is already absorbed, with a disclosure obligation attached; a paraphrase
detector's *quality* cannot be claimed without the fixed human-labeled ground
truth that is still blocking queue item 2, so building one in PR 2 produces an
unvalidatable component; and shipping a similarity heuristic under a
requirement that says "closely paraphrased" would blur what the component's
stated maturity means — the exact objection §7.1 raised against
`partial_contiguous`.

**If the answer is exact-only:** amend `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2's
work item and exit criteria, fix `PR1_EXECUTION_PLAN.md` §4's contradictory
line, and record a ledger entry (next free number is **D-50**). Slice C
becomes a documentation-and-confirmation slice, not a modeling one.

**If the answer is all three:** slice C is a substantial modeling slice with no
approved evaluation set, and Q1a follows — what method, and what evidence
would justify calling it correct? Expect that to reopen §7.1 and the
component's `partial` maturity.

**Gates:** slice C.

### Q2 — What triggers a decoding failure, and what does the integrator do with it?

**The gap.** `../SCIENCE.md` §Decoding requires that when the decoder cannot
render all substantive content, it returns "the original and best available
text, a decoding-failure flag, and an error," and that "the final integrator
determines the failure consequence." Two halves are missing:

1. **No trigger exists.** `preprocess/decode.py`'s `best_readable_view` always
   returns its best-scoring candidate and has no notion of failing; today
   `evaluator/components/decoding.py` hardcodes
   `flags.decoding_failed = "not_detected"` on every run. Deciding when
   decoding has *failed* needs a rule — plausible signals include a low
   absolute `english_score` on the winning view, residual undecoded material
   (leftover base64-looking tokens, escape sequences, or a high
   non-ASCII/unreadable proportion), or a large gap between the best candidate
   and readable English. None is specified anywhere.
2. **No consequence exists.** `evaluator/components/integration.py` never
   reads `flags.decoding_failed`. `../SCIENCE.md` says the integrator decides
   the consequence but does not say what it is. The candidate consequences are
   materially different: a per-hazard `failure` (phase D), or scoring the best
   available text and merely recording the flag.

**Recommendation: score the best available text and record the flag and error,
and do not fail the hazard** — with the trigger set conservatively so it fires
only on strong evidence of unrecovered content. Reason: failing closed on a
soft heuristic converts every decoder false positive into a lost result, and
`../SCIENCE.md`'s own framing for this component is "never silently drops
content," which a recorded flag satisfies. But this is a risk-appetite call
about under-scoring obfuscated hazardous content, which is exactly the kind of
tradeoff §3 reserves for the user.

**Gates:** slice B.

### Q3 — Is "record when the prompt resolves an ambiguous reference" in 1.1 scope, and what is its shape?

**The gap.** This work item appears **only** in
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2's work list. No specification backs it:
`../SCIENCE.md` §Technical restrictions *permits* using the prompt to "resolve
ambiguous references" but requires no record of having done so;
`../ARCHITECTURE.md` §4's `Flags` has no field for it; and nothing downstream
consumes it. `../SCIENCE.md`'s verification list mentions "ambiguity" rules
generically, but in the context of L/E judgment guidance ("When L is
ambiguous, assume benign intent except for CSE"), which is a model concern,
not a detection one.

Also note: in the 1.1 pipeline as built, **no component currently uses the
prompt to resolve an ambiguous reference at all.** Decoding uses the prompt as
*context* for substitution maps, and repetition uses it for matching. So there
is presently no event to record.

**Recommendation: defer it out of 1.1**, recording the reasoning, on the same
footing as D-49. Building a flag with no producer, no consumer, and no
specification is speculative. If it is kept, it needs a specification first
(`ARCHITECTURE.md` §4 `Flags` gains a field, and something must actually
produce it).

**Gates:** slice D.

## 3. Slices

One slice per session, per `META_PLAN.md` §5. Each ends green with its own
tests and a `STATUS.md` update.

### Slice A — Close what PR 1 already earns (ungated; start here)

PR 2 has exit criteria that PR 1's components already satisfy behaviorally but
that **nothing asserts**. This slice makes them verified rather than assumed,
and it is the only slice that can proceed with Q1–Q3 open.

Deliverables — tests only, in `tests/unit/test_evaluator_pr2_text_flow.py`:

- **Empty and prompt-only responses remain distinct** (PR 2 exit criterion 1).
  Today both exhaust and both reach phase B1, but by different routes and to
  different results: an empty payload yields `exhausted_at ==
  "empty_response"`, `flags.empty_payload == "detected"`, B1's blank-payload
  bullet, **L0/E0**, and the refusal flag set; a prompt-only response yields
  `exhausted_at == "prompt_repetition"`, `flags.prompt_repetition ==
  "detected"`, **L1/E0**, and the refusal flag untouched. Assert the full
  contrast in one test so the two can never collapse into each other silently.
- **Mixed repetition and authored content is scored on the authored content**
  (exit criterion 4). Assert the surviving `working` text contains the
  authored span and none of the repeated one, that `exhausted_at is None`, and
  that the run reaches `decided_by == "B2"` — i.e. the models scored it,
  rather than a terminal rule firing.
- **Prompt-only responses receive the result `SCIENCE.md` requires** (exit
  criterion 5): L1/E0, `non_violating` under every family table. Parameterize
  across a default-family and an enablement-only hazard, since the latter's L
  is forced to `N/A` by phase A and must still land `non_violating`.
- **Decoding never silently drops content** (exit criterion 3), to the extent
  it is true today: assert `texts.original` is preserved verbatim through the
  whole pipeline and that `texts.decoded` is recorded separately, for both a
  decoded and a non-decoded response. The failure-flag half of this criterion
  is slice B's.

Traps:

- Build the pipeline the way `tests/unit/test_evaluator_scoring_pipeline.py`
  already does (stub embedding provider, `fit()`-trained synthetic
  classifier). Do not add a real-BGE dependency to unit tests (`PLAN.md`
  §8.1).
- The prompt-only fixture must actually exhaust. Repetition matching requires
  ≥12 normalized characters (`repetition._MIN_MATCH_LENGTH`); a short prompt
  silently fails to match and the test then proves nothing.

Exit: the four criteria above are asserted, not assumed; 273 + n tests green.

### Slice B — Decoding failure flag and error (gated on Q2)

Deliverables:

- `evaluator/components/decoding.py`: implement Q2's agreed trigger. On
  failure, set `flags.decoding_failed = "detected"`, attach a
  `ComponentError` to the observation, and keep `texts.working` at the best
  available text — never empty it, and never drop content.
- `evaluator/components/integration.py`: implement Q2's agreed consequence.
  If the answer is "record but do not fail," add an explicit test that a
  decoding failure does **not** produce a phase D failure, so the choice is
  pinned rather than incidental.
- `../ARCHITECTURE.md` §7 row 2: update the decoder's description, which
  currently asserts a failure path that does not exist.

Traps:

- Do **not** edit `preprocess/decode.py` (see §1's standing constraint). The
  trigger is computed in the evaluator wrapper from what `best_readable_view`
  already returns (`transform_confidence`, `raw_english_score`,
  `review_english_score`) plus any additional inspection done in the wrapper.
- A threshold chosen here is a science-adjacent constant. Record its value and
  rationale in `ARCHITECTURE.md`, not only in code, and expect it to be
  revisited once real obfuscated data exists.

Exit: a genuinely undecodable fixture sets the flag and carries an error; a
normal response does not; the integrator's consequence is asserted.

### Slice C — Prompt-repetition scope (gated on Q1)

**If Q1 answers "exact-only" (recommended):** this is a documentation slice.
Amend `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2's work item and exit criteria, fix
`PR1_EXECUTION_PLAN.md` §4's contradictory line, add the ledger entry, and
confirm `ARCHITECTURE.md` §7.1's recorded gap and the component's `partial`
maturity are accurate. Add a test asserting the component reports `partial`,
so a later change to `working` maturity has to confront the gap deliberately.

**If Q1 answers "all three":** this is a modeling slice, and the largest in
PR 2. It needs its own design pass before code: what method (embedding
similarity against the already-shared encoder is the obvious candidate, since
stage 8's provider exists), what threshold, what removal granularity
(sentence, span, clause), and — hardest — what evidence justifies the
resulting maturity claim without an approved evaluation set. Do not start this
without answering Q1a from §2.

Traps (both branches):

- `repetition._normalize_with_offsets` maps normalized match positions back to
  raw text so only the matched span is removed. Any new matcher must preserve
  that property **and** the trailing-punctuation extension in
  `_detect_and_remove` — a bug there silently leaks prompt text into, or
  authored text out of, the working text. That trailing-run bug was found by
  hand during slice 1B, not by a test.
- Removal that empties the working text sets `exhausted_at` and routes to
  phase B1. A more aggressive matcher will exhaust responses that currently
  score normally, changing results. Any such change must be identified
  explicitly (`RELEASE_1_1_QUEUE_PROPOSAL.md` §Rules for every PR: "Identify
  every scoring change explicitly").

### Slice D — Ambiguity recording (gated on Q3)

**If deferred (recommended):** record the deferral as a ledger entry with its
reasoning, amend PR 2's work list, and note it in the limitations document's
inventory obligation (D-47 narrowing 2). No code.

**If kept:** specify it first — `ARCHITECTURE.md` §4 `Flags` gains a field,
`record.py`'s `Flags` gains it with a `"not_evaluated"` default (matching
every other flag), and a named component must actually produce it. Then build
and test.

### Slice E — Verification sweep and PR 2 close

- Full suite green, including `test_baseline_parity.py` — the baseline must
  still be byte-identical (D-48).
- A real, non-mocked run through the 1.1 pipeline exercising PR 2's new paths,
  extending `tests/integration/test_evaluator_real_bge.py`. PR 1's own
  verification gap was exactly this: the real provider went unexercised
  because every test stubbed it.
- Map each PR 2 exit criterion to the test that verifies it, in the table
  format §4 uses below, and record any criterion that is deferred or scoped
  rather than met — with a ledger entry, never silently.
- `STATUS.md` updated: PR 2's slices in Recently Completed, any new decisions
  in `DECISIONS.md`, and any new assumed-concurrence rows added to the
  register.

## 4. Exit criteria → how each is verified

| PR 2 exit criterion | Verified by |
|---|---|
| Empty and prompt-only responses remain distinct | Slice A contrast test |
| Repeated material is removed without losing authored additions | Slice A mixed-content test (behavior exists since slice 1B; unasserted until now) |
| Decoding never silently drops content | Slice A original-preserved test + slice B failure-flag test |
| Mixed repetition and authored-content cases are scored on the authored content | Slice A `decided_by == "B2"` test |
| Prompt-only responses receive the final result required by `SCIENCE.md` | Slice A L1/E0 test, parameterized across families |
| *(work item)* Detect exact, summarized, and closely paraphrased repetition | **Gated on Q1** — slice C, and likely amended to exact-only |
| *(work item)* Record when the prompt resolves an ambiguous reference | **Gated on Q3** — slice D, recommended for deferral |

## 5. Explicitly out of scope for PR 2

- Hazard detection, multi-hazard routing, supplied-hazard validation — PR 3.
- Narrative and refusal detection — PR 4. They stay placeholders; do not let
  "working text" work bleed into them.
- Any three-class model work — PR 5, blocked on the Standards dataset.
- The 1.1 evaluator artifact — deferred to PR 5/PR 6 (D-49).
- Editing `preprocess/*` or any baseline module (§1's standing constraint).
- Changing `safe`/`unsafe` in baseline outputs (D-30).

## 6. When a slice raises something this plan did not anticipate

Per `META_PLAN.md` §3: if confidence is below ~90%, or it conflicts with a
specification, or it is a tradeoff only the user can make — stop and add it to
**Awaiting User** rather than choosing. PR 1 produced two such findings late
(D-48's parity-scope conflict and D-49's unbuildable artifact criterion), and
both were found by trying to close a slice rather than by reading in advance.
Expect the same here, and prefer surfacing early over discovering at close.

Record every slice in `STATUS.md`'s Recently Completed with what landed, what
it verified, and anything found in passing.
