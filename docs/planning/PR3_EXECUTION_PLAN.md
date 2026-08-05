# PR 3 execution plan — hazard detection and multi-hazard routing

Written 2026-08-04, after PR 2 closed. This is the working plan for
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 3, the third slice of `STATUS.md` queue
item 4. Written to be run from a clean session: everything a session needs is
either here or named here.

**Goal (from PR 3):** require a valid supplied hazard, support a configurable
detection scope, and evaluate every hazard actually supplied or detected.

---

## 0. Read first

In this order. Do not skip — this project's failure mode is sessions
re-deriving settled ground.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §3 (uncertainty) and §5 (queue) govern this work |
| `STATUS.md` — header, Queue, Awaiting User | Live state |
| `../SCIENCE.md` §Technical restrictions, §Modular pipeline, §Hazard detection, §Hazard scope configuration, §Final integration | **Behavior. Governs on any conflict.** §Hazard detection's exposure note and §Final integration's withdrawn completeness rule are load-bearing for this PR specifically |
| `../ARCHITECTURE.md` §2, §3, §3.1–§3.2, §4, §6, §7 row 3, §9, §12.1 | The structure this builds inside. §2 is the actual specification for this PR's new work; §12.1 states the exposure this PR does not close |
| `PR1_EXECUTION_PLAN.md` slice 1A | Built `open_run` scoped to registry validation only, **deliberately deferring** supplied-hazard and hazard-scope validation to this PR — read its note in `run.py`'s own module docstring too |
| `PR2_EXECUTION_PLAN.md` | The template this plan follows (read-first list, slices, exit-criterion map) and the precedent for a "verify what's already built" slice |
| `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 3 | The work items and exit criteria this plan implements |
| `DECISIONS.md` D-23, D-27, and the "What the Release 1.1 standard replaces" scope note near the top | D-23: artifact-frozen sets are authoritative, never installed config. D-27: hazard normalization is **carried** for 1.1 even though its baseline fail-per-row *mechanism* is not — the scope note says explicitly: "D-3, D-11, D-14, D-22, D-27, and D-31's per-row handling of a missing or unsupported supplied hazard is baseline-only. Release 1.1 validates that required input before response scoring and rejects the run." |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions — all met as of 2026-08-04

- PR 2 is complete and pushed: slices A and B, plus a follow-up fix for a
  README duplication (`a285656`, `4dbb75f`, `f08cb0d`). `HEAD` is `f08cb0d`.
- Baseline is green: **287 tests**, `pytest` from the repo root.
- Environment: `pyenv activate airr` (or `~/.pyenv/versions/airr/bin/python`).
- No entry condition blocks PR 3: it needs neither the Standards team's
  dataset (that's PR 5) nor the narrative ground truth (that's PR 4).

**Standing constraint, carried from PR 2 — read before touching any file.**
The baseline CLIs' output must not change (D-48). `src/hazard_classifier/
preprocess/*`, `schema.py`, `embed.py`, `heads.py`, `rules.py`, `metrics.py`,
`model.py`, and `cli/*` are **shared with the baseline**; this PR's work
belongs entirely in `src/hazard_classifier/evaluator/`. Nothing in the plan
below touches a baseline module, so `test_baseline_parity.py` is not expected
to need any new attention — but if a slice finds a genuine reason to touch
one, that is an Awaiting User item, not a judgment call (same rule PR 2 §1
stated).

**Standing constraint, specific to this PR: hazard detection stays a
placeholder.** `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 3's own work list says so
explicitly ("Keep hazard detection as a visible placeholder until an
approved implementation exists"), and `hazard.py`'s docstring names the same
blocker narrative detection has — the Standards team's fixed examples, not
built here. This PR is titled "hazard detection **and multi-hazard
routing**" for a reason: almost everything nameable as "routing" (scoring
multiple hazards off one shared embed, carrying separate provisional and
final judgments, rolling up only supplied+detected) is **already built**, as
a side effect of PR 1's architecture. What genuinely does not exist yet is
narrower than the PR title suggests — see §2 below before writing any code.

## 2. What already works, and what this PR actually has to build

Read this before starting slice A — most of PR 3's own "Work" list in
`RELEASE_1_1_QUEUE_PROPOSAL.md` is checked off already:

| PR 3 work item | Status |
|---|---|
| Require and validate one supplied hazard before response processing | **Not built.** `run.py`'s own docstring: "(1) and (2) need a labeled artifact and per-row input data that this slice has no reason to touch -- they are PR 3's." This is the real work — §3 below. |
| Reject the run if the supplied hazard is missing, unsupported, or outside scope | **Not built.** Same as above. |
| Pass the supplied hazard forward without relabeling it as detected | **Already built.** `scoring.py`'s `_judge_hazard`: `source="supplied" if hazard == record.supplied_hazard else "detected"`. |
| Give hazard detection the decoded response and configured scope, not the prompt | **N/A while it's a placeholder.** `HazardDetectionPlaceholder.run` reads nothing from the record at all. This is a contract statement for whichever future PR builds real detection, not something to wire now. |
| Return every additional applicable hazard found in the response | **Not built — and stays that way.** The placeholder returns none, deliberately (see the standing constraint above). |
| Keep hazard detection as a visible placeholder | **Already true.** Nothing to do. |
| Score L and E separately for the supplied hazard and each additional detected hazard | **Already built.** `scoring.py`'s `run` loops `for hazard in record.evaluated_hazards`, producing one `HazardJudgment` per hazard. |
| Reuse the same preprocessing and embedding pass across hazards | **Already built and already tested**: `test_evaluator_scoring_pipeline.py::test_embeddings_are_not_recomputed_per_evaluated_hazard`. |
| Pass every per-hazard result to final integration | **Already built.** `integration.py`'s `integrate` loops `record.evaluated_hazards` the same way. |
| Roll up only the supplied and additional detected hazards, not every hazard merely permitted by scope | **Already built.** The rollup never reads `run.hazard_scope` — only `record.evaluated_hazards`, which is `supplied ∪ detected`, never the whole configured scope. |

**One structural gap behind that last row, worth naming explicitly:**
nothing currently *derives* `evaluated_hazards` from `detected_hazards`
after stage 3 runs. Every existing test sets both fields directly at record
construction. This is harmless today — the placeholder never populates
`detected_hazards`, so there is nothing to derive — but it means "multi-hazard
routing" has never actually been exercised **through a stage-3 component
that populates both fields itself**, only via hand-built fixtures. Slice B
closes exactly that gap with a registry-swapped stub (mirroring PR 1's own
replaceability tests), not by adding derivation logic to `pipeline.py` (which
must stay free of "scientific decision logic," and deriving one record field
from another is arguably that component's own job, symmetric with how the
placeholder already declines to touch `detected_hazards` itself).

So PR 3 is really two different-sized pieces of work: a small, genuinely new
validation layer (slice A), and a verification sweep proving mechanics that
already exist actually hold end-to-end (slice B) — the same shape PR 2 turned
out to have.

## 3. Slice A — Run-entry validation (start here)

**The new code this PR exists to add.** `ARCHITECTURE.md` §2 names two
rejection conditions `open_run` does not yet check:

> 1. the supplied hazard of any input row is missing, unrecognized, or
>    outside `hazard_scope`;
> 2. `hazard_scope` contains a hazard the selected artifact does not support
>    (D-23 — the artifact's frozen sets are authoritative).

§2's literal signature is `open_run(config, artifact) -> Run`; slice 1A built
`open_run(config, registry)` instead, deliberately, deferring both checks
here. This section proposes the concrete mechanism — ARCHITECTURE.md names
*what* must be rejected, not the exact function shape, so this is this
slice's own implementation choice, not an already-locked decision. Flag it
explicitly if you disagree with the shape below; it is a design call, not a
re-derivation of settled ground.

### 3.1 The mechanism

**Two checks, not three — condition 1's three-way phrasing collapses.**
"Unrecognized" and "outside `hazard_scope`" become the same test once
condition 2 runs first: if `hazard_scope` is validated against the artifact's
supported hazards *before* any response is processed, every hazard actually
in scope is, by construction, both a real, recognized code and one the
artifact supports. A response's supplied hazard failing "in `hazard_scope`"
then covers "unrecognized" and "outside scope" as one membership test; only
"missing" (blank) is a distinct, separate check. `RELEASE_1_1_QUEUE_PROPOSAL.md`
PR 3's own exit-criterion line already talks this way — "**Missing and
unsupported** supplied hazards reject the run" — two categories, not three.

**Design:**

1. **Widen `open_run`** to accept the artifact's supported-hazard set and
   validate `config.hazard_scope` against it before anything else, raising
   `RunRejectedError` naming any unsupported hazard found. Take a plain
   `supported_hazards: AbstractSet[str]` parameter — not the whole
   `HazardResponseClassifier` — so `run.py` stays decoupled from `model.py`
   the same way it already is from every other concrete component. The
   caller passes `classifier.trained_hazards` (already the artifact's frozen,
   authoritative set per D-23; already used this way in `scoring.py`). There
   is no 1.1 evaluator artifact yet (D-49) — this is the same baseline
   `HazardResponseClassifier` `scoring.py` already wraps, not a new loader.
2. **Add a sibling function**, e.g. `validate_supplied_hazard(supplied_hazard:
   str, run_context: RunContext) -> None`, called once per response, **before**
   `run_pipeline` is invoked for it (not from inside `pipeline.py` — that
   module's whole point is "no scientific decision logic," and a per-response
   configuration gate belongs with the rest of "run entry," §2, not folded
   into stage control). Normalize `supplied_hazard` first via
   `schema.normalize_hazard` (`.strip().replace("-", "_")`, no lowercasing —
   D-27, **carried** for 1.1 even though the baseline's per-row fail-open
   mechanism is not) before checking membership. Raise `RunRejectedError` if
   the normalized value is blank, or not in `run_context.hazard_scope`.
3. **Every `RunRejectedError` message names the offending value and the
   reason** (§2's own requirement, already the pattern the registry check
   uses — match its style).

Traps:

- Do not validate `hazard_scope` against the artifact *per response*. It is a
  run-wide configuration fact, checked once in `open_run`, not once per row —
  re-checking it per response would be wasted work and would blur which
  check is which when a `RunRejectedError` fires.
- Do not normalize inside `RunConfig.__post_init__` by editing
  `hazard_scope`'s members silently. If a caller passes an already-inconsistent
  scope (mixed hyphens/underscores), normalizing it invisibly could hide a
  real caller bug. Normalize the *supplied* hazard being checked against an
  already-canonical scope, not the scope itself — callers are responsible for
  supplying a normalized `hazard_scope`, matching how `RunConfig` is built
  from trusted configuration, not raw per-row CSV input.
- `open_run`'s existing registry-validation behavior and error message style
  must not change — only add the new check, and keep both failure modes
  distinguishable in the raised message.
- Update `run.py`'s own module docstring once both checks land — it currently
  states, accurately as of PR 1, that conditions (1) and (2) are unbuilt.
  Leaving it unchanged after this slice would immediately misdescribe the
  module, the same class of staleness `DECISIONS.md` D-47 has already been
  caught on twice.

### 3.2 Tests

Extend `tests/unit/test_evaluator_run.py` (do not replace its existing
tests — they cover the registry-validation behavior, which is unchanged):

- `open_run` rejects when `hazard_scope` contains a hazard absent from
  `supported_hazards`, naming the offending hazard.
- `open_run` accepts when every `hazard_scope` member is supported.
- `validate_supplied_hazard` rejects a blank/whitespace-only supplied hazard.
- `validate_supplied_hazard` rejects a supplied hazard outside
  `run_context.hazard_scope`.
- `validate_supplied_hazard` accepts a supplied hazard that normalizes (e.g.
  `"HTE"` or `"hte "` is out of scope for **this** test's own reasoning only
  if the *normalized* form is checked — pick a normalization-sensitive case
  deliberately, e.g. a scope of `{"hte"}` and a supplied value of `"HTE"`, and
  assert on whichever side of D-27's `.strip().replace("-","_")` (no
  lowercasing) actually applies; do not assume case-folding happens if D-27
  says it does not).
- `validate_supplied_hazard` accepts a normalized match (e.g. `hazard_scope =
  {"spc_fin"}`, supplied `"spc-fin"`).

Exit: both new checks are covered in isolation, the existing registry-check
tests are untouched and still pass, 287 + n tests green.

## 4. Slice B — Multi-hazard routing verification and PR 3 close

**Verify what §2 above already showed is built**, the same shape PR 2's
slice B took. No new component behavior beyond slice A's validation layer.

- **A full-pipeline, multi-hazard test using a registry-swapped stub for
  stage 3** (mirroring `test_evaluator_scoring_pipeline.py`'s
  `test_every_component_can_be_swapped_for_a_stub_without_editing_another`),
  not a hand-built record. The stub's `run` should set **both**
  `detected_hazards` and `evaluated_hazards` together — proving the field
  pair that today only ever gets set by test fixtures can be set by a real
  stage-3 component and flow correctly through the rest of the pipeline.
  Assert, through this stub:
  - two separate `HazardJudgment`s exist in `record.per_hazard`, each with
    its own `provisional_l`/`provisional_e` **and** `final_l`/`final_e` (PR 3
    exit criterion: "Multiple hazards receive separate provisional and final
    records");
  - `hazard_source` is `"supplied"` for the row's own hazard and `"detected"`
    for the stub-added one, read from the assembled record after a full run
    — not from a hand-set field (exit criterion: "Supplied and detected
    hazards remain distinguishable");
  - the embedding provider is still called exactly once for the response,
    even with two hazards evaluated (already covered by an existing test
    with hand-set fields; confirm it still holds when stage 3 itself is what
    populates the second hazard).
- **A rollup test through the real pipeline, not `integrate()` in
  isolation**: construct a fixture (or reuse the trained classifier's two
  hazards, `hte` and `prv`) where one hazard's response scores violating and
  the other non-violating, and assert `overall_result == "violating"` at the
  full-pipeline level (exit criterion: "One violating hazard makes the
  overall result violating"). `test_evaluator_integration.py`'s
  `test_rollup_is_violating_when_any_hazard_is` already proves this at the
  `integrate()` function level; this test proves the same claim survives
  contact with the real pipeline, embeddings, and scoring stage.
- **Confirm "Privacy and Sexual Content never require Legitimization" holds
  end-to-end**, not just via `test_phase_a_forces_na_even_when_a_legitimization_judgment_exists`'s
  direct `integrate()` call — one assertion, through the full pipeline, that
  a `prv` or `sxc_prn` hazard's `final_l == "N/A"` regardless of what the
  (partial, `distribution=None`) scoring stage produced.
- **A test that makes the disclosed exposure concrete, not just documented.**
  `ARCHITECTURE.md` §12.1 and `SCIENCE.md` §Hazard detection both name the
  same example: a response that legitimizes sexual abuse of a minor scores
  differently depending on whether `cse` or only `sxc_prn` is in the
  evaluated set, because Legitimization never applies to `sxc_prn` (phase A)
  while it can drive a violating result under `cse`'s default-family table.
  Build a small fixture demonstrating this **contrast** directly (same
  response, evaluated once under each hazard set, different results) and
  assert it — not to fix anything (removing the exposure is out of scope;
  it was a joint, recorded decision, `ARCHITECTURE.md` §13's A-1), but so the
  exposure is a passing, visible test rather than only prose two documents
  already state. This is this PR's own exit criterion ("Hazard detection's
  misses are reported as such") made concrete: nothing downstream
  compensates, and the test proves it rather than asserting it never
  happens.
- **Real, non-mocked BGE run** extending
  `tests/integration/test_evaluator_real_bge.py` with a two-hazard case,
  matching PR 2 slice B's own precedent of exercising the real provider
  rather than only the stub. Use the golden artifact's two trained hazards
  (`hte`, `prv`) so no new fixture training is needed.
- **Full suite green, including `test_baseline_parity.py`** (D-48 unchanged
  — this PR never touches a baseline module, so this should need no new
  attention, only confirmation).
- **Confirm the D-47 limitations inventory still names hazard detection
  correctly.** Its scope is unchanged (still a placeholder, still blocked on
  the Standards team's fixed examples) — this should be a clean
  confirmation, not a fix, but check it explicitly rather than assuming: PR 2
  slice B found a real gap on a check that looked like it should be clean,
  twice.
- **Consider whether slice A's mechanism deserves a `DECISIONS.md` entry.**
  §3.1 above is a design choice this plan makes, not a re-statement of an
  already-locked one — `ARCHITECTURE.md` §2 named the *what*, not the exact
  function shapes or the three-conditions-collapse-to-two reasoning. If it
  holds up through implementation, record it (next available number is
  **D-53** per the ledger's own numbering note); if slice A's own
  implementation finds a better shape, that supersedes this plan's proposal
  outright, not the other way around.
- `STATUS.md` updated: both slices in Recently Completed, `PR3_EXECUTION_PLAN.md`
  itself treated the way `PR1_EXECUTION_PLAN.md`/`PR2_EXECUTION_PLAN.md` were
  once PR 3 closes — a record of what was built, not live work.

## 5. Exit criteria → how each is verified

| PR 3 exit criterion | Verified by |
|---|---|
| Missing and unsupported supplied hazards reject the run before scoring | Slice A: `open_run`'s new artifact-support check, `validate_supplied_hazard`'s missing/out-of-scope checks |
| Supplied and detected hazards remain distinguishable | Already true (`scoring.py`'s `source` field) and already tested with hand-set fields (PR 1); slice B re-confirms it through a real stage-3 stub |
| Multiple hazards receive separate provisional and final records | Already built (`scoring.py`/`integration.py` both loop `evaluated_hazards`); slice B's full-pipeline stub test is the first proof through a real stage-3 component rather than a hand-built record |
| One violating hazard makes the overall result violating | Already proven at the `integrate()` level (`test_rollup_is_violating_when_any_hazard_is`); slice B adds the same claim through the full pipeline |
| Privacy and Sexual Content never require Legitimization | Already proven at the `integrate()` level; slice B adds an end-to-end confirmation |
| Hazard detection's misses are reported as such — no downstream rule compensates | Disclosed in `ARCHITECTURE.md` §12.1, `SCIENCE.md` §Hazard detection, and `README.md`'s Release 1.1 evaluator status section; slice B adds a concrete contrast test proving the exposure is real, not fixing it |

## 6. Explicitly out of scope for PR 3

- A real hazard-detection implementation. Stays a placeholder — blocked on
  the Standards team's fixed examples, same footing as narrative detection.
- Narrative, refusal, and disclaimer-comparison work — PR 4.
- Any three-class model work — PR 5, blocked on the Standards dataset.
- The 1.1 evaluator artifact — still deferred to PR 5/PR 6 (D-49). This PR's
  `open_run` change takes a plain `supported_hazards` set, not a new artifact
  loader.
- Reinstating cross-hazard completeness (the withdrawn phase D rule,
  `ARCHITECTURE.md` §13's A-1). The exposure it used to backstop is accepted,
  recorded, and this PR's own job is to make it a visible, tested fact, not
  to reverse a joint decision unilaterally.
- Editing `preprocess/*` or any other baseline module (§1's standing
  constraint).
- Changing `safe`/`unsafe` in baseline outputs (D-30).

## 7. When a slice raises something this plan did not anticipate

Per `META_PLAN.md` §3: if confidence is below ~90%, or it conflicts with a
specification, or it is a tradeoff only the user can make — stop and add it to
**Awaiting User** rather than choosing. §3.1's mechanism is this plan's own
design proposal, not a locked decision — if implementing it surfaces a better
shape or a real conflict with `ARCHITECTURE.md` §2's literal text, that is
exactly this kind of finding.

Record every slice in `STATUS.md`'s Recently Completed with what landed, what
it verified, and anything found in passing.
