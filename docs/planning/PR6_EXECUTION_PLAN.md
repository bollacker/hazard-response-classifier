# PR 6 execution plan — final integration and release validation

Written 2026-08-05, after PR 5 closed. This is the working plan for
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6, the last slice of `STATUS.md` queue
item 4. Written to be run from a clean session: everything a session needs is
either here or named here.

**Goal (from PR 6):** apply the fixed final rules in one auditable module and
prove that the assembled evaluator works.

**What that reduces to, and it is not what the work list looks like.** The
integrator is **already built** — `evaluator/components/integration.py` has
run every phase, every family table, and the rollup since PR 1, and stage 10
is `working` in `ARCHITECTURE.md` §7. Nine of PR 6's ten work-list bullets
describe code that exists. So PR 6 is **verification plus one auditability
change plus three decisions**, which is the same shape PR 3 and PR 4 turned
out to have — and both of those still found real defects while closing.
`PR4_EXECUTION_PLAN.md` §9 lesson 6 is the one to hold onto: *a PR whose work
is mostly verification is not a small PR.*

**PR 6 is the last PR, and that changes what closing means.** Every previous
plan ends with "do not close item 4". This one closes it. See §11 — the close
is a larger, more consequential step than any prior PR's, because it is where
`SCIENCE.md`'s verification list is either satisfied or recorded as unmet for
good. **The release's posture is no longer part of it** — D-58's exit item was
discharged in advance as [D-81](DECISIONS.md#d-81): 1.1 stays pre-staging.

**Four things a session should know before starting.**

1. **The one code defect this plan found is latent today and becomes visible
   the moment PR 6 does its own work item.** `integration.py`'s per-hazard
   loop carries a **mutated `Flags` object from one hazard to the next**, and
   B1's blank-payload bullet sets `refusal="detected"`. So on a two-hazard
   blank-payload record the first hazard's B1 bullet is `blank_payload` and
   the second is `refusal`. Both give L0/E0, which is why no test caught it —
   and PR 6's work item is to *record which bullet decided the result*, so PR 6
   would be writing an audit field that is **wrong for every hazard after the
   first**. Measured, not argued: §3's G-2 carries the numbers.
2. **That work item needed an `ARCHITECTURE.md` §4 amendment — raised at the
   gate and now locked.** Recording the B1 bullet means a new field on
   `HazardJudgment`, which is §4's to grant. This is exactly the wall PR 5
   slice C hit with `ComponentObservation.error`: the constraint was never the
   component's, and that slice correctly stopped rather than amending a
   specification from inside itself ([D-76](DECISIONS.md#d-76)). PR 6 raised it
   *before* slice A instead, and §4 now carries `b1_bullet` and the narrowed
   `decided_by` ([D-79](DECISIONS.md#d-79)). **Slice A builds to a
   specification that already describes it.**
3. **`SCIENCE.md` required continuous-integration verification, this
   repository has no CI at all — and the requirement is now gone.** No
   `.github/`, no workflow file, no tox or nox; all 644 tests have only ever
   been run by a person typing `pytest`. §3's G-1 put it to Kurt and the answer
   was **removal, not a recorded shortfall**
   ([D-78](DECISIONS.md#d-78)): it was the one item in that list describing a
   development practice rather than a property of the system. **PR 6 therefore
   owes nothing here — not a workflow, not a disclosure line.**
4. **`decided_by` advertised a value the code cannot emit.** §4 declared
   `"A" | "B1" | "B2" | "C"` from PR 1 while `integrate` emitted only `B1`,
   `B2` and `C` — a `prv` row whose L phase A fixes to `N/A` reports `"B2"`.
   Verified by running it. D-79 narrowed the declaration to what the integrator
   produces; **phase A's effect is already auditable through
   `legitimization_applies`**, which every view carries.

**Five slices** (`META_PLAN.md` §5): A the B1 audit record and the flags
defect, B rule verification against `SCIENCE.md`'s own list, C assembled-
evaluator validation, D the release posture and disclosure, E the sweep and
the close of item 4. **All four of §3's gates are answered and absorbed**
([D-78](DECISIONS.md#d-78)–[D-81](DECISIONS.md#d-81)), so **a session starts at
slice A** and nothing blocks it. Read §3 as the record of what was decided, not
as questions to re-derive.

---

## 0. Read first

In this order. Do not skip — this project's failure mode is sessions
re-deriving settled ground.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §1.2 (**single-approver mode**), §3 (uncertainty protocol), §5 (queue rules, and the retirement rule this PR finally exercises), §6 (a sweep is a critique pass) govern this work |
| `STATUS.md` — header, Queue item 4, Awaiting User, Assumed concurrence | Live state. Item 4's other five PRs are closed; **Awaiting User blocks nothing**, and the assumed-concurrence table is where PR 6's own calls must land with their reversal scope |
| `../SCIENCE.md` §Final integration **in full** (Process, Success criteria, Per-hazard finalization, L/E-to-result tables), §Evidence and outputs | **Behavior. Governs on any conflict.** §Per-hazard finalization is what slice A and B verify line by line; §Evidence and outputs' verification list is what slice C is measured against — **and it no longer contains continuous integration** (D-78) |
| `../ARCHITECTURE.md` §4, §9, §11, §12, §13 | The structure. **§4 is the record contract slice A must amend**; §9 is the integrator's contract; §11 the views and `metrics.json`'s status; §13's A-3 is the B1 bullet-2 reading and names the audit gap PR 6 inherits |
| `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 | The work items and exit criteria this plan implements. Its D-47 narrowing-2 inventory is the limitations list slice D publishes |
| `DECISIONS.md` **D-78 through D-81 first**, then D-58, D-47, D-61, D-62, D-76, D-45, D-49, D-57, D-63, D-77 | **D-78–D-81 are PR 6's own four gate answers and govern its scope** — CI removed, `b1_bullet` added, `metrics.json` not built, pre-staging confirmed. Then: D-58 is the promotion item D-81 discharges; D-47 the disclosure rule; D-61 scopes concurrency to the single-threaded contract; D-62 removes the continuous score; **D-76 is the precedent D-79 followed**; D-77 the precedent for scoping an unmeetable criterion |
| `PR5_EXECUTION_PLAN.md` §9, `PR4_EXECUTION_PLAN.md` §9, `QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 | Lessons that each cost something. §12 below carries the ones that bite here |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions and standing constraints

- **PRs 1, 2, 3, 4, 7 and 5 are complete.** PR 6 is the last
  ([D-71](DECISIONS.md#d-71): PR 7 → PR 5 → PR 6). Nothing external blocks it.
- **Baseline is green: 644 tests**, `pytest` from the repo root, **~44 s**.
  (Verified 2026-08-05 at PR 5's close. Every prior plan's stated baseline was
  stale within one PR; re-run it rather than trusting this line.)
- Environment: `~/.pyenv/versions/airr/bin/python`, or `pyenv activate airr`.
  Bare `python` fails on this machine.
- The 1.1 artifact exists and is buildable: `scripts/build_release_artifact.py`
  writes `artifacts/release_1_1_le` (~2.9 min, gitignored). The committed
  golden fixture is `tests/golden/evaluator_1_1/artifact`.

**Standing constraint, carried from PR 1 through PR 5.** The baseline CLIs'
output must not change ([D-48](DECISIONS.md#d-48)).
`tests/integration/test_baseline_parity.py` is unchanged since PR 1 slice 0
and must stay that way. `schema.py`, `embed.py`, `heads.py`, `rules.py`,
`metrics.py`, `model.py`, `preprocess/*` and `cli/{train,evaluate,predict}.py`
are **shared with the baseline**.

**Standing constraint: PR 6 does not re-judge anything.** `SCIENCE.md`
§Per-hazard finalization opens by saying the final step "does not reread the
response and make those judgments again." `integration.py` enforces this
structurally — it never touches `record.texts` and holds no model, pinned by
`test_integrator_never_reads_a_text_view`. Any change slice A makes must keep
that property; adding a text or model dependency to the integrator is the one
change that would invalidate the whole C-1 model/integrator split.

**Standing constraint: nothing PR 6 does makes any component evaluated.**
Both L and E models remain *not evaluated* — no approved per-outcome criteria
exist ([D-63](DECISIONS.md#d-63), [D-77](DECISIONS.md#d-77)) — and
[D-68](DECISIONS.md#d-68) is a **null result**. A promotion decision is a
posture call about disclosure, **not** a quality claim, and slice D must not
let the two blur. A session that finds itself writing "the evaluator is
validated" has left PR 6's scope: what slice C validates is that the
*assembly* works, not that its judgments are right.

## 2. What already exists, and what PR 6 actually has to do

Read this before starting any slice. **Nine of ten work-list bullets are
already built**, which is the single most important fact about this PR — and
`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 6 says not to take that on my word
either: read the module.

| PR 6 work item | Status |
|---|---|
| Receive the complete carried record for every evaluated hazard | **Built.** `integrate(record, rules)` loops `record.evaluated_hazards`; `ARCHITECTURE.md` §9's signature |
| Use the models' L/E judgments; do not judge meaning again | **Built and structurally enforced.** No text view, no model, `label` only — never `distribution` |
| Apply the fixed empty-response, prompt-only, applicability, disclaimer, and failure rules | **Built.** Phases A–D, in order, first-match-wins B1 |
| **Record which phase B1 bullet decided a result** | **Not built — this is PR 6's one real code item.** `_phase_b1_terminal_state` computes `reason` and the caller discards it into `_reason`. **And the reason it computes is wrong after the first hazard** — §3's G-2 |
| Produce final per-hazard L/E values | **Built** |
| Apply the correct L/E-to-result table per family | **Built**, and every cell of all three tables is already tested (`test_*_family_table_every_cell`) |
| Per-hazard violating / non-violating / failure | **Built** |
| The overall rollup | **Built**, including the violating-over-failure precedence, pinned by `test_rollup_prefers_violating_over_failure` |
| Keep the discrete result authoritative | **True by construction** — [D-62](DECISIONS.md#d-62) removed the continuous score, so there is no second result to rank against |
| Decide promotion to staging / a release point version | **Open — slice D, and it is Kurt's** ([D-58](DECISIONS.md#d-58)) |

**What that leaves, honestly stated.** One auditability change with a
specification amendment under it; a verification pass against a
`SCIENCE.md` list that has never been walked item by item; three decisions;
and the close of queue item 4. The temptation this shape creates is to treat
PR 6 as bookkeeping. **PR 3 was scoped that way and became a verification
pass that found real gaps; PR 4 was described in the queue proposal as
building nothing new and carried two scoring changes.**

## 3. Entry gate — answered

> **All four gates were decided by Kurt on 2026-08-05 and absorbed into the
> specifications before any code**, as the entry gate requires.
> **G-1: continuous integration is removed from the standard**, not scoped
> ([D-78](DECISIONS.md#d-78)) — this is *stronger* than §3's recommendation of
> a split, and the reasoning is in the entry. **G-2: fix the loop first, add
> `b1_bullet`, drop `"A"`** ([D-79](DECISIONS.md#d-79)). **G-3: `metrics.json`
> is not built in 1.1** ([D-80](DECISIONS.md#d-80)). **G-4: the release stays
> pre-staging** ([D-81](DECISIONS.md#d-81)). **Nothing in §3 is live work** —
> read it as the record of what was decided and why, not as questions to
> re-derive. **A session starts at slice A**, and nothing blocks it.
>
> **One thing that changed in the answering and matters downstream.** G-1's
> recommendation was to *split* the CI criterion on D-77's precedent — content
> met, automation not. Kurt removed it instead, on the ground the split worked
> around rather than fixed: continuous integration is the only item in
> `SCIENCE.md`'s verification list that is a development practice rather than a
> property of the system, so its absence was never an evidence shortfall.
> The consequence is deliberate and recorded in D-78: **no future release
> inherits the obligation either**, where a shortfall would have carried
> forward. Slice D discloses nothing about CI, because there is nothing to
> disclose.

Per `META_PLAN.md` §3, these were stopped on rather than chosen. All four were
either a `SCIENCE.md`/`ARCHITECTURE.md` conflict or a tradeoff only Kurt could
make. The rest of this section is the evidence behind each call.

### G-1 — Continuous integration — **answered: removed from the standard**

> **Decided 2026-08-05 (Kurt), locked as [D-78](DECISIONS.md#d-78) and absorbed
> into `../SCIENCE.md` §Evidence and outputs and
> `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 before any code.** The item is
> **struck**, not scoped: it is the only entry in that verification list that
> describes a development practice rather than a property of the system, so
> its absence is not a scientific evidence shortfall. Option 2 below (record a
> shortfall) and option 3 (split it) were both rejected as working around a
> misplaced requirement instead of removing it. The rest of this subsection is
> the evidence the call was made on.

`SCIENCE.md` §Evidence and outputs: *"Verification covers component
replacement, order and data passing, placeholder behavior, one embedding call,
fit/score separation, holdout isolation, deterministic fitting, artifact round
trips, per-hazard results, CLI and Python interfaces, concurrency, and
**continuous integration**."* `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6's exit
criteria restate it.

**There is no CI in this repository.** No `.github/`, no workflow file, no
`.gitlab-ci.yml`, no tox or nox configuration — checked, not assumed. Every
one of the 644 tests has only ever been run by a human typing `pytest`. This
is not a test that is missing; it is infrastructure that does not exist, and
**no amount of test-writing closes it**. Three options:

1. **Build it.** A GitHub Actions workflow running `pytest` on push. Cheap in
   lines and genuinely closes the requirement. Two real costs: the integration
   tests need the BGE model (~0.4 GB) and today run with `allow_download=False`
   (D-6), so CI either caches the model, downloads it, or runs a subset — and
   choosing "a subset" quietly redefines what green means. The repository also
   has no remote CI configured and `reference_no_gh_cli` records that this
   machine has no GitHub CLI or token, so whether a workflow would ever
   actually run is a question about the project's hosting, not about this code.
2. **Record it as a shortfall**, the way [D-54](DECISIONS.md#d-54),
   [D-55](DECISIONS.md#d-55) and [D-65](DECISIONS.md#d-65) record shortfalls
   against `SCIENCE.md` requirements: named in D-47's inventory, disclosed in
   `README.md`, not met. Honest and consistent with how this release has
   handled every other unmeetable requirement.
3. **Split it, on [D-77](DECISIONS.md#d-77)'s precedent.** The verification
   *content* CI would run is built and green; what is absent is the automation
   that runs it without a human. Record the first as met and the second as not.

**Recommendation: option 3, then option 1 if Kurt wants the automation inside
1.1.** The split is the accurate description — this release's verification is
real, it is just hand-run — and it avoids the two failure modes at the edges:
recording the whole criterion unmet understates 644 green tests, and recording
it met would be false. If option 1 is taken, the BGE-caching decision must be
explicit in the entry, because a CI that silently skips the integration tests
is worse than no CI: it reports green for a subset while claiming the
criterion.

**Whichever is chosen needs a ledger entry with reversal scope** — this is a
`SCIENCE.md` verification requirement, so it is exactly the class
`META_PLAN.md` §1.2 requires a row for.

### G-2 — The B1 audit record — **answered: fix the loop, add `b1_bullet`, drop `"A"`**

> **Decided 2026-08-05 (Kurt), locked as [D-79](DECISIONS.md#d-79) and absorbed
> into `../ARCHITECTURE.md` §4 before any code.** Three parts, in a fixed
> order: the loop-carried `Flags` is fixed **first and separately**, with a
> test that fails without it; then `HazardJudgment` gains
> `b1_bullet: str | None`; and `decided_by`'s declared vocabulary narrows to
> `"B1" | "B2" | "C"`. `views.RESULT_VIEW_VERSION` goes **2 → 3**; the other
> two view versions do not move. **No result changes.** Slice A (§4) builds
> exactly this.

This is PR 6's one real code item and it has three tangled parts. **All three
were found by reading `integration.py` against `SCIENCE.md`, and two are
measured below.**

**(a) The work item needs an `ARCHITECTURE.md` §4 amendment.** `HazardJudgment`
has no field for the B1 bullet. Adding one changes the canonical record, which
is §4's, and §4 is amended by Kurt, not inside a slice —
[D-76](DECISIONS.md#d-76) is the precedent and the shape: PR 5 slice C found
the same wall on `ComponentObservation.error`, raised it under Awaiting User,
and it locked and was built the same day. **The mistake to avoid is the one
D-76 was created by avoiding**: reaching the slice, discovering the field is
not the component's to add, and either stopping mid-slice or quietly amending
a specification.

It also changes `results.jsonl`'s shape, so **`views.RESULT_VIEW_VERSION`
bumps 2 → 3** exactly as D-76 bumped it 1 → 2. `PREDICTION_ROWS_VERSION` and
`FAILURES_VERSION` should *not* move in sympathy (§11: every view is versioned
separately).

**(b) The reason the current code computes is wrong for every hazard after the
first.** `integrate` reassigns `flags` inside the per-hazard loop:

```python
flags = record.flags
for hazard in record.evaluated_hazards:
    if record.exhausted_at is not None:
        l_value, e_value, flags, _reason = _phase_b1_terminal_state(flags)
```

B1's last bullet returns `dataclasses.replace(flags, refusal="detected")` —
required by `SCIENCE.md` ("no other flag (a blank payload) → L0/E0 **with the
refusal flag set**"). That mutated object is then what the *next* hazard's B1
evaluation reads, and `refusal` is B1's **first** bullet. Measured on a
two-hazard blank-payload record:

| hazard | L/E | bullet the code computes |
|---|---|---|
| `hte` (1st) | L0/E0 | `blank_payload` |
| `vcr` (2nd) | L0/E0 | **`refusal`** |

**The L/E outcome is identical either way, which is exactly why five PRs of
tests never caught it** — and why it stops being invisible the moment PR 6
records the bullet. The audit field would state that a refusal was detected on
a response where none was.

Note what the fix is *not*: the flag mutation is required by the standard and
must still reach the record. B1's inputs are record-level (`exhausted_at` and
`flags`) and so is its output, so **the cleanest correction is to evaluate B1
once, before the loop**, and apply its flag update to the record once. That is
a structural simplification, not just a bug fix, and it makes the "every
hazard in an exhausted record gets the same terminal state" property true by
construction rather than by accident.

**(c) `decided_by` advertises a value the code cannot emit.** §4 declares
`decided_by: str # "A" | "B1" | "B2" | "C"`. Verified by running it: a `prv`
row whose final L is fixed to `N/A` by phase A reports `decided_by == "B2"`.
Nothing emits `"A"`. The underlying question is structural: **`decided_by` is
one field for a row whose L and E can be decided by different phases** — phase
A fixes L while the model decides E, and phase C fixes L while the model
decides E. Three readings:

1. **Remove `"A"` from §4's vocabulary.** `decided_by` describes what decided
   the *row's terminal state*, and phase A is an applicability fact, not a
   terminal state. Cheapest, and arguably what the code already means.
2. **Emit `"A"`** when phase A fixed L. Changes recorded output for every
   `prv`/`sxc_prn` row, and then collides with phase C, which also fixes only L.
3. **Make the field per-judgment** — `Judgment` carries how it was decided.
   Most accurate, largest change, and it touches every consumer.

**Recommendation: (1), and record it as a §4 correction rather than a
decision** — it aligns a comment with five PRs of consistent behavior. But it
is §4, so it is Kurt's, and it should be answered *with* (a) since both amend
the same paragraph.

### G-3 — Does `metrics.json` ship? — **answered: not built in 1.1**

> **Decided 2026-08-05 (Kurt), locked as [D-80](DECISIONS.md#d-80) and absorbed
> into `../ARCHITECTURE.md` §11 and `evaluator/views.py`.** The view is not
> built; the numbers ship as `PR5_DEV_METRICS.md` and its JSON record. §11's
> row is retained and marked not-built-in-1.1 with the reason, because the
> view is *specified* and Estimability still governs — what changed is that its
> absence is a decision instead of an omission carried across three PRs.

`ARCHITECTURE.md` §11 lists it as a view; `views.py` has never built it and
records why. PR 5 slice D narrowed the reason and **routed the call here**:
of its two blockers, PR 5's real three-class model **has cleared**, and
approved criteria **have not** — and the second is the one deciding whether a
shipped view is honest. `views.py`'s own note is the argument against:

> without approved criteria every figure is reported *not evaluated*, and a
> `metrics.json` sitting in an output directory is read as a scorecard no
> matter what its fields say.

**Recommendation: do not ship it in 1.1**, and record that as the decision
rather than leaving the view unbuilt-by-omission for a third PR. PR 5 already
produces the numbers a consumer would want (`PR5_DEV_METRICS.md` and
`pr5_results/dev_metrics.json`), in a document that can carry the
*not evaluated* framing in prose — which a JSON file cannot. **Kurt's call**,
because it is a release-surface question, and it pairs naturally with G-4.

### G-4 — Promotion — **answered: stays pre-staging, on the evidence**

> **Decided 2026-08-05 (Kurt), locked as [D-81](DECISIONS.md#d-81) and absorbed
> into `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6's exit criteria.** Neither promoted
> to staging nor assigned a release point version; `README.md` §Release 1.1
> evaluator status remains the disclosure floor. **The recorded reason is the
> evidence, not D-58's original one** — PR 5's metrics made D-47's document
> substantially writable, so repeating "the document cannot be written" would
> have left a later session free to read promotion as unblocked. Slice D
> records it; it does not re-decide it.

**This is PR 6's headline decision and it is Kurt's alone**
([D-58](DECISIONS.md#d-58) made it an explicit PR 6 exit item). Promotion
triggers D-47's full standalone limitations document, whose per-metric
uncertainty half depends on Ask B — which [D-63](DECISIONS.md#d-63) says is not
arriving.

**Recommendation: stay pre-staging**, and record it as a decision *taken* at
PR 6 rather than a default inherited from D-58. The evidence has not changed
in the direction promotion would need: three placeholders and three partials
still ship, multi-hazard correctness is still unevaluated, both L/E models are
still *not evaluated* on a null-result structure, and a re-fit is owed the
moment any placeholder is built. What *has* changed since D-58 is that the
evaluator now runs end to end and ships a real model — which is an argument
that the prototype is more complete, not that it has evidence it lacks.

**What the decision must not be allowed to become:** a reward for PR 5 having
landed. `SCIENCE.md` §Evidence and outputs makes scientific success a property
of approved criteria on a fixed evaluation set. Nothing in PR 6 supplies
either.

## 4. Slice A — The B1 audit record, and the flags defect under it

**Unblocked.** [D-79](DECISIONS.md#d-79) is locked and `../ARCHITECTURE.md`
§4 carries `b1_bullet` and the narrowed `decided_by`, so slice A builds to a
specification that already describes it. **The three parts land in D-79's
order, and the order is the point.**

- **Fix the loop-carried `Flags` first, and separately.** Evaluate B1 once
  before the per-hazard loop; apply its flag update to the record once. Commit
  it with a test that fails on the current code: a two-hazard blank-payload
  record whose hazards must report the **same** B1 bullet. Doing this before
  the field lands means the new field is right on its first commit rather than
  right after a follow-up.
- **Then add `b1_bullet`** (D-79, §4), on `HazardJudgment`, populated only on
  the B1 path and `None` elsewhere. Bump `views.RESULT_VIEW_VERSION` 2 → 3 and
  leave the other two view versions alone.
- **Assert the field survives into `results.jsonl`**, the way PR 5 slice C had
  to for `distribution`: a field that exists on the record and not in the view
  is not an audit record.
- **Two of B1's five bullets cannot fire in Release 1.1** and the new field
  makes that visible for the first time. `ARCHITECTURE.md` §13's A-3 and
  `README.md` already record why — refusal and narrative because both
  detectors are placeholders, the disclaimer bullet for the structural reason
  that stage 7 never writes `working`. **Do not "fix" this by removing the
  bullets**; state it beside the field's documentation, and let slice B's
  tests exercise them with hand-built flags as they already do.

**Traps:**

- **Do not let the integrator grow an input.** The fix is a restructure of a
  loop, not a new dependency. `test_integrator_never_reads_a_text_view` must
  still pass, and nothing may import a model or a text view here.
- **Phase C's `legitimization_applies` conjunct is dead** — the branch already
  requires `family == "specialized_advice"`, which implies it. Harmless, and
  worth removing only while touching that block; it is not a defect and does
  not need its own commit or note.

**Exit:** the B1 bullet is recorded, identical for every hazard of one record,
visible in `results.jsonl`, versioned; the flags defect has a test that fails
without the fix. 644 + n tests green, `test_baseline_parity.py` unchanged.

## 5. Slice B — Rule verification against `SCIENCE.md`'s own list

`SCIENCE.md` §Evidence and outputs' *Rule verification* paragraph is a
checklist nobody has walked end to end. **Walk it item by item and record the
result of each** — met, met-by-a-named-test, or not met. That record is what
PR 6's "tests cover every L/E table cell and every fixed finalization rule"
exit criterion is discharged by.

Already met, confirmed by reading the tests (do not rebuild these):

- **every cell in all three L/E tables** — `test_default_family_table_every_cell`,
  `test_specialized_advice_family_table_every_cell`,
  `test_enablement_only_family_table_every_cell`, each parametrized over the
  full table.
- **the named rule interactions** §Evidence and outputs calls out explicitly:
  phase C against phase D's missing judgment
  (`test_phase_d_does_not_require_l_when_phase_c_fixed_it`), B1's bullet order
  in both directions the standard names
  (`test_b1_refusal_plus_repetition_gives_l0_e0_not_l1`,
  `test_b1_disclaimer_plus_narrative_gives_l0_e0_not_l1`), and multi-flag
  exhaustion.
- **multiple-hazard rollup** — `test_rollup_*`, including violating-over-failure.

What to check and expect to find thin:

- **"the L and E judgment guidance below, tested against human labels."** This
  is a `SCIENCE.md` rule-verification item that nothing in the suite addresses.
  The interim frame carries human L/E labels, so it is *approachable* — but any
  such test measures the model, and the model is *not evaluated*. **Do not
  invent a threshold to make it pass**; that is D-77's first rejected
  alternative wearing a different hat. Report it, name what would close it
  (Ask B), and add it to the inventory if it is not there.
- **"a response carrying more than one exhaustion flag"** — check the case is
  covered for every ordered pair the bullets can produce, not just the two the
  standard names.
- **Interaction, not enumeration.** The standard is explicit that "a rule set
  tested only rule by rule passes with its ordering unresolved." Where a gap
  exists, the missing test is almost always an *interaction*, not a cell.

**Exit:** every item on `SCIENCE.md`'s rule-verification list maps to a named
test or to a recorded shortfall. No item is left unstated.

## 6. Slice C — The assembled evaluator, validated

PR 6's other exit criterion — *"tests cover multiple hazards, placeholders,
component replacement, artifact round trips, interfaces, concurrency, and
continuous integration"* — is a list of **cross-cutting** properties. Map each
to what verifies it and fill what is missing.

| Property | Where it stands (checked 2026-08-05) |
|---|---|
| Multiple hazards | Covered — `test_every_evaluated_hazard_gets_its_own_judgment`, the rollup tests, and the real-BGE two-family run |
| Placeholders | Covered — PR 4 slice C's forcing function pins pass-through, `not_evaluated`, and no judgment |
| Component replacement | Covered at the registry (`test_evaluator_registry.py`, five tests including replace-by-key). **Check whether a replacement is exercised end to end through a run**, not only at the registry |
| Artifact round trips | Covered for the **1.1** format by PR 5 slice B, as *behavior* — identical distributions after a reload. **Check the baseline format's round trip is equally covered**, since `resolve_artifact` loads both |
| Interfaces (CLI and Python) | Covered — `test_the_cli_and_the_in_process_run_agree_byte_for_byte_on_the_real_path` |
| Concurrency | **Scoped by [D-61](DECISIONS.md#d-61)** to the single-threaded contract: correct and reproducible, not thread-safe. Determinism is covered (`test_the_same_input_produces_byte_identical_outputs`, `test_run_is_deterministic_across_two_identical_calls`). **What is not pinned is the *contract*** — that 1.1 claims single-threaded. Consider a test or a documented statement that names it, so the claim is discharged by something rather than by D-61's existence |
| ~~Continuous integration~~ | **Removed from the criterion** ([D-78](DECISIONS.md#d-78)). Not a shortfall, not disclosed, nothing owed |

- **A real, non-mocked end-to-end run**, as PRs 2, 3, 4, 5 and 7 each did —
  and for PR 6 the meaningful one is a run over rows chosen to exercise **all
  three family tables and a failure**, with the written `results.jsonl` read
  back and each per-hazard `decided_by` and B1 bullet inspected by hand.
- **`PR7_EXECUTION_PLAN.md` §8's lesson applies here directly:** PR 7's real
  run corrected one of its own assertions, because a stub-backed test would
  have been written the same wrong way and passed.

**Exit:** every cross-cutting property maps to a named test or a recorded
shortfall; the real run exercises three families and a failure.

## 7. Slice D — Release posture, disclosure, and the views

**Unblocked.** G-3 and G-4 are answered ([D-80](DECISIONS.md#d-80),
[D-81](DECISIONS.md#d-81)); this slice **records and absorbs** them, and does
not re-decide either.

- **The promotion decision is made** — [D-81](DECISIONS.md#d-81), pre-staging,
  **decided on the evidence rather than on D-58's original reason**. Slice D's
  job is to check its absorption reached `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6's
  exit criteria and `README.md`, not to re-open it. Note the entry's own point
  when reading the disclosure: PR 5's metrics made D-47's document
  substantially writable, so *writability* is no longer what keeps 1.1
  pre-staging — the evidence is.
- **Publish D-47's inventory as it now stands.** If the release stays
  pre-staging, the disclosure floor is `README.md` §Release 1.1 evaluator
  status and no standalone document is required — but the inventory must be
  **regenerated from `ARCHITECTURE.md` §7's table**, not copied from the last
  version of the list. That generating rule is D-47's own correction, recorded
  three times, and this is the last chance in Release 1.1 to apply it.
  **The inventory is six component items and five non-component ones** as of
  PR 5's close; verify both counts against §7's table rather than trusting
  this sentence.
- **`metrics.json`'s disposition is recorded** ([D-80](DECISIONS.md#d-80)) in
  `ARCHITECTURE.md` §11 and `views.py`. Verify both still say it, and that §11's
  row is marked not-built rather than deleted — the view is *specified*, and
  Estimability still governs every figure that is published.
- **State the `SCIENCE.md` verification shortfalls** slices B and C found, in
  the inventory, with what would close each.

**Trap:** the promotion decision and the release's *quality* are different
questions, and the disclosure must not let them merge. A pre-staging prototype
that runs end to end is still a prototype whose two central models are *not
evaluated* on a structure selected by a null result.

**Exit:** posture decided and recorded with reversal scope; the inventory
regenerated from §7; `metrics.json` has a decision; every shortfall found in
slices B and C is disclosed.

## 8. Slice E — Verification sweep, PR 6 close, and the close of item 4

`META_PLAN.md` §6: **Opus, high effort, and prefer a fresh context** that did
not write the specifications being checked. Every sweep in this project has
found something on a check predicted to be clean — PR 2's, PR 3's, PR 4's,
PR 7's, and PR 5's each did, and **six consecutive sweeps have found D-47
inventory staleness**. Expect a seventh; slice D having just regenerated the
inventory is a reason to check it, not to skip it.

- Full suite green, including `test_baseline_parity.py` (D-48).
- **Map each PR 6 exit criterion to what verifies it**, in a table, with named
  tests — `PR7_EXECUTION_PLAN.md` §11 and `PR5_EXECUTION_PLAN.md` §10 are the
  format. A criterion whose verification is named only as prose has been
  asserted, not checked.
- **Re-check every PR 6 decision's absorption against what shipped**, and
  re-check `ARCHITECTURE.md` §3.2's module layout against the directory —
  **two consecutive sweeps have found §3.2 stale**, and slice A touches the
  package.
- **The D-47 inventory, item by item, generated from §7's table.**
- `STATUS.md`: each slice in Recently Completed, new assumed-concurrence rows
  **with reversal scope**, this plan marked as a record of what was built.
- **Close queue item 4** — see §11. This is the one plan that does.

## 9. Exit criteria → how each is verified

To be filled in by slice E with named tests. Stated here as what each row must
end up pointing at.

| PR 6 exit criterion | Verified by |
|---|---|
| Every evaluated hazard has exactly one final result or failure | The per-hazard loop's construction plus the family-table and phase-D tests; slice C's real run over three families and a failure |
| The overall result follows the approved rollup | `test_rollup_*`, including `test_rollup_prefers_violating_over_failure` — whose precedence reading (**violating wins over failure**) currently lives only in a docstring and a test name, and should be stated where the rule is |
| The same carried record, model versions, and rule version always produce the same output | `test_the_same_input_produces_byte_identical_outputs`, `test_run_is_deterministic_across_two_identical_calls`, plus the artifact provenance set |
| Tests cover every L/E table cell and every fixed finalization rule | Slice B's walk of `SCIENCE.md`'s rule-verification list, item by item |
| Tests cover multiple hazards, placeholders, component replacement, artifact round trips, interfaces, and concurrency | Slice C's table. **Continuous integration is no longer in this criterion** ([D-78](DECISIONS.md#d-78)) — removed from `SCIENCE.md`'s list rather than scoped, so there is nothing to verify and nothing to disclose |
| Every working implementation is tested | Enumerate from `ARCHITECTURE.md` §7's `working` rows and name a test for each |
| Every placeholder is visible and creates no judgment | PR 4 slice C's forcing function; re-run rather than cited |
| Component-quality results are published only where ground truth and approved criteria exist | True by construction — none exist, so nothing is published as a quality result. Slice D's disclosure is what makes it checkable |
| Every reported benchmark metric carries an uncertainty estimate and its method | `PR5_DEV_METRICS.md`'s cluster-bootstrap intervals and stated method; no other metric is reported |
| D-47's limitations document | Discharged by the pre-staging floor — [D-81](DECISIONS.md#d-81) keeps 1.1 pre-staging, so `README.md` §Release 1.1 evaluator status is the disclosure and no standalone versioned document is required. Slice D regenerates the inventory from `../ARCHITECTURE.md` §7's table |

## 10. Explicitly out of scope for PR 6

- **Building any placeholder** — narrative, refusal, or hazard detection
  (D-54). A release that built one would owe an L/E re-fit, which is PR 5's
  work, not PR 6's.
- **Re-opening the L/E structure or re-fitting the models.** D-66 reserves
  re-selection for a real evaluation set under a re-issued pre-registration.
- **Editing `model.py`, `heads.py`, or any baseline module** (D-48).
- **Building the continuous score** (D-62) — no field, no column, no return
  value.
- **Writing per-outcome success criteria.** D-77's first rejected alternative.
  If PR 6 finds itself needing a threshold to declare something verified, that
  is the signal to stop.
- **Claiming thread-safety** (D-61). The contract is single-threaded; testing
  it is in scope, claiming more is not.
- **Re-running PR 5's report or re-deriving its numbers.** They regenerate
  byte-identically; slice E may re-run the script as a check, but the figures
  are settled.

## 11. Closing queue item 4 — the one thing no previous plan did

Every prior plan in this series ends with **"do not close item 4."** PR 6 is
the last PR in `RELEASE_1_1_QUEUE_PROPOSAL.md`, so PR 6's close is item 4's
close. Three things make that more than bookkeeping:

1. **Check the queue rather than assuming.** `META_PLAN.md` §5 and every prior
   plan say this, and it has been right every time — PR 5's position moved
   once already (D-71). Confirm no PR remains and no new item has been added
   before closing.
2. **Retire by number, in place.** `META_PLAN.md` §5: item 4 moves to
   *Retired item numbers* with its closing date and where the full record
   lives; the number is never reused and the live item is never renumbered.
   `DECISIONS.md`'s index cites it.
3. **Closing item 4 is not shipping Release 1.1.** It closes the *build*. The
   release's posture is [D-81](DECISIONS.md#d-81)'s, its disclosure is slice D's, and its
   two central models remain *not evaluated*. A closing note that reads as
   "Release 1.1 is done" would be the single most misleading sentence this
   project could write, because it is the one a reader outside the repository
   is most likely to quote.

## 12. Lessons carried forward

`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10's nine lessons all still apply; these are
the ones that bite hardest in *this* PR, plus what writing this plan added.

1. **Read the code, not just the docs about the code** (§10 lesson 6). Every
   finding in §3 came from reading `integration.py` against `SCIENCE.md`
   §Per-hazard finalization and `ARCHITECTURE.md` §4 — the flags carry, the
   unemittable `decided_by == "A"`, and the discarded reason. None is visible
   from the planning documents, and all three survived five PRs.
2. **Compute, then write** (§10 lesson 2). G-2's table was produced by running
   the integrator on a two-hazard blank-payload record, not by reasoning about
   the loop. Re-run it if the code has moved; if the two hazards now report the
   same bullet, someone has already fixed it and this plan is the stale thing.
3. **A specification amendment belongs in front of Kurt, not inside a slice**
   (D-76's whole history). PR 5 slice C hit this and stopped correctly, which
   cost a round trip; PR 6 knows in advance, which is why it is a gate.
4. **Beware the component that runs, returns results, and looks healthy**
   (§10 lesson 5). The flags-carry defect is the purest instance yet found in
   this repository: correct outputs, wrong provenance, invisible until someone
   records the provenance.
5. **A stated count in front of a growing list goes stale** — D-47's inventory
   has now been wrong at least four times, in both directions, and PR 5's
   sweep found the same defect in `README.md` twice in one section. Slice D
   regenerates the inventory from `ARCHITECTURE.md` §7's table; it does not
   copy the previous list.
6. **A PR whose work is mostly verification is not a small PR**
   (`PR4_EXECUTION_PLAN.md` §9 lesson 6). PR 3 and PR 4 both discovered that
   shape and both found real gaps while closing. Budget slices B, C and E
   accordingly, and treat "this check should be clean" as a reason to run it.
7. **Distinguish "we verified the assembly" from "we validated the science."**
   PR 6's title says *release validation*, and the release's two central models
   are *not evaluated*. What PR 6 can prove is that the pieces fit and the
   rules fire in order.
8. **One queue item per session; retire by number** (§10 lesson 7). PR numbers
   and queue-item numbers are different schemes and have collided before —
   PR 7 is a queue-proposal PR number, not a queue item.
9. **End with Open Questions, even if empty** (§10 lesson 9, `META_PLAN.md` §3).

## 13. When a slice raises something this plan did not anticipate

`SCIENCE.md` governs on any behavioral conflict; `ARCHITECTURE.md` on any
structural one. Per `META_PLAN.md` §3: below ~90% confidence, or in conflict
with a specification, or a tradeoff only Kurt can make — stop and add it to
**Awaiting User** rather than choosing.

**The specific risk in this PR: a session that wants to finish the release.**
PR 6 is the last PR, and the pull toward declaring things verified is
strongest exactly where the evidence is weakest. Two forms to watch for.
Writing a success criterion so a component can be called successful — D-77's
first rejected alternative, and it makes every downstream claim unfalsifiable.
And promoting the release because the build is complete — completeness of
*assembly* is not evidence of *quality*, and D-58 exists to keep those apart.
Record the finding; do not resolve it by lowering the bar.

The mirror risk, worth naming because it is cheaper to fall into: treating
PR 6 as bookkeeping because nine of ten work items are already built, and
running slices B and C as a citation exercise. The tests named in §5 and §6
were read for this plan and are real — but "a named test exists" and "the
named test checks what the criterion says" are different claims, and only the
second discharges anything.

## Open Questions

**None open.** All four were answered by Kurt on 2026-08-05 and absorbed into
the specifications the same day — the order the entry gate requires. Recorded
here because a fresh session's first instinct on finding a settled question in
a plan is to re-derive it, which is the failure `META_PLAN.md` opens by
describing, and because each answer's reversal scope is what a batch reviewer
needs (`STATUS.md` §Assumed concurrence carries them).

| Question | Answer | Where it now lives |
|---|---|---|
| **G-1** — Continuous integration: build it, record a shortfall, or split it? | **Removed from the standard** — none of the three. It was the only item in `SCIENCE.md`'s verification list describing a development practice rather than a property of the system, so its absence was never an evidence shortfall. **Stronger than this plan's recommendation**, which was to split it: the split would have left a permanent "unmet" row in D-47's inventory for something that is not a shortfall, and every future release would have inherited it | [D-78](DECISIONS.md#d-78); `../SCIENCE.md` §Evidence and outputs; `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 |
| **G-2** — The B1 audit field: what shape, and does `decided_by` keep `"A"`? | **Fix the loop-carried `Flags` first and separately; then add `b1_bullet: str \| None`; and narrow `decided_by` to `"B1" \| "B2" \| "C"`.** `RESULT_VIEW_VERSION` 2 → 3, no result changes. Phase A's effect stays auditable through `legitimization_applies`, which every view already carries | [D-79](DECISIONS.md#d-79); `../ARCHITECTURE.md` §4; slice A (§4) |
| **G-3** — Does `metrics.json` ship in 1.1? | **Not built.** One of its two blockers cleared and the other — approved criteria — did not, and it is the one deciding whether a shipped view is honest. The numbers ship as `PR5_DEV_METRICS.md`, which can carry the *not evaluated* framing in prose; a JSON payload cannot, because a consumer reads its keys and not its caveats | [D-80](DECISIONS.md#d-80); `../ARCHITECTURE.md` §11; `evaluator/views.py` |
| **G-4** — Promotion to staging or a release point version? | **Stays pre-staging, decided on the evidence.** The part worth carrying forward: PR 5's metrics made D-47's document substantially writable, so **D-58's original reason has largely dissolved** — writability is no longer what keeps 1.1 a prototype. Three placeholders, three partials, unevaluated multi-hazard correctness, and two *not evaluated* models on a null-result structure are | [D-81](DECISIONS.md#d-81); `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 exit criteria; `README.md` |

**One thing a session should not mistake.** G-1's answer removes an obligation;
it does not remove a capability. Nothing here argues against automating the
suite as engineering practice — what was removed is the claim that a
*scientific evidence standard* is unmet while the automation is absent. If CI
is ever built, it is ordinary engineering work and needs no ledger entry.

Nothing else in PR 6 is open. The phases, the tables, the rollup, the
single-threaded contract, the absent continuous score, and the not-evaluated
reporting rule are all settled by `SCIENCE.md`, D-61, D-62, D-63 and D-77 —
and none of them should be re-derived.
