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
| `DECISIONS.md` D-48 – D-52 | D-48 governs what parity means here; D-50/D-51/D-52 are PR 2's own scope calls, already absorbed into the specifications |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions — all met as of 2026-08-04

- PR 1 is complete and pushed: slices 0, 1A, 1B, 1C plus D-48/D-49
  (`9bfa845`).
- PR 2's three scope calls are locked and absorbed: D-50, D-51, D-52.
- Baseline is green: **280 tests**, `pytest` from the repo root.
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

## 2. Entry-gate questions — all three answered 2026-08-04

Every question this plan originally raised is now settled by a locked ledger
entry, and the specifications have been updated. **No slice is gated.** This
section is kept as the record of what was asked and decided; the answers are
already absorbed, so build from the specifications, not from here.

| Question | Answer | Entry |
|---|---|---|
| Q1 — does 1.1 ship summarized/paraphrased repetition? | **No. Exact-only.** Measure later, revisit if the gap proves material | [D-50](DECISIONS.md#d-50) |
| Q2 — what triggers a decoding failure, and what is the consequence? | **Neither, for now.** The decoder always returns a result (worst case: un-decoded text); the trigger is a stub that always reports success. Decoder is `partial`, flag is `not_evaluated`, no integrator consequence | [D-51](DECISIONS.md#d-51) |
| Q3 — is ambiguous-reference recording in scope? | **Removed from 1.1**, not deferred — no specification, no field, no producer | [D-52](DECISIONS.md#d-52) |

Two consequences of Q2's answer are easy to miss and are load-bearing:

- **`flags.decoding_failed` is `not_evaluated`, never `not_detected`.** The
  failure check never ran, so claiming a negative finding would be the exact
  anti-pattern slice 1B's placeholder forcing function exists to catch.
- **The decoder is `partial`, and the release outcome says so.**
  `../SCIENCE.md` §Decoding's success criterion has two halves and only one is
  built, so `RELEASE_1_1_QUEUE_PROPOSAL.md`'s "working decoding" was corrected
  rather than left overclaiming.

Both are already implemented and pinned by
`tests/unit/test_evaluator_decoding_stub.py`.

## 3. Slices

One slice per session, per `META_PLAN.md` §5. Each ends green with its own
tests and a `STATUS.md` update.

### Slice A — Close what PR 1 already earns (start here)

PR 2 has exit criteria that PR 1's components already satisfy behaviorally but
that **nothing asserts**. This slice makes them verified rather than assumed.

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
- **Decoding never silently drops content** (exit criterion 3): assert
  `texts.original` survives verbatim through the whole pipeline and that
  `texts.decoded` is recorded separately, for both a decoded and a
  non-decoded response. This is the criterion's *by construction* half; its
  *by detection* half is stubbed and already pinned by
  `tests/unit/test_evaluator_decoding_stub.py` (D-51), so do not re-assert it
  here.

Traps:

- Build the pipeline the way `tests/unit/test_evaluator_scoring_pipeline.py`
  already does (stub embedding provider, `fit()`-trained synthetic
  classifier). Do not add a real-BGE dependency to unit tests (`PLAN.md`
  §8.1).
- The prompt-only fixture must actually exhaust. Repetition matching requires
  ≥12 normalized characters (`repetition._MIN_MATCH_LENGTH`); a short prompt
  silently fails to match and the test then proves nothing.
- Do not assert `flags.decoding_failed == "not_detected"` anywhere. It is
  `not_evaluated` by decision (D-51), and that distinction is load-bearing.

Exit: the four criteria above are asserted, not assumed; 280 + n tests green.

### Slice B — Verification sweep and PR 2 close

- Full suite green, including `test_baseline_parity.py` — the baseline must
  still be byte-identical (D-48).
- A real, non-mocked run covering PR 2's paths, extending
  `tests/integration/test_evaluator_real_bge.py`. PR 1's own verification gap
  was exactly this: the real provider went unexercised because every test
  stubbed it.
- Confirm the limitations-document inventory (D-47 narrowing 2) names all
  five 1.1 shortfalls: the hazard, narrative, and refusal placeholders, plus
  **decoding's stubbed failure trigger** (D-51) and **stage 4's exact-only
  scope** (D-50). The last two are shortfalls against a stated success
  criterion rather than absent components, which makes them easy to omit.
- Map each PR 2 exit criterion to the test that verifies it, and record any
  criterion met by scoping rather than by building — with a ledger entry,
  never silently.
- `STATUS.md` updated: slices in Recently Completed, new decisions in
  `DECISIONS.md`, new assumed-concurrence rows in the register.

### 3.1 Closed before execution — what D-50/D-51/D-52 already did

This plan originally had slices B, C, and D gated on the three entry-gate
questions. Answering those questions did the work, so the slices are closed
rather than pending. Recorded here so a session does not go looking for them:

| Was | Outcome |
|---|---|
| Slice B — decoding failure flag and error | **Done** as the D-51 stub: `_detect_decoding_failure` seam, `not_evaluated` flag, `partial` maturity, `ARCHITECTURE.md` §7 row 2 updated, pinned by `tests/unit/test_evaluator_decoding_stub.py`. A real trigger is future work with no scheduled PR |
| Slice C — prompt-repetition scope | **Done** as D-50: exact-only confirmed, `RELEASE_1_1_QUEUE_PROPOSAL.md` and `PR1_EXECUTION_PLAN.md` §4 amended, `ARCHITECTURE.md` §7.1 now cites the entry. `repetition.py` needed no change — it already implemented exactly this scope |
| Slice D — ambiguity recording | **Closed** as D-52: requirement removed from 1.1. No code, no flag, no field |

## 4. Exit criteria → how each is verified

| PR 2 exit criterion | Verified by |
|---|---|
| Empty and prompt-only responses remain distinct | Slice A contrast test |
| Repeated material is removed without losing authored additions | Slice A mixed-content test (behavior exists since slice 1B; unasserted until now) |
| Decoding never silently drops content | Slice A original-preserved test. **Met by construction, not detection** — `test_evaluator_decoding_stub.py` pins the stubbed trigger (D-51), so an unrecovered decode is currently indistinguishable from a successful one |
| Mixed repetition and authored-content cases are scored on the authored content | Slice A `decided_by == "B2"` test |
| Prompt-only responses receive the final result required by `SCIENCE.md` | Slice A L1/E0 test, parameterized across families |
| *(work item)* Detect **exact** prompt repetition | Already built (slice 1B) and scoped to exact-only by D-50. Summarized and paraphrased are **not in 1.1**; the gap is disclosed, not verified |
| *(work item)* ~~Record when the prompt resolves an ambiguous reference~~ | **Removed from 1.1** (D-52) — nothing to verify |

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
