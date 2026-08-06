# PR 5 execution plan — L/E training, scoring, and evaluation

Written 2026-08-05, after PR 4 closed. This is the working plan for
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5, a slice of `STATUS.md` queue item 4.
Written to be run from a clean session: everything a session needs is either
here or named here.

**Goal (from PR 5):** select and validate L/E models that treat all three
outcomes as equally important and return the probabilities final integration
needs.

**What that reduces to now that queue item 2 has closed.** The *selection* half
is done — [D-68](DECISIONS.md#d-68) picked a flat three-class multinomial
softmax fitted per hazard (`L1 · W1 · S1 · H3 · V1 · P1`) for both targets, and
`PREREGISTRATION_LE_STRUCTURE.md` §6 fixed the artifact payload. So PR 5 is a
**build**, not a study: move the selected structure out of `experiments/` into
production code, define and write the 1.1 artifact, replace stage 9, and report
per-outcome numbers that are honest about being dev-class and *not evaluated*.

**Three things make it larger than "port a class", and a session should know
all three before starting.**

1. **The selection was fitted on text the evaluator does not produce.**
   `experiments/features.py` embeds the interim frame's raw `response_text`;
   the pipeline embeds `texts.working`, after decoding and prompt-repetition
   removal. `SCIENCE.md` §Legitimization Training requires "working text
   filtered through the preceding components", and PR 5's work list restates
   it. **Neither the pre-registration nor D-68 mentions which text was used**,
   and §7's "what this selection cannot establish" does not list it. This is
   §3's gate question G-1 and it is measured, not argued, in slice 0.
2. **`MultinomialSoftmax` is not serializable as it stands.** It holds live
   `sklearn.LogisticRegression` objects, and [D-37](DECISIONS.md#d-37) forbids
   pickle and `joblib`. Production must persist coefficients, intercepts, *and*
   the per-cell standardization statistics, then score with pure NumPy.
3. **PR 5's first exit criterion cannot be met.** "The selected models meet
   approved per-outcome criteria" — approved criteria are Ask B, which
   [D-63](DECISIONS.md#d-63) established is not arriving. That is a scoping
   decision and needs a ledger entry, the way D-54 and D-55 scoped PR 4's.

**Six slices** (`META_PLAN.md` §5): 0 the measurement the gate needs, A the
production fitter, B the artifact, C the scoring component, D evaluation and
reporting, E the sweep and close. **Slices 0, A, B and C have run** (all
2026-08-05, §4–§7) and **§3's gate questions G-1 and G-2 are answered and
absorbed** ([D-72](DECISIONS.md#d-72), [D-73](DECISIONS.md#d-73)): fit on
pipeline working text, fit split only. **A session starts at slice D.** G-3
stays open and blocks only the close.

---

## 0. Read first

In this order. Do not skip — this project's failure mode is sessions
re-deriving settled ground.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §1.2 (**single-approver mode**), §3 (uncertainty protocol), §5 (queue rules), §6 (a sweep is a critique pass) govern this work |
| `STATUS.md` — header, Queue item 4, Awaiting User, Assumed concurrence | Live state. Nothing in Awaiting User blocks this scope; the assumed-concurrence table is where PR 5's own new calls must land |
| `../SCIENCE.md` §Legitimization model, §Enablement model (**both Training and Scoring subsections**), §Evidence and outputs | **Behavior. Governs on any conflict.** The working-text sentence in each Training subsection is what G-1 turns on; the not-evaluated rule is why PR 5's headline exit criterion cannot be met |
| `PREREGISTRATION_LE_STRUCTURE.md` §1, §2, **§5, §6**, §7, §8 | The procedure that produced D-68. **§6 is the artifact specification for slice B**; §5's touch budget is what forbids "just re-run the selection"; §7 is the disclosure list PR 5 adds to; §8's seven amendments are the precedent for how a departure is recorded |
| `../ARCHITECTURE.md` §4, §6, §7 row 9, §8, **§10**, §11, §12 | The structure this builds inside. §4 is the `Judgment`/`distribution` contract, §10 the artifact table, §12 records D-68's closure of the L/E slot |
| `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 | The work items and exit criteria this plan implements |
| `DECISIONS.md` D-68, D-66, D-63, D-65, D-45, D-37, D-49, D-57, D-23 | D-68 is the selection (**read its null-result framing**); D-45's unfittable-is-unavailable rule is what per-hazard cells force PR 5 to implement again; D-37 bars pickle; D-49 makes the artifact format PR 5's and its round trip PR 6's |
| `QUEUE_ITEM_2_EXECUTION_PLAN.md` §10, `PR4_EXECUTION_PLAN.md` §9 | Lessons that each cost something. §11 below carries them forward |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions and standing constraints

- **PR 4 is complete** (`c93baae`); PRs 1–4 are landed. Item 4 stays open.
- **Sequencing: PR 7 → PR 5 → PR 6** ([D-56](DECISIONS.md#d-56) places PR 7;
  [D-71](DECISIONS.md#d-71), 2026-08-05, moves PR 5 ahead of PR 6). **PR 5 runs
  second of the three remaining PRs.** It was last until D-71, on a reason —
  the Standards-team data gate — that D-63 had already removed; what moved it
  is that PR 6 must test *artifact round trips* while D-49 makes the artifact
  format PR 5's deliverable. Nothing in PR 5 depends on PR 7 or PR 6 existing,
  so a session may run it whenever PR 7 is done.
- **Baseline is green: 525 tests**, `pytest` from the repo root, ~23 s.
  (Corrected 2026-08-05 at slice A: 433 was PR 4's count, written before PR 7
  landed 92 more. Slice A takes it to **576** in ~40 s — see §5 — slice B to
  **600**, slice C to **624**, and D-76 to **628** in ~43 s.)
- Environment: `~/.pyenv/versions/airr/bin/python`, or `pyenv activate airr`.
  Bare `python` fails on this machine.
- The data exists and is frozen: `data/interim_split_v1.json` (`interim-v1`,
  seed `20260804`), loaded by `interim_data.load_interim(split=...)`, verified
  against the source SHA-256 in `PREREGISTRATION_LE_STRUCTURE.md` §1.

**Standing constraint, carried from PR 1 through PR 4.** The baseline CLIs'
output must not change ([D-48](DECISIONS.md#d-48)).
`src/hazard_classifier/{schema,embed,heads,rules,metrics,model}.py`,
`preprocess/*`, and `cli/*` are **shared with the baseline**. PR 5 touches the
same subject matter as `model.py` — fitting, artifacts, scoring — so the
temptation to extend `model.fit`/`save`/`load` is real and must be refused.
**The 1.1 fitter and artifact are new modules.** `model.py` keeps writing
`heads.npz` and `thresholds.json` for the baseline; the 1.1 artifact writes
neither.

**Standing constraint specific to PR 5: the models ship *not evaluated*.**
`SCIENCE.md` §Legitimization Scoring and §Enablement Scoring both require it
absent approved per-outcome criteria, and `PREREGISTRATION_LE_STRUCTURE.md` §7
restates it. No number PR 5 produces is a benchmark result, a generalization
estimate, or a quality claim — every one of them is a dev-set number under
[D-66](DECISIONS.md#d-66) on out-of-version labels under
[D-63](DECISIONS.md#d-63). A session that finds itself writing "the model
achieves…" has left PR 5's scope.

**Standing constraint: D-68 is a null result.** No candidate beat the
incumbent; on L the selected structure scored *below* it (0.4336 vs 0.4840). It
was selected because the higher-scoring candidates cannot emit the three-class
distribution `SCIENCE.md` requires. **Building it is not evidence it is good**,
and PR 5's disclosures must not read as though selection implied validation.

## 2. What already exists, and what PR 5 actually has to do

Read this before starting any slice.

| PR 5 work item | Status |
|---|---|
| Write the pre-registration first (D-59) | **Done.** `PREREGISTRATION_LE_STRUCTURE.md`, executed to completion by queue item 2 (D-68). PR 5 does not re-open it; a departure is an §8 amendment |
| Compare candidate structures on the fixed evaluation set | **Done — and not to be redone.** §5's touch budget and D-66 reserve any re-selection for a real evaluation set with a re-issued pre-registration |
| Select the best-supported structure | **Done (D-68).** `L1 · W1 · S1 · H3 · V1 · P1`, both targets |
| Train on working text produced by the preceding components | **Open — this is gate G-1.** The selection was fitted on raw `response_text` (`experiments/features.py`), not on pipeline `working` text. `SCIENCE.md` requires the latter |
| Cover naive and attacked prompts | **Not met, and not fillable ([D-65](DECISIONS.md#d-65)).** Recorded shortfall; already in D-47's inventory |
| Exclude the prompt ([D-60](DECISIONS.md#d-60)) | **True by construction.** No candidate takes prompt text, enforced by `candidates.py`'s import assertion and by stage 8 reading a response-derived view only |
| Train and version models separately from scoring; lock the model version per run | **Half built.** `RunContext.component_selections` records implementation + version and `views.py` carries it; the *artifact* half is slice B — the 1.1 artifact does not exist yet ([D-49](DECISIONS.md#d-49) deferred it here) |
| Return a provisional L judgment **and a three-class distribution** when L applies; the same for E on every evaluated hazard | **Not built.** `BaselineTwoHeadScorer` sets `distribution=None` by design (§4 — never synthesized). Slice C is the first implementation that fills it |
| Do not apply fixed exceptions or result tables inside either model | **True by construction, and enforced.** `candidates.py::_assert_no_fixed_rule_import` parses its own source at import; slice A must carry that assertion into the production module, not leave it behind in `experiments/` |
| Evaluate each outcome separately and with equal importance | **Slice D.** `experiments/comparison_metrics.py` has the selection metric; per-outcome reporting with uncertainty is what PR 5 owes |
| Report a component as not evaluated absent ground truth or criteria | **Slice D + E.** §1's standing constraint |

**What exists in `experiments/` and what that is worth.**
`MultinomialSoftmax` in `src/hazard_classifier/experiments/candidates.py` is the
selected structure, already correct in three ways worth preserving exactly:
per-hazard cells, `heads.py`'s standardization convention (mean/std over fit
rows, scale floored at `1e-6`), and D-45's unfittable-is-unavailable handling
(a single-class cell is `unavailable`, never substituted). It is **not**
production code: it holds live estimator objects, has no serialization, and
lives in a module whose purpose was a comparison that is now closed.

**Do not import `experiments/` from production code, and do not delete it.**
It is the record of how D-68 was reached and its tests pin that record; the
production module is a separate implementation that must be shown to agree with
it (slice A's equivalence test).

## 3. Entry gate — answered

> **G-1 and G-2 were decided by Kurt on 2026-08-05 and absorbed into
> `PREREGISTRATION_LE_STRUCTURE.md` before any code**, as the entry gate
> requires. **G-1: fit on pipeline working text** ([D-72](DECISIONS.md#d-72)).
> **G-2: fit split only** ([D-73](DECISIONS.md#d-73)). **G-3 remains open** and
> blocks only the close. Nothing below is live work except G-3 — read G-1 and
> G-2 as the record of what was decided and why, not as questions to re-derive.
> **A session starts at slice A.**

Per `META_PLAN.md` §3, these were stopped on rather than chosen.

### G-1 — Which text are the 1.1 models fitted on? — **answered: working text**

> **Decided 2026-08-05 (Kurt), locked as [D-72](DECISIONS.md#d-72) and absorbed
> into `PREREGISTRATION_LE_STRUCTURE.md` §1, §7 and §8 before any code.** Fit on
> the `working` view stages 1–7 produce; **the selection is not re-run**, and
> that its ranking survives the change of input view is a recorded assumption,
> now listed in §7 as something the procedure did not establish. The rest of
> this section is the evidence behind that call.

`SCIENCE.md` §Legitimization Training and §Enablement Training both say the
model "is trained on human ground truth using **working text filtered through
the preceding components**." `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 restates it.
**The selection that produced D-68 did not do this**: `experiments/features.py`
embeds `response_text` directly, with no decoding pass and no prompt-repetition
removal. The pre-registration does not mention text at all — §1 names the
source CSV and the split, §2.1's hard constraints cover the estimator and the
prompt but not the input view — and §7's disclosure list does not carry it.

So the structure was chosen on one feature set and the release would ship a
model fitted on another. The three options:

1. **Fit on pipeline-produced working text.** `SCIENCE.md` governs on a
   behavioral conflict (`META_PLAN.md` §1.1), and this is the only option that
   closes the train/serve gap. Cost: D-68's comparison was measured on
   different features, so the selection transfers by assumption rather than by
   measurement. Recorded as a `PREREGISTRATION_LE_STRUCTURE.md` §8 amendment
   and a §7 disclosure line.
2. **Fit on raw `response_text`.** Reproduces the selected configuration
   exactly. Cost: a standing shortfall against a `SCIENCE.md` training
   requirement, joining D-65 in D-47's inventory — and a real train/serve skew,
   since every scored row at serve time has had repetition removed.
3. **Re-run the selection on working-text features.** Cleanest scientifically,
   and **the most expensive**: 28 fits, and it spends comparison budget the
   pre-registration deliberately fixed (§2.4 forbids adaptive expansion; §5
   reserves re-selection for a real evaluation set).

**Recommendation: option 1, and slice 0's measurement (§4) now supports it on
both sides of the trade.**

- **The cost of option 1 is near zero.** Refitting on working text loses no
  rows (0 exhaust), deletes almost nothing (8 rows of 859 lose a span, median
  reduction 0.0%), and disturbs no per-hazard balance (the change is even
  across all 15 hazards). The transfer of D-68's selection to slightly
  different features remains an assumption — that is real, and it is what the
  `PREREGISTRATION_LE_STRUCTURE.md` §8 amendment records — but the features
  differ by decoding, not by content removal, and no comparison on the ladder
  turned on the input view.
- **The cost of option 2 is not near zero.** A third of rows are decoded at
  serve time, and the decoded forms are semantically different text —
  leetspeak and obfuscation rendered into English. A model fitted on the raw
  form has never seen the form it will be asked to score, on 285 of 859 rows.
  Same length is not same embedding.
- **Option 3 is not justified by this measurement.** Re-running the selection
  buys certainty about a transfer whose risk the numbers show to be bounded,
  and spends a budget `PREREGISTRATION_LE_STRUCTURE.md` §2.4 and §5 fixed
  deliberately.

**Still Kurt's call**, because the assumption in option 1 is a scientific one
and `META_PLAN.md` §3 reserves those. What has changed is that it is now a
decision with numbers under it.

### G-2 — Fit split, or all 859 rows? — **answered: fit split only**

> **Decided 2026-08-05 (Kurt), locked as [D-73](DECISIONS.md#d-73) and absorbed
> into `PREREGISTRATION_LE_STRUCTURE.md` §1 and §5.** The artifact ships fitted
> on the fit half alone — 635 rows for E, 563 for L — and the dev slice stays
> held out, so slice D's numbers describe the model that ships.

`PREREGISTRATION_LE_STRUCTURE.md` §1 divides the data 635/224 (E) and 563/200
(L, after excluding `prv`/`sxc_prn` under phase A). Two defensible answers:

- **Fit split only.** The dev numbers slice D reports then describe *the
  artifact that ships*. Recommended: it is the only option under which PR 5's
  reported numbers and PR 5's shipped model are the same object, and 224 dev
  rows are already thin enough without also being unrepresentative.
- **All 859 rows.** More data for a model whose per-hazard cells are ~42 rows
  each, at the cost that no reported number describes the shipped artifact and
  D-66's dev slice is consumed.

Either way the artifact manifest records which, and slice D's report states it
in the same sentence as every metric.

### G-3 — How is PR 5's first exit criterion discharged? *(blocks only the close)*

"The selected models meet approved per-outcome criteria on evaluation rows
excluded from fitting" **cannot be met in 1.1** — approved criteria are Ask B,
and D-63 established the Standards team's inputs are not arriving. This is the
same shape as D-54's and D-55's scoping of PR 4's criteria, and it needs the
same treatment: **a ledger entry** recording that the criterion is met by
scoping rather than by building, what replaces it (per-outcome dev-class
metrics with uncertainty, reported as *not evaluated*), and its reversal scope.
Recommended as a new entry at the close, drafted in slice E.

## 4. Slice 0 — Measure the train/serve text delta

> **Complete** (2026-08-05), run early and out of order because G-1 blocks
> slice A and the measurement is cheap. `scripts/probe_working_text_delta.py`
> is committed and reproducible. **The result, on all 859 interim rows:**
>
> | | rows | |
> |---|---:|---|
> | working text identical to `response_text` | 568 | 66.1% |
> | **differs** | **291** | **33.9%** |
> | — decoding (stage 2) rewrote the text | 285 | |
> | — repetition removal (stage 4) removed a span | **8** | 0.9% of all rows |
> | — differs but **same length** (normalization only) | 266 | |
> | **exhausts** (working empties, stages 1–7) | **0** | |
>
> Median and p90 character reduction on changed rows are **0.0%**; the maximum
> is 23%. The change is spread evenly across all 15 hazards (15–25% of each),
> which matters because the fit is per hazard.
>
> **How to read it.** The two risky failure modes are both absent: **nothing
> is deleted** (8 rows lose a span; median reduction zero) and **nothing
> exhausts**, so every row the selection was fitted on is a row the evaluator
> would actually score — refitting on working text costs no data and no
> per-hazard balance. What is *not* small is decoding: a third of rows are
> rewritten, and the rewrites include leetspeak and obfuscated jailbreak text
> rendered into plain English. A frozen BGE encoder represents those very
> differently even at identical length, so "same length" must not be read as
> "same features". **That asymmetry is the finding** — it is why the gap is
> cheap to close and expensive to leave open, and it is what §3's G-1 should
> be decided on.

**Small, and it exists to answer G-1 with a number** (lesson: compute, then
write). No production code.

- Commit `scripts/probe_working_text_delta.py`, in the shape of
  `scripts/probe_disclaimer_scope.py`: reproducible, documented, quotable.
- For all 859 interim rows, run the real stages 1–7 the pipeline would run
  (`Decoder`, `PromptRepetitionDetector`, and the placeholders, which change
  nothing) against the row's own prompt and response, and compare
  `texts.working` with `response_text`. Report: rows where the two differ; the
  distribution of character-length deltas; rows that **exhaust** (working text
  empties, so the row would never reach stage 9 at all); and the same figures
  broken down by hazard, since the fit is per hazard.
- Exhausted rows are the sharp end: a row that exhausts at serve time is
  decided by phase B1 and never scored, but it still carries a human L/E label
  that a naive fit would train on. Report the count and say plainly whether
  such rows should be excluded from fitting — a question for G-1's answer.
- Use `interim_data.load_interim()`. The frame carries `prompt_uid`, `hazard`,
  `prompt_text`, `response_text`, `legitimization_value`,
  `enablement_value`, `prompt_group_id`, and `split` — confirmed against the
  loader, so stages 1–7 can be driven per row with no embedding pass and no
  network. The whole probe is pure Python and should run in seconds.

**Exit:** the numbers exist, are committed and reproducible, and G-1 is
presented to Kurt with them. **Stop here.**

## 5. Slice A — The production fitter

> **Complete** (2026-08-05). **576 tests, zero regressions**,
> `test_baseline_parity.py` unchanged (D-48). Four new modules, none of them
> touching `model.py`, `heads.py`, or any other baseline module:
>
> | Module | What it is |
> |---|---|
> | `evaluator/training/multinomial.py` | D-68's estimator and the fitted, **pure-NumPy** model it produces. No component import, no text, no live estimator after `fit` |
> | `evaluator/training/features.py` | The serve-time feature path: the real stages 1–7 produce `working`, the real stage 8 embeds and pools it |
> | `evaluator/training/release.py` | `fit_release_models()` — the fit half, the L eligibility rule, and `FitProvenance` |
> | `evaluator/no_fixed_rules.py` | `candidates.py`'s import guard, carried into production |
>
> **The equivalence claim is verified, not stated.** On the real fit split's
> working-text features — 768-dimensional, all 28 cells — the production
> fitter and `experiments.candidates.MultinomialSoftmax` agree to
> **`max|diff| = 0.0` on both targets**, with identical unavailable-cell
> sets. That is what makes "we shipped what was selected" checkable, and it
> is why `experiments/` is not deleted.
>
> **The real fit, run once end to end** (~2.5 min on CPU, one BGE pass):
> 635 feature rows, **0 exhausted**; **E: 635 rows, 15 cells**; **L: 563
> rows, 13 cells** (`prv`/`sxc_prn` excluded by eligibility, not by
> failure); **no unavailable cell on either target**, and **every cell saw
> all three classes**, so the absent-class path §5 warned about is real code
> on a case this data does not contain. Rows per cell run 33–93 (`hte` is
> the outlier) — the ~42 the pre-registration predicted.
>
> **Two things a later slice should know.**
>
> 1. **Exhausted rows are excluded from fitting, and the exclusion is
>    counted** (`FitProvenance.exhausted_excluded`). A row whose working text
>    empties in stages 1–7 is decided by `SCIENCE.md` phase B1 and never
>    reaches stage 9, so fitting on its human label would train on text no
>    model ever scores. Slice 0 measured **zero** such rows, so this changes
>    no number today; it is implemented because a fit that silently trained
>    on unscoreable rows would be invisible in every output.
> 2. **The suite went from ~23 s to ~40 s.** `test_evaluator_training_release.py`
>    runs stages 1–7 over the real 635-row fit split (with a stub encoder) to
>    check D-73's row counts and the L exclusion as *behavior* rather than as
>    prose. That is the cost of testing the release's central row-selection
>    claims against the real split; it is not accidental.

Build to D-68 and `PREREGISTRATION_LE_STRUCTURE.md` §6. New module —
suggested `src/hazard_classifier/evaluator/training/multinomial.py` or a
top-level `le_model.py`; do not extend `model.py` (§1).

- **Fit on the working-text view, on the fit split only** — G-1's and G-2's
  answers, now `PREREGISTRATION_LE_STRUCTURE.md` §1. Two practical
  consequences:
  - **A fresh embedding pass is required.** `experiments/features.py`'s cache
    is keyed on the exact content embedded (`_content_sha256`), so passing
    working text is a cache miss and re-embeds automatically rather than
    silently reusing the raw-text vectors — the cache is safe here, but the
    pass costs one BGE run over the rows and needs the model already cached
    locally (`allow_download=False`, D-6). Do it once, outside any fit loop.
  - **The split labels are `"train"`/`"eval"`, not `"fit"`/`"dev"`.**
    `interim_data.load_interim(split="train")` is the fit half the
    pre-registration calls *fit*; `"eval"` is what it calls the *dev* slice.
    The vocabularies differ and the code's wins — mixing them silently fits
    on the held-out rows, which is the one mistake D-73 exists to prevent.
- **Fit per `(target, hazard)` cell**, both targets, exactly the estimator
  D-68 selected. **Reproduce `MultinomialSoftmax` parameter for parameter** —
  `LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs",
  random_state=DEFAULT_SEED, max_iter=1000)`, standardization by fit-row
  mean/std with scale floored at `1e-6`, uniform sample weights (`W1`). A
  different regularization or a dropped `class_weight` is **a different model
  from the one that was selected**, however reasonable it looks.
- **L excludes `prv` and `sxc_prn`** (`PREREGISTRATION_LE_STRUCTURE.md` §1;
  `SCIENCE.md` phase A makes final L `N/A` there). Use
  `interim_data.legitimization_rows`.
- **D-45's rule, re-implemented here because per-hazard cells force it.** A
  cell with fewer than two present classes is **unavailable**, recorded as
  such, never substituted by a pooled or neighbouring fit. Record the fitted
  cell set explicitly — §6's `H3` row requires the artifact to record which
  `(target, hazard)` cells were fit.
- **Carry the fixed-rule import assertion into production.**
  `candidates.py::_assert_no_fixed_rule_import` is the mechanism that makes
  "no candidate applies a `SCIENCE.md` fixed rule" checkable by running the
  code. The production fitter and scorer must not import
  `evaluator.components.integration`, and the assertion should say so.
- **Equivalence test against the experiment implementation.** On the same rows,
  same features, same seed, the production fitter's `predict_proba` must agree
  with `experiments.candidates.MultinomialSoftmax` to floating-point tolerance.
  This is the only thing that makes "we shipped what was selected" a verified
  claim rather than a stated one, and it is why `experiments/` is not deleted.

**Traps:**

- **The absent-class column.** `LogisticRegression.classes_` omits a class
  never present in a cell's rows; `MultinomialSoftmax` places columns by class
  label and leaves the absent one at `0.0`. Production must do the same and the
  artifact must record each cell's fitted class set — otherwise a reloaded
  model silently mis-orders its columns. **A distribution with a hard zero is a
  disclosure item** for slice D: the model cannot predict a class it never saw.
- Do not "improve" the estimator. Any change is a departure from D-68 and needs
  an §8 amendment with its reason, not a commit message.

**Exit:** the production fitter reproduces the selected structure, agrees with
`experiments/` numerically, records unavailable cells, and is tested
independently of scoring (PR 5 exit criterion: "fitting and scoring are
independently testable"). 433 + n tests green.

## 6. Slice B — The 1.1 artifact

> **Complete** (2026-08-05). **600 tests, zero regressions**,
> `test_baseline_parity.py` unchanged. `evaluator/artifact.py` is a **new
> writer and a new reader**, not a branch on `model.save`/`model.load`.
>
> ```
> <artifact>/
>   manifest.json      identity, embedding, components, rule version, training provenance
>   rules.json         families, the frozen supported set, the frozen rule constants
>   model/
>     cells.json       which (target, hazard) cells were fit, and each cell's class order
>     legitimization.npz
>     enablement.npz   coef (n_features, 3), intercept (3,), mean, scale
> ```
>
> **No `thresholds.json`** — not written, and `load_artifact` **rejects** an
> artifact that has one, so §6's "retained only for `L3`" is enforced rather
> than remembered. **No pickle**: the payload loads under
> `allow_pickle=False`, and a static test asserts no module under
> `evaluator/` imports `pickle`, `joblib`, or `dill`.
>
> **The round trip is checked as behavior**, not as parsing: a loaded model
> must produce **identical distributions** to the model that was written,
> and the provenance record must compare equal. Deferring the reader's test
> to PR 6 would have meant shipping a writer with no reader.
>
> **Two things the plan did not anticipate, both real.**
>
> 1. **The manifest records the components that produced the training
>    text** — each stage's implementation, version, and maturity.
>    `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 carries a standing obligation
>    ("three of those components are placeholders… **a re-fit is owed
>    whenever any of them is built**"), and until now nothing made it
>    *checkable*. Comparing an artifact's training component set against a
>    run's says exactly where a re-fit is owed. §10's "component
>    implementations and versions" is the field; the training-time reading of
>    it is what makes it load-bearing.
> 2. **`rules.json`'s two family sets are written in full, not narrowed to
>    the supported hazards** — the opposite of what the baseline's
>    `model.save` does. They are the *frozen rule constants* a run's
>    `RuleSet` is rebuilt from, and narrowing silently reclassifies a hazard
>    outside the intersection as `default`: the one family whose L/E table
>    **requires** a Legitimization judgment. `hazard_family` is the separate
>    per-artifact record and *is* keyed by the supported set, which is
>    derived from the fitted cells and never supplied (D-57).
>
> **What is committed, and what is not.**
> `tests/golden/evaluator_1_1/artifact` is the golden fixture §6 asks for —
> 768-dimensional, real BGE, fitted on `examples/sample_input.csv`'s twelve
> synthetic rows, and **named a fixture in its own `artifact_id` and
> `split_role`** so nothing can mistake it for a model of anything.
> `tests/golden/capture_evaluator_1_1.py` recaptures it and an integration
> test proves the committed copy still reproduces from current code.
> `scripts/build_release_artifact.py` builds the **real** artifact (876 KB,
> 15 supported hazards, 28 cells, ~2.9 min) into gitignored `artifacts/`;
> whether one ships is PR 6's promotion call (D-58), not slice B's.
>
> **Left to slice C, deliberately:** the `profile.resolve_artifact` branch.
> `artifact.is_evaluator_artifact()` is the dispatch test (the baseline
> manifest has no `format` key, so the formats are told apart by a field
> rather than by guessing at directory contents), but wiring it changes
> `build_registry`'s scorer construction — which is slice C's subject.

`ARCHITECTURE.md` §10 and `PREREGISTRATION_LE_STRUCTURE.md` §6 are the
specification. **This is the deliverable [D-49](DECISIONS.md#d-49) deferred
into PR 5**, and PR 6 round-trips it.

- `model/` — per target and per fitted cell: coefficient matrix
  `(n_features, 3)`, intercept `(3,)`, and the standardization `mean`/`scale`
  vectors, in `.npz`. **Class order per cell in JSON.**
- `manifest.json` — artifact id and version, embedding provider name/version,
  pooling strategy, component implementations and versions, rule version, and
  **training provenance**: the source SHA-256, the split file and its version,
  which split half was fitted on (G-2), the text view fitted on (G-1), and the
  seed. PR 5's exit criterion "runs reproduce results from locked model, rule,
  data, split, and metric versions" is met by this field set or it is not met.
- `rules.json` — hazard families, the artifact's supported hazard set, frozen
  rule constants. [D-23](DECISIONS.md#d-23): serve time reads the artifact,
  never installed config. The supported set is what [D-57](DECISIONS.md#d-57)
  makes `hazard_scope` default to, so it must contain exactly the hazards with
  at least one fitted cell.
- **No `thresholds.json`.** §6: retained only for `L3`. A writer that emits an
  empty one is wrong, not harmless.
- **No pickle, no `joblib`** ([D-37](DECISIONS.md#d-37)). The reader
  reconstructs pure-NumPy scoring; nothing unpickles an estimator.
- Commit a small **golden 1.1 artifact** fixture next to
  `tests/golden/baseline/artifact`, trained on a synthetic fixture, so
  integration tests have something to load without fitting.

**Traps:**

- The baseline's `model.save`/`model.load` are shared code (§1). Write a new
  writer/reader; do not add a branch to the old one.
- Round-tripping is PR 6's exit criterion, but **a load-what-you-saved test
  belongs here** — deferring it to PR 6 means shipping a writer with no reader.

**Exit:** an artifact writes, loads, and scores identically before and after a
round trip; no `thresholds.json`; no pickle anywhere; manifest carries the full
provenance set.

## 7. Slice C — The scoring component

> **Complete** (2026-08-05). **628 tests, zero regressions**,
> `test_baseline_parity.py` unchanged. `MultinomialPerHazardScorer`
> (`multinomial_per_hazard`, **working**) sits alongside
> `BaselineTwoHeadScorer` (`baseline_two_head`, still **partial**, still
> registered — it remains the only implementation exercising §4's
> `distribution=None` path).
>
> **Verified end to end on the real artifact**, not only on fixtures:
> `hrc-run` over interim dev rows with `artifacts/release_1_1_le` produced
> real distributions for both targets, `argmax` labels, and phase C firing
> correctly — e.g. an `spc_lgl` row whose provisional L was `L1`
> (0.137/0.863/0.001) and whose **final** L was fixed at `L0` with
> `decided_by == "C"`, the provisional judgment and its distribution
> untouched. That is §7's second trap, observed rather than argued.
>
> **What the maturity flip did and did not buy.** Stage 9 is `working` in
> `ARCHITECTURE.md` §7 row 9, and "L/E scoring's absent distribution" is out
> of D-47's inventory in `RELEASE_1_1_QUEUE_PROPOSAL.md`, `README.md`, and
> `ARCHITECTURE.md` §7's prose count (which is back to **three** partials —
> it has now been wrong in both directions, and the section says so). **Both
> models are still *not evaluated***: that follows from having no approved
> per-outcome criteria, which no maturity field can supply.
>
> **The wiring slice B left here.** `profile.resolve_artifact` now loads
> either format, dispatching on the 1.1 manifest's `format` field, and
> `build_registry` selects stage 9's implementation **from the artifact**
> rather than from a flag — the other scorer has no model in that artifact to
> score with, so the mismatch is unrepresentable instead of a per-row failure.
> `ResolvedRun.classifier` is renamed `artifact`, since it is a
> `HazardResponseClassifier` only half the time now.
>
> **One PR 5 work item slice C surfaced and could not close alone — now
> closed.** `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 inherits from PR 7's sweep:
> *"Record every per-hazard `ComponentError` the scoring stage produces, not
> just the first."* The new scorer had the same shape as the old one because
> **the constraint was never the component's** — `ComponentObservation.error`
> was a single `ComponentError | None` in `ARCHITECTURE.md` §4. Slice C
> raised it under `STATUS.md` §Awaiting User rather than amending a
> specification inside a slice (`META_PLAN.md` §3); **Kurt accepted, and it is
> locked as [D-76](DECISIONS.md#d-76) and built** —
> `errors: tuple[ComponentError, ...]` across all ten components,
> `views.failure_rows` searching every error, and
> `views.RESULT_VIEW_VERSION` bumped 1 → 2 because `results.jsonl`'s shape
> changed. **628 tests.** It was an auditability gap and never a wrong result:
> `HazardJudgment.failure_reason` remains the authoritative per-hazard text
> and phase D writes it for every failing hazard.
>
> **Not done here, and correctly so:** `README.md`'s per-outcome reporting.
> §8 owns replacing that paragraph with numbers; slice C corrected only what
> the flip made *false* ("the scorer shipping today is not the selected
> structure yet"), leaving the reporting to slice D.

Replace stage 9's implementation. New class alongside `BaselineTwoHeadScorer`,
new `implementation` id (`multinomial_per_hazard`), **registered rather than
substituted** — §6's registry keys on `(stage, implementation_id)` and PR 7's
runner selects by id.

- **Keep `BaselineTwoHeadScorer` registered.** It is the only implementation
  that exercises the `distribution=None` path §4 specifies, PR 1–PR 4's tests
  select it, and removing it would make a component contract untested.
- Emit `Judgment(label=..., distribution=(p0, p1, p2), model_version=...)`,
  label by **`argmax` over the distribution** (§6: every non-`L3` candidate
  decides by argmax; there are no thresholds to apply).
- **Unavailable cells produce a per-hazard `ComponentError`**, exactly as the
  baseline scorer does through `resolve_component_action` — the integrator's
  phase D turns it into a per-hazard failure. Never a substituted judgment,
  never a uniform distribution (§6's no-fallback rule; D-45's principle).
- `legitimization_applies` stays the enablement-only test it is today; the
  scorer makes no applicability *decision*, it reports what it judged.
- **Stage 9's maturity becomes `working`** in `ARCHITECTURE.md` §7 row 9 — and
  when it does, **the "L/E scoring's absent distribution" entry added to D-47's
  inventory on 2026-08-05 comes out** (`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6
  narrowing 2, which names it as the one inventory item with a scheduled end).
  Removing it is part of this slice, not an afterthought.
- A real, non-mocked BGE test extending `tests/integration/test_evaluator_real_bge.py`,
  as PR 2, PR 3, and PR 4 each did: a real encoder, the 1.1 golden artifact, a
  well-formed three-class distribution that sums to 1.

**Traps:**

- The distribution must survive `views.py` into `results.jsonl` as a list of
  three floats (`_judgment_view` already handles it) — assert it, since this is
  the first implementation for which that branch is live.
- Phase C fixes final L at L0 without touching the distribution. The
  *provisional* judgment and the *final* label are different fields and a
  disclaimer must not rewrite the former.

**Exit:** stage 9 emits real three-class distributions for both targets,
unavailable cells fail their hazard rather than inventing a judgment, and the
maturity flip and inventory removal both land.

## 8. Slice D — Evaluation and reporting

What PR 5 owes that is not code: per-outcome numbers that cannot be mistaken
for a benchmark.

- **Each outcome separately** — L0, L1, L2, E0, E1, E2 — per-class recall,
  precision, and F1. A single accuracy figure does not satisfy the
  equal-importance requirement, because a rare class hides inside it
  (`STATUS.md` §Standards team, Ask B).
- **Every figure carries an uncertainty estimate and the method that produced
  it** (`SCIENCE.md` §Evidence and outputs, Estimability;
  `PREREGISTRATION_LE_STRUCTURE.md` §3). Cluster bootstrap over
  `prompt_group_id`, seeded, the same discipline the disclaimer probe uses.
- **Per-hazard claims are weak by construction** — ~15 dev rows per hazard
  (§7). Report intervals, never point estimates, and say so.
- **The words "not evaluated" appear next to the numbers**, not in a footnote.
  Both models are reported as *not evaluated* whatever the figures show.
- **Do not build `metrics.json` as a shipped view here.** `views.py` records
  that it needs approved criteria and the approved uncertainty method, and only
  one of the two blockers clears with PR 5. PR 5 produces the report; whether a
  view ships is PR 6's call alongside the promotion decision (D-58).
- `README.md` §Release 1.1 evaluator status: replace the "the scorer shipping
  today is also not the selected structure yet" paragraph (added 2026-08-05)
  with what actually ships, keeping D-68's null-result framing intact.

## 9. Slice E — Verification sweep and PR 5 close

`META_PLAN.md` §6: **Opus, high effort, and prefer a fresh context** that did
not write the specifications being checked. Not bookkeeping — PR 2's, PR 3's,
and PR 4's sweeps each found real gaps on checks predicted to be clean.

- Full suite green, including `tests/integration/test_baseline_parity.py`
  (D-48). PR 5 writes a *new* artifact format and must not perturb the old one.
- **Map each PR 5 exit criterion to what verifies it** (§10's table), and record
  every criterion met by scoping with a ledger entry — G-3's entry at minimum.
- **Re-check D-68's, D-49's, and D-37's absorption against what shipped**, and
  the pre-registration §6 payload row against the actual `.npz`.
- **The D-47 inventory, item by item.** PR 5 both removes an item (stage 9's
  absent distribution) and may add one (G-1's answer, if option 2). Three
  consecutive sweeps have found staleness here; expect a fourth.
- `PREREGISTRATION_LE_STRUCTURE.md` §7 gains whatever PR 5 learned that the
  selection could not establish; §8 gains an amendment if G-1 chose option 1.
- `STATUS.md`: each slice in Recently Completed, new assumed-concurrence rows
  **with reversal scope**, this plan marked as a record of what was built.
- **Do not close item 4** unless PR 5 is genuinely the last PR standing — check
  the queue rather than assuming, since PR 5's position may have moved.

## 10. Exit criteria → how each is verified

| PR 5 exit criterion | Verified by |
|---|---|
| The selected models meet approved per-outcome criteria on evaluation rows excluded from fitting | **Cannot be met in 1.1** — approved criteria are Ask B, not arriving (D-63). G-3's ledger entry records the scoping; slice D's per-outcome dev-class report with uncertainty is what replaces it, under the not-evaluated rule |
| All three L outcomes and all three E outcomes are evaluated separately | Slice D's per-class metrics with cluster-bootstrap intervals |
| Fitting and scoring are independently testable | Slice A's fitter tests (no pipeline, no record) and slice C's component tests (loaded artifact, no fitting); the golden 1.1 artifact is what decouples them |
| Runs reproduce results from locked model, rule, data, split, and metric versions | Slice B's manifest provenance set + slice C's `component_selections` recording; a same-input-same-output test |
| No AI-only labels are presented as human ground truth | True by construction — every label is Jailbreak v1.0 human judgment (D-63); D-65 records that naive coverage was **not** manufactured, which is the same rule applied |

## 11. Explicitly out of scope for PR 5

- **Re-running or re-opening the structure selection.**
  `PREREGISTRATION_LE_STRUCTURE.md` §5 and D-66 reserve that for a real
  evaluation set with a re-issued pre-registration. G-1 option 3 is the one
  narrow exception a session may *propose*, never take unilaterally.
- **Fine-tuning an encoder, or changing the representation.** §2.1's hard
  constraint and §2.3's single-level Representation axis.
- **Building narrative, refusal, or hazard detection** to close the train/serve
  gap PR 5's work list names (D-54). The re-fit those components owe is a
  future release's.
- **Editing `model.py`, `heads.py`, or any baseline module** (D-48), including
  "just adding a multinomial branch" to `save`/`load`.
- **Shipping `metrics.json`** — §8.
- **The promotion decision** (D-58) and the standalone limitations document
  (D-47) — PR 6's.
- **The runner and CLI** — PR 7's, and PR 5 does not need them.

## 12. Lessons carried forward

1. **Read the code, not just the docs about the code**
   (`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 6). G-1 exists because
   `experiments/features.py` was read against `SCIENCE.md`'s training
   sentence. Four PRs' worth of specification review had not surfaced it.
2. **Compute, then write** (§10 lesson 2). Slice 0 exists so G-1 is answered
   with a measurement instead of an argument.
3. **A decision that reaches no specification is not settled** (§10 lesson 4).
   G-1's answer must land in `PREREGISTRATION_LE_STRUCTURE.md` §7/§8 and the
   artifact manifest, not only in a commit message.
4. **Beware the component that runs, returns results, and looks healthy**
   (§10 lesson 5). A multinomial always returns three numbers that sum to 1,
   including for a cell fitted on 40 rows of two classes. The distribution
   being well-formed says nothing about it being right.
5. **A null result stays null.** D-68 selected a structure that lost to the
   incumbent on L. Every disclosure PR 5 writes must keep that visible;
   shipping is not validation.
6. **One queue item per session; retire by number** (§10 lesson 7). PR numbers
   and queue-item numbers are different schemes.
7. **End with Open Questions, even if empty** (§10 lesson 9, `META_PLAN.md` §3).

## 13. When a slice raises something this plan did not anticipate

`SCIENCE.md` governs on any behavioral conflict; `ARCHITECTURE.md` on any
structural one; `PREREGISTRATION_LE_STRUCTURE.md` on anything about the
selection. Per `META_PLAN.md` §3: below ~90% confidence, or in conflict with a
specification, or a tradeoff only Kurt can make — stop and add it to **Awaiting
User** rather than choosing.

The specific risk in this PR: **a session that finds the selected structure
performing poorly will be tempted to fix it.** Tuning regularization, adding a
class weight, pooling hazards with thin cells — each is a new selection made
without a pre-registration, on a dev set, after seeing the labels. That is the
exact failure §2.4 and §5 exist to prevent. Record the finding; do not act on
it.

## Open Questions

**One open, and it blocks only the close.** Two of the three were answered on
2026-08-05 and absorbed the same day, before any code — the order the entry
gate requires. Recorded here because a fresh session's first instinct on
finding a settled question in a plan is to re-derive it.

| Question | Answer | Where it now lives |
|---|---|---|
| **G-1** — fit on pipeline `working` text, on raw `response_text`, or re-run the selection? | **Working text.** The selection is *not* re-run; that its ranking survives the change of view is a recorded assumption. Slice 0 bounded the risk: 8 of 859 rows lose any text, none exhaust, the difference is overwhelmingly decoding rather than deletion — while *not* refitting would leave 285 rows scored in a decoded form the model never saw | [D-72](DECISIONS.md#d-72); `PREREGISTRATION_LE_STRUCTURE.md` §1, §7, §8; slice A |
| **G-2** — fit split, or all 859 rows? | **Fit split only** — 635 rows for E, 563 for L. The dev slice stays held out, so slice D's numbers describe the artifact that ships rather than a differently-fitted sibling | [D-73](DECISIONS.md#d-73); `PREREGISTRATION_LE_STRUCTURE.md` §1, §5; slice B's manifest, slice D's framing |
| **G-3** — how is the approved-criteria exit criterion discharged? | **Open.** It cannot be met (D-63). Scoping a stated exit criterion requires a ledger entry with reversal scope, as D-54/D-55 did for PR 4 | A new `DECISIONS.md` entry, drafted in slice E |

Nothing else in PR 5 is open. The structure, the payload format, the data, the
split, the input view, and the not-evaluated reporting rule are all settled by
D-68, D-63 through D-66, D-72, D-73, and `SCIENCE.md` — and none of them should
be re-derived.
