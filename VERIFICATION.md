# Verification Plan — confirming every locked decision

**Purpose.** A durable collection of the checks that together confirm all 28
locked decisions in `DECISIONS.md` actually compose and are correctly built.
This is the master backlog; `STATUS.md`'s thin queue pulls a few items from here
at a time (META_PLAN §5), one per session. See `META_PLAN.md` for the process.

**Two item types (META_PLAN §2 / §4):**
- **IC-n — Integration check** (paper, cross-decision): confirms decisions
  *compose*. Cheap, but has no ground truth to falsify against, so used only for
  genuinely cross-cutting orderings. Most are already done (see below).
- **IS-n — Implementation slice** (code + a failing-first test): the real forcing
  function. A red-then-green test proves whether decisions compose in a way no
  amount of re-reading can. **Preferred** — per META_PLAN §4, this is where the
  remaining confirmation should happen, not more paper review.

---

## Current implementation state (2026-07-25, updated after IS-A, IS-C, IS-B, IS-C2, IS-C3, IS-1 through IS-11, `embed.py`, and the D-35 CLI skin)

**Every implementation slice in this backlog is now done, including IS-9**
(closed 2026-07-25 as satisfied by adjacent real data, D-34 — the toy's own
literal reference-number match was superseded, not achieved; see IS-9's own
entry below) **and the D-35 CLI skin** (`hrc-train`/`hrc-evaluate`/
`hrc-predict`, landed as three ordered queue items — see each command's own
notes below). **This closes the entire backlog: every locked decision
(D-1 through D-35) now has a landed implementation. Nothing remains
queued.**

- **Built + green (125 tests, `pytest` passing — all but 3 need no network,
  3 integration tests need it on first run only, model cached after):**
  - `schema.py` — **new, IS-1 landed.** `normalize_hazard` (D-27, ported
    verbatim from the toy) and `load_csv` (mode-scoped required columns —
    D-24 predict/D-26 evaluate/train; train-only optional `known_hazards`
    rejection, D-27; ordinal-label `{0,1,2}` range check on
    `enablement_value`/`legitimization_value` only, never on blank values,
    never at all in predict mode). 14 tests in `tests/unit/test_schema.py`,
    including two forcing functions verified by deliberate sabotage (not just
    reading the code): (1) a case-variant hazard code (`"SPC_FIN"`) stays
    genuinely distinct from `"spc_fin"` under train's `known_hazards`
    rejection, confirming no lowercasing; (2) an evaluate-mode row with an
    **unrecognized hazard and a blank ground-truth label together** does
    **not** raise — the schema-layer half of D-26's Finding-A fix, proving
    `schema.py` never promotes a blank label to a run-abort even when it
    cannot confirm the hazard is known. Sabotage-tested the range-check logic
    directly (temporarily widened the accepted value set in an isolated
    process) and confirmed the two range-check tests go red under the
    sabotaged version — not vacuous passes.
  - `preprocess/decode.py`, `segment.py`, `flags.py` — **new, IS-2 landed.**
    See the IS-2 entry below for full detail (20 new tests).
  - `heads.py` — **new, IS-3 landed.** `BinaryHead` dataclass + `fit_binary_head`
    (standardize/logistic/centering, D-7). See the IS-3 entry below for full
    detail (7 new tests).
  - `model.py` — **new, IS-4 through IS-11 landed (every implementation
    slice in this backlog, including IS-9, is now landed or closed).**
    `fit`/`choose_holdout_seed_prompts` (cell enumeration,
    D-1/D-4/D-5/D-7/D-18/D-2/D-10, IS-4); `save`/`load` (artifact I/O,
    D-1/D-6/D-13/D-23/D-27/D-28, IS-5); the D-28 train-time gate
    (`WhollySkippedEnablementError`/`warnings.warn`, IS-6); `score_row`/
    `HardFailError`/`ScoredRow` (the predict/evaluate scoring pipeline —
    D-3/D-4/D-11/D-19/D-20/D-21/D-27, IS-7); `evaluate_rows`/
    `BlankGroundTruthError` (the `hrc-evaluate` metric assembly —
    D-13/D-14/D-15/D-16/D-17/D-26, IS-8); `predict_rows`/
    `to_predictions_frame`/`to_failures_frame` (the `hrc-predict` batch split
    — D-22/D-25, IS-10); `HazardResponseClassifier.score`/`PredictRow`/
    `RowResult` (the batch Python API — D-23/D-31, IS-11). See the IS-4
    through IS-11 entries below for full detail
    (6 + 4 + 3 + 6 + 6 + 6 + 2 = 33 new tests). **Not built here:** the
    actual `hrc-train`/`hrc-evaluate`/`hrc-predict` argparse CLIs + file I/O
    (`metrics.csv`/`summary.txt` rendering).
  - `embed.py` — **new (2026-07-25, user-directed, following the IS-9
    blocker below).** `embed_sentences` (real `BAAI/bge-base-en-v1.5` via
    `sentence-transformers`, CPU-only, D-6; `_load_model` is
    `functools.lru_cache`-wrapped so `score`'s "BGE model loaded once"
    requirement, IS-11, is real, not just a docstring claim),
    `enablement_keep_mask`/`pool_response_vector` (mean pooling + the
    Enablement prompt-repetition drop, ported from the toy's
    `aggregate_for_response`/`effective_indices`). `torch`/
    `sentence-transformers` added to `pyproject.toml`. `DEFAULT_MODEL_NAME`
    now sources from `config.DEFAULT_EMBEDDING_MODEL_NAME` (moved there,
    IS-11, so `model.py` can reference the default model without pulling in
    `torch`/`sentence-transformers` for callers who never touch real
    embeddings). 5 no-network unit tests (pooling logic) + 3
    `tests/integration/` tests (network needed on first run only, model
    cached after — this is why they're `tests/integration/`, not
    `tests/unit/`, per `PLAN.md` §8.1's "unit tests need no model download"
    rule): the original mechanism test (`preprocess/*` → `embed.py` →
    `fit`/`save`/`load`/`score_row` end-to-end) plus two new IS-11 tests
    (below). **This proves the pipeline's mechanism works, not that it
    matches the toy's science** — see IS-9 below for why those are different
    claims right now.
  - `rules.py` — `ordinal_prediction`/`optimize_ordinal_thresholds` (D-9/D-10
    monotonicity gate, 5 tests); `is_required_component`/
    `resolve_component_action` (D-18 + D-3/D-4/D-5/D-11/**D-20** predict
    resolution, truth table verified as a real forcing function — **D-20's
    absent/invalid-required-cell fail-closed case landed IS-A**; **D-23's
    frozen-source requirement landed at the unit level, IS-C** — both
    functions now take `enablement_only_hazards` as a required parameter,
    never importing installed config).
  - `rules.py` — `ordinal_prediction`/`optimize_ordinal_thresholds` (D-9/D-10
    monotonicity gate, 5 tests); `is_required_component`/
    `resolve_component_action` (D-18 + D-3/D-4/D-5/D-11/**D-20** predict
    resolution, truth table verified as a real forcing function — **D-20's
    absent/invalid-required-cell fail-closed case landed IS-A**; **D-23's
    frozen-source requirement landed at the unit level, IS-C** — both
    functions now take `enablement_only_hazards` as a required parameter,
    never importing installed config).
  - `metrics.py` — `partition_by_holdout` (D-13), `legitimization_eligible_mask`
    (D-15, and **D-23's frozen-source requirement landed at the unit level,
    IS-C2** — mirrors `rules.py`'s IS-C exactly), `component_metrics` (D-16
    high-head AUC enforced structurally, and now returns **`n` per D-17's
    DI-Q4 amendment, landed IS-B** — the caller's existing pre-filtering via
    `legitimization_eligible_mask` makes Enablement's `n` = `n_rows` and
    Legitimization's `n` = `n_rows` minus enablement-only rows automatically,
    with no new hazard-family logic added to the function itself),
    `final_label_metrics` (D-17 safe=1 + specialized-advice exclusion, and now
    **D-23's frozen-source requirement landed at the unit level, IS-C3** —
    same pattern, `specialized_advice_hazards` required, no default). **This
    module no longer imports `hazard_classifier.config` at all** — every
    hazard-family lookup across `metrics.py` now takes its set as an explicit,
    required caller-supplied parameter. This closes out the IS-C → IS-C2 →
    IS-C3 chain of same-pattern findings this session's D-23 work surfaced.
  - `config.py` — `ENABLEMENT_ONLY_HAZARDS`, `SPECIALIZED_ADVICE_HAZARDS`
    (still the source of the *values* used to build frozen-set test fixtures
    and, eventually, the artifact's `rules.json` at train time — D-23 governs
    the *serve-time* source only, per D-23's own §4 Touches: "at *train* time
    the installed config is what gets frozen").
- **Built + green (D-35, 2026-07-25, 142 tests total):** the
  argparse/console-script CLIs for all three commands — `src/
  hazard_classifier/cli/__init__.py`, `_common.py` (`add_allow_download_flag`,
  `fatal`, `warn_if_skipped_components` — the D-28 load-time warning
  `PLAN.md` §5/§6 required but nothing had built until this slice),
  `train.py`, `evaluate.py`, `predict.py`, plus `metrics.csv`/`summary.txt`
  rendering (`metrics.py`'s new `flatten_metrics_report`/`render_summary`).
  `pyproject.toml` gained `[project.scripts]`;
  `examples/sample_input.csv` was created for §8.1's mocked-BGE CLI smoke
  tests. The shared step every CLI uses — `embed.build_component_features`
  — was extracted from `HazardResponseClassifier.score`'s prior inline
  implementation (D-35's own architecture choice) so all three CLIs and
  `score` share one pipeline, not four independent copies. Verified beyond
  the mocked unit tests for all three commands: real, non-mocked runs via
  the installed console scripts against the real cached BGE model, output
  files inspected by hand each time. §10 Phase 0 (`embed.py`) and the
  file-I/O/argument-parsing skin around Phases 3-5 are both now fully
  built and tested — **nothing remains unbuilt in this project.**
- **IS-C/IS-C2/IS-C3's full-artifact-wiring half (IS-5), D-19/D-20/D-21's
  scoring-path wiring (IS-7), and D-13/D-14/D-15/D-17's metric-assembly
  wiring (IS-8) are all closed now:** a real save→load round-trip confirms
  frozen-set reads; `score_row` composes the fail-closed predicate, the
  disclaimer rule, the gate, and v1.4/v14 into one pipeline (IC-1(a) trace);
  `evaluate_rows` composes `score_row` with `metrics.py`'s already-built
  functions into the exact `metrics.json` shape, with the exclude-before-
  partition and blank-label-abort orderings D-14/D-26 require confirmed by
  forcing-function tests, not just by reading the code.
- **This session's earlier Awaiting-User finding was resolved by the user
  (D-29, "leave the natural ValueError as-is").** **IS-8 raised and resolved
  a second one in the same pass** (not a pause, since the user answered
  immediately): `is_safe_ground_truth`'s literal encoding — an Open Question
  since IS-1 that became a hard blocker once `evaluate_rows` needed to
  actually parse it — was asked directly and locked as **D-30**
  (`"safe"`/`"unsafe"`, case-sensitive exact match).
- **Three fix-in-passing findings this pass, none a new decision:**
  (1) IS-6: two pre-existing IS-4/IS-5 tests used a single-class-
  **Enablement** fixture to exercise D-5's skip marking; IS-6's gate made
  that fixture raise instead — switched to single-class-**Legitimization**.
  (2) IS-7: `HazardResponseClassifier` had no `specialized_advice_hazards`
  field — IS-5's `save` froze it but never read it back; added the field, a
  matching `fit` parameter, and `load` support. (3) IS-8: `score_row`'s
  `ScoredRow` had no way to report the business-rule-**adjusted high**
  probability D-16's AUC needs (only the discrete prediction and the
  combined score) — added `enablement_adjusted_high`/
  `legitimization_adjusted_high` fields, populated alongside the existing
  ones, with a new IS-7 test confirming the disclaimer rule zeroes this
  value too, not just the ordinal prediction.
- **IS-9 blocked on missing data, not missing code (2026-07-25):** attempting
  IS-9 surfaced that the toy's raw labeled CSVs and its BGE hazard-weighted
  run's output directory are **not present anywhere in this environment**
  (`security-evaluator/inputs/README.md` explicitly excludes them from the
  repo: "provide the files at run time"). The reference numbers themselves
  are real (in the toy's `README.md`) but there is no input data to
  reproduce a run from. User directed building `embed.py` now (done — see
  above) and explicitly deferring the actual parity confirmation until real
  labeled data becomes available. **IS-9 remains genuinely open, not just
  unstarted** — it cannot be completed in this environment as it stands.
- **No known code gaps remain** in any built module (`schema.py`,
  `preprocess/*`, `heads.py`, `model.py`, `rules.py`, `metrics.py`,
  `config.py`, `embed.py`) as of this pass. **Every implementation slice in
  `VERIFICATION.md`'s backlog is done except IS-9**, which is blocked on
  real data that does not exist in this environment, not on unwritten code.
  What remains, precisely: the actual `hrc-train`/`hrc-evaluate`/
  `hrc-predict` argparse CLIs + file I/O (a thin wrapper around
  already-built, already-tested logic) and IS-9's real parity confirmation
  (needs real labeled data to materialize). There is no more paper-review
  work queued — from here, further confirmation is either building the CLI
  skin or waiting on data.
- **Packaging fix, found while adding `schema.py`'s pandas dependency:**
  `pyproject.toml` was missing `pandas` entirely and had `scikit-learn` listed
  only under the `dev` extra, even though `metrics.py` (shipped, non-test code)
  already imports `sklearn.metrics` directly — `pip install
  hazard-response-classifier` (without `dev`) would have failed to import.
  Fixed: both are now main dependencies.
- **Ledger correction, found while implementing `schema.py`:** `DECISIONS.md`
  D-26's Finding-A amendment (point 4) and the matching `PLAN.md` §2.1 prose
  had a drafting slip — "any non-blank value in [the three ground-truth
  columns] must be in `{0,1,2}`" read as applying the ordinal range check to
  `is_safe_ground_truth` too, which isn't an ordinal. Corrected in both files
  (D-26 gets a correction note, not a rewrite); `schema.py` implements the
  corrected scope (range-checks only `enablement_value`/`legitimization_value`,
  checks `is_safe_ground_truth` for column presence only). **New Open
  Question surfaced, not resolved:** `is_safe_ground_truth`'s literal string
  encoding (`"safe"`/`"unsafe"`? `"True"`/`"False"`? `"1"`/`"0"`?) is not
  pinned by any locked decision or by the toy (which carries it through as an
  opaque, unparsed string). Needed before any code parses it into a boolean
  (`hrc-evaluate`'s `is_safe_true`, `final_label_metrics`'s first argument) —
  flagged for a future fix-proposal, not guessed at here.

---

## Coverage matrix (decision → confirming item → status)

| Decision | Confirming item(s) | Status |
|---|---|---|
| D-1 holdout excluded from fit; default 0 | model.py ✓ (**IS-4 landed**: default-0 → empty list; forcing fn — corrupting holdout-only rows/labels doesn't change the fit; **IS-5 landed**, manifest round-trip) | **green (unit)** |
| D-2 in-sample threshold/centering bias | model.py ✓ (**IS-4 landed**, `n_own>=5` cliff ported); IS-9 (closed via adjacent data, D-34 — the toy-parity numeric comparison this row originally named stays unresolved, superseded not achieved) | **green (unit); toy-parity comparison superseded (D-34)** |
| D-3 fail-closed on unknown/unfit cell | rules.py ✓ ; model.py ✓ (**IS-7 landed** — `score_row` raises `HardFailError`, forcing fn) | **green (unit)** |
| D-4 empty/echo-only excluded; per-component predict 0 | rules.py ✓ ; model.py ✓ (**IS-4 landed**, fit-time exclusion via `component_effective` mask; **IS-7 landed**, predict-time `"score_zero"` path) | **green (unit)** |
| D-5 whole-component skipped trigger | model.py ✓ (**IS-4 landed** — falls out of `heads.py`'s per-cell degeneracy check automatically since every hazard's fit shares the same row-level labels; forcing fn: single-class labels → every cell skipped) | **green (unit)** |
| D-6 CPU-only; determinism | model.py ✓ (**IS-5 landed**, bit-identical save→load round-trip); IS-1 (no --device, already true — no `--device` flag exists) | **green (unit, round-trip)** |
| D-7 standardization stats net of D-1/D-4; Legit ex-enablement-only | IS-3 ✓ (mean/scale identical across hazard weightings; row-set determines mean/scale, forcing fn); model.py ✓ (**IS-4 landed** — Legit's actual enablement-only row-set exclusion now wired via `is_required_component`, forcing fn confirms identical mean/scale across hazards through the full `fit()` call) | **green (unit)** |
| D-8 class_weight wart documented | IS-9 (closed via adjacent data, D-34 — parity comparison superseded) + README note | not built |
| D-9 / D-10 monotonicity gate | test_threshold_optimizer ✓✓ | **green** |
| D-11 predict precedence split | test_predict_resolution ✓ (forcing fn) | **green** |
| D-12 no `--cv` | `cli/evaluate.py` ✓ (**D-35 landed** — no `--cv` flag exists) | **green (paper decision, confirmed by absence)** |
| D-13 evaluate auto-partition + warning | test_metrics ✓ ; model.py ✓ (**IS-5 landed**, manifest field round-trip; **IS-8 landed**, `evaluate_rows` partitions + warns, forcing fn) | **green (unit)** |
| D-14 exclude hard-fail before partition | model.py ✓ (**IS-8 landed** — `HardFailError` caught, tallied, excluded before partitioning, forcing fn incl. Finding A) | **green (unit)** |
| D-15 Legit metrics ex-enablement-only | test_metrics ✓✓ ; model.py ✓ (**IS-8 landed**, `evaluate_rows` applies `legitimization_eligible_mask`, forcing fn) | **green (unit)** |
| D-16 retain probs; high-head AUC; provenance | test_metrics ✓ ; model.py ✓ (**IS-7/IS-8 landed** — `ScoredRow.*_adjusted_high` feeds `component_metrics`'s `high_prob` directly); IS-9 (closed via adjacent data, D-34 — Finding B's provenance question, which needed the toy's exact reference numbers, stays unresolved) | **green (unit); Finding B provenance question superseded, not resolved (D-34)** |
| D-17 safe=1; schema; excluded counts; per-comp `n` | test_metrics ✓ (incl. **IS-B landed**, forcing fn); model.py ✓ (**IS-8 landed** — full `metrics.json` shape assembled, shape test) | **green (unit)** |
| D-18 Legit not required for enablement-only | test_predict_resolution ✓ ; model.py ✓ (**IS-4 landed** — no `(legitimization, prv)` cell enumerated, forcing fn) | **green (unit)** |
| D-19 business-rule stage; disclaimer rule | rules.py ✓ ; model.py ✓ (**IS-7 landed**, `score_row` — IC-1(a) trace + forcing fn) | **green (unit)** |
| D-20 absent required cell fails closed | rules.py ✓ (**IS-A landed**, forcing fn); model.py ✓ (**IS-7 landed**, wired into `score_row` via `resolve_component_action`) | **green (unit)** |
| D-21 v14 side-output; label-independent | rules.py ✓ ; model.py ✓ (**IS-7 landed**, forcing fn: hand-constructed cell where the two disagree) | **green (unit)** |
| D-22 predict split outputs, no abort | model.py ✓ (**IS-7 landed** — `HardFailError` rather than aborting; **IS-10 landed** — `predict_rows` splits into predictions/failures, every row in exactly one, forcing fn); `cli/predict.py` ✓ (**D-35 queue item 3 landed** — real console-script run confirmed) | **green (unit + real run)** |
| D-23 frozen `rules.json`, not config | rules.py ✓ (**IS-C**), metrics.py ✓✓ (**IS-C2**, **IS-C3**), model.py ✓ (**IS-5 landed** — real save→load round-trip, forcing fn; **IS-11 landed** — `embedding_model_name`/`revision` also frozen + round-tripped, same principle applied to the BGE model choice) | **green — closed end-to-end, all call sites + artifact wiring, incl. embedding model** |
| D-24 seed_prompt_id required; GT optional predict | schema.py ✓ (**IS-1 landed**, forcing fn: predict ignores out-of-range GT values entirely) | **green (unit)** |
| D-25 predict CLI; failures.csv columns | model.py ✓ (**IS-10 landed** — `PREDICTIONS_COLUMNS`/`FAILURES_COLUMNS` exact, no `seed_prompt_id`, empty-batch header confirmed via real file write/read-back); `cli/predict.py` ✓ (**D-35 queue item 3 landed**) | **green (unit + real run)** |
| D-26 evaluate CLI; GT required; blank-label (Finding A) | schema.py ✓ (structural half **landed, IS-1**); model.py ✓ (**IS-8 landed** — per-row family-aware `BlankGroundTruthError` abort, forcing fn incl. Finding A; also locked `is_safe_ground_truth`'s encoding as **D-30**, a blocking Open Question since IS-1); `cli/evaluate.py` ✓ (**D-35 queue item 2 landed** — `fatal()` on `BlankGroundTruthError`, forcing-fn test) | **green (unit + real run)** |
| D-27 normalization; rules.json=trained; unified lookup | schema.py ✓ (**IS-1 landed**, `normalize_hazard` ported verbatim + train-mode rejection, forcing fns); model.py ✓ (**IS-5 landed** — `rules.json` key set = trained hazards exactly, forcing fn; **IS-7 landed** — `score_row`'s `hazard in trained_hazards` check is the unified lookup) | **green (unit)** |
| D-28 wholly-skipped surfaced train/load | model.py ✓ (**IS-6 landed** — Enablement hard-fails via `WhollySkippedEnablementError`, Legitimization warns+writes, forcing fns); model.py ✓ (**IS-5 landed** — `skipped_components` rollup round-trips and matches per-cell status across files); `cli/_common.py` ✓ (**D-35 queue item 1 landed** — `warn_if_skipped_components`, called by both `evaluate.py`/`predict.py`, direct unit tests in `test_cli_common.py`) | **green (unit, train-time gate + manifest + load-time warning)** |
| D-29 hrc-train raises natural error on blank GT | ratifies IS-4's existing behavior; no code | **green (paper decision only)** |
| D-30 `is_safe_ground_truth` = `"safe"`/`"unsafe"` | schema.py ✓ (**IS-8 landed**, `parse_is_safe_ground_truth`); model.py ✓ (`evaluate_rows` uses it directly) | **green (unit)** |
| D-31 `score(rows)` never raises; per-row entries | model.py ✓ (**IS-11 landed** — `RowResult`, forcing fn: mixed batch never raises) | **green (integration)** |
| D-32 `rule_reasons` string for D-4 zero, not D-18 | model.py ✓ (`score_row`'s `score_zero` branch, forcing fn: isolated single-string test + IC-1(a) coexistence assertion) | **green (unit)** |
| D-33 `qwk` reports `null` when undefined | metrics.py ✓ (`_safe_qwk`, forcing fn: reuses the `auc`-undefined single-class fixture) | **green (unit)** |
| D-34 IS-9 closed via adjacent real data | `scripts/run_real_data_is9.py` ✓ — real end-to-end run against 859 real rows; toy-parity comparison itself explicitly superseded, not resolved | **green (real-data run); toy-literal-parity not achieved** |

---

## Integration checks (paper) — mostly already done this session

- **IC-1 — Predict-path ordering, all three hazard families** (Step 0 D-27 → Step 1
  D-3/D-11 → Step 2 D-4 → Step 3 D-5/D-20 → D-19 business rules → D-10 gate →
  v1.4/D-21). **DONE** (D-25–D-28 consistency audit + the D-19–D-24 check's (a)
  trace). The `default`/`specialized_advice`/`enablement_only` families each
  compose. **Re-confirmed in code (IS-7):** the specialized-advice +
  disclaimer + Enablement-repetition-only trace passes end-to-end through
  `score_row`, not just on paper.
- **IC-2 — D-19–D-24 mutual + whole-ledger.** **DONE** —
  `critiques/2026-07-25-integration-d19-d24.md`. No conflict.
- **IC-3 — D-26 blank-label × D-14/D-22/D-23/D-27.** **DONE** — Finding A,
  `critiques/2026-07-25-decisions-consistency.md`.
- **IC-4 — AUC provenance/parity D-2/D-16/D-10/DR-4.** **DONE (paper)** — Finding
  B. The *empirical* half was folded into **IS-9**, which computed both AUCs
  against a real dataset (2026-07-25) but never against the toy's own
  reference numbers — **IS-9 closed via D-34 with this specific comparison
  superseded, not resolved.**
- **IC-5 — the three denominators coexist (D-15/D-17/D-18):** `n_rows` /
  `components.legitimization.n` / `final_label.n`. **DONE (paper)** + partly in
  `test_metrics`; the `n` field itself is **IS-B**.
- **IC-6 — fit-time row-set consistency (D-1/D-4/D-7/D-18):** which rows enter
  each component's `mean`/`scale`/`center_mean`/heads. **OPEN**, but better
  falsified by **IS-3/IS-4** than by more paper.

The ledger's cross-decision consistency is now well-covered on paper. **Remaining
confirmation is overwhelmingly implementation slices** (META_PLAN §4).

---

## Implementation slices

### Do now (no new pipeline required — operate on already-built code)

- **IS-A — D-20 fail-open fix.** **DONE (2026-07-25).**
  `resolve_component_action` returned `"serve"` for `cell_status=None` on a
  required/known/scoreable row. Fixed to fail closed on any non-`"fit"` value
  (allow-list, not deny-list) — flipped `if cell_status == "skipped": fail;
  else: serve` to `if cell_status == "fit": serve; else: fail`. Two truth-table
  rows added to `test_predict_resolution.py` (`cell_status=None` and an
  arbitrary invalid string on a required/known/non-empty row), confirmed
  **red** (`serve`) before the fix, **green** after (41 tests total). See
  `DECISIONS.md` D-20's 2026-07-25 "Implementation slice landed" note.
- **IS-B — D-17 per-component `n` field.** **DONE (2026-07-25).**
  `component_metrics` now returns `"n": len(y_true)`. Rather than adding new
  hazard-family logic to the function, this relies on the caller's *existing*
  pre-filtering — `legitimization_eligible_mask` is already applied upstream
  before scoring Legitimization (confirmed by the pre-existing D-15
  integration test) — so Enablement's `n` (given the full population)
  naturally equals `n_rows`, and Legitimization's `n` (given the masked
  subset) naturally equals `n_rows` minus the enablement-only-hazard row
  count, exactly per D-17's DI-Q4 amendment, without `component_metrics`
  itself needing to know *why*. New test,
  `test_component_metrics_n_reflects_the_passed_row_count` (mixed-hazard
  fixture: `hte, prv, sxc_prn, spc_lgl, hte`): confirmed `KeyError: 'n'`
  **red** before the change, then confirmed `legitimization.n < enablement.n`
  by exactly the `prv`/`sxc_prn` row count (43 tests total, up from 42). See
  `DECISIONS.md` D-17's 2026-07-25 "Implementation slice landed" note.
  **Remaining, not done here:** the actual `metrics.json` assembly (IS-8) that
  surfaces this `n` in the output schema.
- **IS-C — D-23 frozen-source refactor, `rules.py`.** **DONE, unit level
  (2026-07-25).** `is_required_component` and `resolve_component_action` no
  longer import `ENABLEMENT_ONLY_HAZARDS` from `hazard_classifier.config` —
  both take it as a required `enablement_only_hazards` parameter, **no
  default**, so a caller cannot silently fall back to config by omitting the
  argument. Forcing-fn test
  (`test_is_required_component_uses_the_passed_set_not_installed_config`):
  passes a frozen set that disagrees with installed config in both directions
  and confirms the passed set's answer wins, not config's (42 tests total, up
  from 41). See `DECISIONS.md` D-23's 2026-07-25 "Implementation slice landed,
  partially" note. **Remaining, not done here:** the actual **wiring** of a
  real artifact's frozen `rules.json` into the caller still needs
  `model.py`/artifact load (§10 Phase 3, IS-5) — this slice only proves the
  functions *can* take an external source and prefer it over config, not that
  a real artifact supplies one yet.
- **IS-C2 — D-23 frozen-source refactor, `metrics.py`
  `legitimization_eligible_mask`.** **DONE (2026-07-25).** Had the identical
  pattern to IS-C: imported `ENABLEMENT_ONLY_HAZARDS` from installed config to
  decide Legitimization-eligible rows (D-15, mechanized by D-18) for
  `hrc-evaluate`'s reporting. Fixed the same shape as IS-C: now takes
  `enablement_only_hazards` as a required parameter, **no default**. Confirmed
  the signature change broke the three existing call sites first
  (`TypeError: missing 1 required positional argument`) before updating them.
  Forcing-fn test
  (`test_legitimization_eligible_mask_uses_the_passed_set_not_installed_config`,
  mirrors IS-C's) confirms a frozen set disagreeing with installed config in
  both directions wins over config (44 tests total, up from 43). See
  `DECISIONS.md` D-23's second 2026-07-25 "Implementation slice landed,
  partially" note. **Remaining, not done here:** the artifact-wiring half
  (IS-5), same as IS-C.
- **IS-C3 — D-23 frozen-source refactor, `metrics.py` `final_label_metrics`.**
  **DONE (2026-07-25).** Had the identical pattern to IS-C/IS-C2: imported
  `SPECIALIZED_ADVICE_HAZARDS` from installed config directly to exclude
  specialized-advice hazards from the final-label headline (D-17 point 3).
  Fixed the same shape: `final_label_metrics` now takes
  `specialized_advice_hazards` as a required parameter, **no default**.
  Confirmed the signature change broke all four existing call sites first
  (`TypeError: missing 1 required positional argument`) before updating them.
  Forcing-fn test
  (`test_final_label_metrics_uses_the_passed_set_not_installed_config`,
  mirrors IS-C/IS-C2's) confirms a frozen set disagreeing with installed
  config in both directions wins over config (45 tests total, up from 44). See
  `DECISIONS.md` D-23's third 2026-07-25 "Implementation slice landed" note.
  `src/hazard_classifier/metrics.py` no longer imports
  `hazard_classifier.config` at all — **this closes the IS-C → IS-C2 → IS-C3
  chain**: no hazard-family-set config import remains anywhere in `rules.py`
  or `metrics.py` (confirmed by grepping `src/` for any
  `from hazard_classifier.config import` outside `config.py` itself — none
  found). **Remaining, not done here (same as IS-C/IS-C2):** the
  artifact-wiring half — an actual artifact's frozen `rules.json` supplying
  these sets at serve time — still needs `model.py`/artifact load (IS-5).

### Phase 1 — schema + preprocessing

- **IS-1 — `schema.py`.** **DONE (2026-07-25).** `load_csv(path, mode,
  known_hazards=None)` + `normalize_hazard`. Mode-scoped required columns
  (D-24: predict needs only the five core columns, GT optional/ignored
  entirely, not even range-checked; D-26: train/evaluate require all eight).
  `normalize_hazard` ported verbatim (D-27: strip + `-`→`_`, no lowercase).
  Train-only optional `known_hazards` rejection (D-27) — raises if passed for
  evaluate/predict, rather than silently no-op'ing a caller's mistaken
  expectation. Ordinal-label `{0,1,2}` range check on
  `enablement_value`/`legitimization_value` only (a drafting slip in D-26's
  amendment had this loosely covering `is_safe_ground_truth` too — corrected
  in `DECISIONS.md`/`PLAN.md` this pass; `is_safe_ground_truth` gets
  column-presence-only validation, its literal encoding being an unpinned
  Open Question). Never rejects a *blank* ground-truth value at this layer,
  regardless of hazard — the family-aware judgment stays deferred to IS-8
  per D-26's Finding-A amendment. 14 tests in `tests/unit/test_schema.py`
  (59 total). Two things verified as genuine forcing functions, not just
  read: the case-variant-stays-distinct claim (train's `known_hazards`
  rejects `"SPC_FIN"` against a lowercase known set) and, more importantly,
  **the Finding-A forcing function at the schema layer** — an evaluate-mode
  row with a genuinely unrecognized hazard *and* a blank ground-truth label
  does **not** raise, proving `schema.py` can never promote a blank label to
  a run-abort even when it cannot confirm the hazard is known at all (the
  full "excluded, not aborted" guarantee needs IS-8's per-row `rules.json`
  check, which this slice doesn't build, but schema.py's half of the
  guarantee is confirmed). Also sabotage-tested the range-check logic itself
  (temporarily widened the accepted value set in an isolated process) and
  confirmed the two range-check tests go red — not vacuous. Packaging fix
  alongside: `pyproject.toml` gained `pandas` (new dependency) and moved
  `scikit-learn` from `dev`-only to a main dependency (it was already
  imported by shipped `metrics.py`, a pre-existing packaging bug found while
  touching the file). **Not built here:** `preprocess/*` (IS-2, below) —
  genuinely separate in size (the toy's equivalent file is ~1000 lines of
  deobfuscation/segmentation logic) and scope from schema validation, so
  deliberately not combined into this slice.
- **IS-2 — `preprocess/*`. DONE (2026-07-25).** Ported the toy's
  `build_reviewable_sentence_segments.py` (~1000 lines) into three pure-function
  modules per `PLAN.md` §2.2's package layout:
  - `decode.py` — `normalize_unicode`, `english_score`, `printable_text`,
    `parse_mapping_candidates`, `translate_chars`/`wordwise_translate`,
    `rot13`, `decode_escape_sequences`, `decode_base64_tokens`,
    `best_readable_view`. `COMMON_WORDS`/`DOMAIN_WORDS`/`SIGNAL_TERMS`/
    `CORE_WORDS` ported verbatim as literal sets (same values, not derived).
  - `segment.py` — `is_probable_code`, `identifier_to_words`,
    `literal_summary`, `code_to_english_segments`, `chunk_text`,
    `segment_text`. Segments are returned as a `Segment` `NamedTuple`
    (`text, start, end, segment_type`) instead of the toy's raw 4-tuples —
    readable field access, same positional/iteration behavior, no value
    changes.
  - `flags.py` — `wrapper_label`, `disclaimer_label` (`WRAPPER_PATTERNS`/
    `DISCLAIMER_PATTERNS` ported verbatim), `prompt_repetition_features` (+
    `normalize_for_repetition`/`content_words`/`find_repetition_source_span`/
    `normalized_word_windows`/`find_normalized_window_span` helpers),
    `later_authored_continuation`.

  **Bundled wordlist (D-6-adjacent, `PLAN.md` §7):** user was asked which
  source to bundle (a genuine license/size tradeoff, not mine to pick
  silently per META_PLAN §3) and chose a filtered snapshot of this
  machine's `/usr/share/dict/words` (macOS's `web2`, Webster's Second
  International base) over a small MIT-licensed alternative. Filtered with
  the toy's own predicate (lowercased, `fullmatch [a-z]{2,}`, deduplicated):
  234,428 entries, ~2.4MB, at
  `src/hazard_classifier/preprocess/data/wordlist.txt`, provenance recorded
  in the adjacent `WORDLIST_PROVENANCE.md` (including the unresolved caveat
  that the exact redistribution terms of this specific file were not
  independently re-verified — flagged there, not silently assumed).
  `pyproject.toml` gained `[tool.setuptools.package-data]` for
  `hazard_classifier.preprocess = ["data/*.txt"]`; confirmed by an actual
  `python -m build --wheel` that `data/wordlist.txt` lands in the built wheel,
  not just the editable install.

  **Deliberately not ported (scoping decision, not an oversight):**
  `signal_score`/`semantic_signal_score` and `text_hash`/`segment_hash`. The
  toy's own docstring calls `semantic_signal_score` "only a triage heuristic
  for surfacing reviewable segments... not a safety label," and grepping
  `scoring_common.py` confirms neither value is read by any modeling/business
  rule path (`segment_hash` is used only by the toy's own embedding-cache
  layer, out of this slice's scope). `PLAN.md` §2.2's `flags.py` line names
  only "prompt-repetition, disclaimer, wrapper flags," not these two — so
  omitting them tracks the plan's own stated scope rather than narrowing it
  silently. If `embed.py` (not yet built or scoped as its own IS-n item)
  later wants a caching key, `segment_hash` is a one-line addition then, not
  a gap now.

  **Tests (20 new, `tests/unit/test_decode.py` / `test_segment.py` /
  `test_flags.py`; 79 total, zero regressions):** ported the toy's six
  existing asserts (base64 decode; code-to-English extraction; the three
  `prompt_repetition_features`/`later_authored_continuation` cases —
  verbatim/decoded, prompt-plus-continuation, topical-overlap-is-not-
  repetition; the toy's `build_segments`-level composition test, reproduced
  by hand since no orchestration function exists yet in this codebase —
  `embed.py` is later phase). Added new tests beyond the ported set: ROT13
  self-inverse; an HTML-entity case constructed to actually flip the
  `best_readable_view` winner (the toy's own literal example, `&amp;`, ties
  on score and loses the length tiebreak to raw text — verified this by
  running it, then picked a numeric-entity example, `&#112;lease`, that
  genuinely wins, so the test is a real forcing function, not a vacuous
  pass); escaped-hex decode; segment offset/index correctness against the
  original text; wrapper/disclaimer true and false cases. **Host-independence
  forcing function:** rather than a source-text grep (which false-positived
  against this module's own docstring, which legitimately discusses
  `/usr/share/dict/words` as the thing being replaced), the test asserts
  structurally that `_load_bundled_wordlist` takes no arguments and no
  toy-style `WORDLIST_PATHS` fallback list exists to redirect it, plus that
  the loaded word set matches the bundled file's contents exactly (not some
  ambient list of a different size).

### Phase 3 — `model.py` fit + artifact

- **IS-3 — `heads.py` `BinaryHead`. DONE (2026-07-25).** Ported the toy's
  `standardize_train_test`/`fit_binary_head_weighted`
  (`run_bge_hazard_weighted_heads.py` L70-110) and `logit`/`sigmoid`/
  `centered_probability` (`scoring_common.py` L412-423) into a
  `BinaryHead` dataclass (`{mean, scale, coef, intercept, center_mean,
  constant_probability, status}`) plus `predict_proba`/`predict_proba_centered`
  methods and `to_arrays`/`from_arrays` for `.npz` round-tripping (§4
  `heads.npz`), per §2.3's refactor. `fit_binary_head(x, y, sample_weight)`
  has **no hazard parameter at all** — confirmed by an explicit
  signature-inspection test — so it cannot itself apply, skip, or
  special-case the Legitimization enablement-only-hazard exclusion (D-7/D-18);
  that exclusion is entirely the caller's job (`model.py`'s `fit`, IS-4),
  which this slice does not build.

  One deliberate implementation choice beyond a literal port, recorded in
  `heads.py`'s own docstring: `center_mean` is computed from
  `BinaryHead.predict_proba`'s own formula (not sklearn's `predict_proba`
  directly, which the toy uses) so a head's centering is always
  self-consistent with what it will later report, even after a save/load
  round-trip — the toy never had to worry about this since it never
  serializes a head and reloads it later.

  7 tests in `tests/unit/test_heads.py` (86 total, zero regressions):
  `logit`/`sigmoid`/`centered_probability` against hand-computed values;
  **mean/scale identical across two hazard-weightings while coef/center_mean
  differ** — using a deliberately *overlapping*, non-class-aligned
  three-hazard-group fixture, not a cleanly-separable one, after confirming
  empirically that a cleanly-separable fixture makes this a vacuous pass (a
  uniform per-class reweighting of separable data selects the same
  max-margin separator regardless of which class is up-weighted — caught by
  actually running it, not assumed); a structural test that
  `fit_binary_head`'s signature is exactly `{x, y, sample_weight, seed}`;
  fitting on a full row set vs. a subset (simulating the D-7/D-18 exclusion)
  changes `mean`/`scale`, proving the caller must filter before calling in;
  degenerate single-class labels produce a `status="skipped"` constant head
  whose `predict_proba_centered` collapses to exactly `0.5` everywhere (since
  `center_mean` equals the constant itself); save→load round-trip gives
  bit-identical `predict_proba_centered` output for both a fit head and a
  skipped head.
- **IS-4 — `model.py` `fit`. DONE (2026-07-25).** Ported the toy's
  per-target-hazard weighted head fit (`run_bge_hazard_weighted_heads.py`'s
  CV-fold loop, L200-306) with the now-dropped grouped-CV apparatus (D-12)
  removed: each `(component, hazard)` cell is fit **once** on the whole
  non-holdout population, not per-fold. Built `src/hazard_classifier/model.py`:
  `choose_holdout_seed_prompts` (D-1, a simplified port of the toy's
  `choose_holdout_seed_prompts` — seed-prompt-level fraction only, without the
  toy's now-irrelevant response-count target tied to its dropped grouped-CV
  apparatus); `fit(df, component_features, component_effective,
  enablement_only_hazards, ...)` — cell enumeration reuses `rules.py`'s
  already-built `is_required_component` (D-18: no `(legitimization,
  enablement-only-hazard)` cell) to construct **the same row-set expression**
  for both the row-required mask and the fit-row mask, so D-18's exclusion and
  D-7's "identical mean/scale across hazards" property share one code path
  rather than two that could drift apart. D-1 (holdout) and D-4 (per-component
  empty/echo, via an explicit `component_effective` boolean mask rather than an
  implicit "all-NaN feature row" convention — safer, since a real bug
  producing NaN features elsewhere is never silently misread as an intentional
  exclusion) combine into the same fit-row mask. D-5's whole-component skip
  **required no new logic at all**: since every hazard's cell fit for a
  component shares the identical row-level label array (only `sample_weight`
  differs), `heads.py`'s own per-call degeneracy check independently produces
  `status="skipped"` for every hazard automatically when the labels are
  truly single-class — confirmed by test, not just inferred. D-10's gated
  grid search and D-2's `n_own>=5` cliff reuse `rules.py`'s
  `optimize_ordinal_thresholds` directly rather than re-deriving it.

  **New layering contract, documented in `model.py`'s own docstring, not a
  locked decision:** `fit` takes already-pooled per-component feature
  matrices and an explicit per-component "has effective sentences" boolean
  mask, not raw text — whichever future slice builds `embed.py`/pooling must
  satisfy this contract; `fit` itself has no BGE/preprocessing dependency, so
  its unit tests need no model download (`PLAN.md` §8.1).

  6 tests in `tests/unit/test_model_fit.py` (92 total, zero regressions):
  default `holdout_seed_fraction=0` → `holdout_seed_prompt_ids == []` (D-1);
  **a genuine forcing function, not just a recorded-list check** — corrupted
  the ground-truth labels *and* features for exactly the held-out rows and
  confirmed refitting produces bit-identical `mean`/`coef`/thresholds,
  proving holdout rows are truly excluded, not just recorded; single-class
  `enablement_value` across both hazards marks **every** enablement cell
  `status="skipped"` and adds `"enablement"` to `skipped_components`, while
  `legitimization` is unaffected (D-5); no `("legitimization", "prv")` cell
  exists for the enablement-only hazard while `("enablement", "prv")` does
  (D-18); `mean`/`scale` identical across every hazard cell of a component
  confirmed **through the full `fit()` call**, not just `heads.py` in
  isolation (D-7); `choose_holdout_seed_prompts` determinism and the
  zero-fraction case directly.

  **New finding, not resolved here (added to Awaiting User):** a blank
  `legitimization_value` on a non-enablement-only hazard training row (a
  genuine data defect — schema.py tolerates blanks generically and doesn't
  reject it at load time) currently surfaces as a raw `ValueError` from
  `int("")` inside `fit`'s label conversion. No locked decision addresses
  this train-time case — D-26 pins the analogous condition for
  `hrc-evaluate` only (error). Flagged rather than guessed at, per META_PLAN
  §3.
- **IS-5 — artifact save/load. DONE (2026-07-25).** Built `model.py`'s
  `save`/`load` against the §4 format: `heads.npz` (every cell's two
  `BinaryHead`s flattened into one namespace via a deterministic
  `_head_array_key(component, hazard, head_type, field)` helper — built and
  rebuilt from `thresholds.json`'s cell list, **never parsed** out of a key
  string, so a hazard code containing an underscore can never be
  ambiguous), `thresholds.json` (`status`, both thresholds, `threshold_metrics`,
  nested `{component: {hazard: {...}}}`), `rules.json` (`trained_hazards`,
  a `hazard_family` map via a new `rules.hazard_family` helper — ported from
  the toy's `hazard_rule_family`, narrowed to this project's two locked
  families since `config.py` doesn't define the toy's `defamation`/
  `content_as_harm`/`cse` ones — and both hazard-family sets intersected with
  `trained_hazards`, D-27), `manifest.json` (`holdout_seed_prompt_ids`,
  `skipped_components`; the fuller manifest — embedding model id/revision,
  hyperparameters, timestamp, training-file hash, §3 step 5 — is deliberately
  deferred to whichever slice wires up the full `hrc-train` CLI, since those
  values don't exist at this layer yet).

  `save` takes `specialized_advice_hazards` as its own parameter, separate
  from `HazardResponseClassifier` itself — `fit`/cell enumeration never uses
  it (D-18 only names the enablement-only set), so threading it through
  `fit`'s signature would add a dead parameter; `rules.json` still needs it
  for D-23's full family map.

  4 tests in `tests/unit/test_model_artifact.py` (99 total after IS-6, zero
  regressions): save→load round-trip gives **bit-identical**
  `predict_proba_centered` output and exactly-equal thresholds for every
  cell (D-6 determinism); `rules.json`'s `hazard_family` key set equals
  `trained_hazards` exactly (D-27); `skipped_components` in `manifest.json`
  matches a from-scratch recomputation over `thresholds.json`'s per-cell
  `status` (D-28) — a genuine cross-file consistency check, not just
  "the field exists"; and the **IS-C-completing** forcing function — froze
  an `enablement_only_hazards` set disagreeing with installed
  `config.ENABLEMENT_ONLY_HAZARDS` in both directions, saved, reloaded, and
  confirmed `is_required_component` fed the *loaded* set disagrees with the
  same call fed installed config, both directions, and that cell enumeration
  itself (not just the boolean check) followed the loaded set.
- **IS-6 — D-28 train-time gate. DONE (2026-07-25).** Built directly into
  `model.py`'s `fit`, immediately after each component's cell-fitting loop
  finishes: a wholly-skipped **Enablement** raises a new
  `WhollySkippedEnablementError` (before Legitimization's loop even starts —
  there's no deployable classifier to keep building toward); a wholly-skipped
  **Legitimization** emits `warnings.warn(..., UserWarning)` and `fit`
  returns normally, `"legitimization"` present in `skipped_components`.
  **Load-time warning (`hrc-predict`/`hrc-evaluate` reading a loaded
  artifact's `skipped_components`) is still not built** — no predict/evaluate
  pipeline exists yet (IS-7/IS-8).

  3 tests in `tests/unit/test_model_train_gate.py` (99 total, zero
  regressions): single-class-Enablement fixture raises
  `WhollySkippedEnablementError`; single-class-Legitimization fixture warns
  (`pytest.warns`) and still produces a classifier with normally-fit
  Enablement cells for every hazard (a genuinely "usable for
  enablement-only-hazard workloads" artifact, not just "didn't crash");
  Legitimization's warning path confirmed non-raising directly.

  **Cross-check finding, fixed in passing, not a new decision:** two
  pre-existing IS-4/IS-5 tests had used a single-class-**Enablement**
  fixture to exercise D-5's per-cell skip-marking mechanism in isolation,
  written before this gate existed — once IS-6 landed, that same fixture
  started raising `WhollySkippedEnablementError` instead of just marking
  cells skipped, and both tests failed. Fixed by switching both to a
  single-class-**Legitimization** fixture instead (D-5's marking mechanism
  is component-symmetric, so the substitution preserves each test's original
  intent without touching D-28's new, stricter Enablement-specific behavior).

### Phase 4 — `hrc-evaluate`

- **IS-7 — predict/evaluate scoring pipeline. DONE (2026-07-25).** Ported the
  toy's `apply_component_business_rules`/`v14_overall_score`/
  `discrete_v14_label`/`score_from_centered_probs` (`scoring_common.py`
  L583-647, L471-472) into `rules.py`'s `apply_legitimization_disclaimer_rule`
  (only the disclaimer rule — the toy's other two are subsumed by D-18/D-4,
  no live call site), `discrete_v14_label`, `v14_overall_score`,
  `combined_component_score` (all taking an already-resolved `HazardFamily`
  rather than re-deriving it from a hazard code, since the caller already
  computed it once for Step 0), and `model.py`'s `score_row` — the single
  per-row pipeline: `resolve_component_action` (already built, D-3/D-4/D-11/
  D-18/D-20, not re-derived) → serve via the frozen heads or D-4's `0.0`
  sentinel → the disclaimer rule (Legitimization + specialized-advice only)
  → `ordinal_prediction`'s monotonicity gate on the **adjusted** probabilities
  (D-19) → the discrete v1.4 label + D-21's continuous side-output.
  `HardFailError` is raised for `fail_unseen_hazard`/`fail_skipped_cell`
  rather than deciding a consequence — that's `hrc-predict`/`hrc-evaluate`'s
  job (D-22/D-14, IS-10/IS-8), sharing this exact predicate.

  6 tests in `tests/unit/test_model_score_row.py` (105 total, zero
  regressions): the **IC-1(a) trace end-to-end** (specialized-advice hazard +
  a disclaimer sentence + Enablement scored via D-4's repetition-only path →
  `predicted_label == "safe"`) through a real `fit()`-trained classifier, not
  a stub; the disclaimer rule's effect isolated from D-4 and proven
  non-vacuous by comparing the same probe with/without a disclaimer sentence
  (the no-disclaimer case predicts something other than the disclaimer-forced
  `0`); a `not_required` component (`legitimization_predicted is None` for an
  enablement-only hazard); `HardFailError` for an unseen hazard and
  separately for a genuinely skipped Legitimization cell (built via a
  single-class fixture, mirroring IS-6's own construction); and **D-21's
  independence property**, tested with a hand-constructed `Cell` (a
  degenerate `BinaryHead` with `center_mean=0.5`, which makes
  `predict_proba_centered` return an exact, fully controlled value —
  centered nonzero `0.6` crosses a `0.5` threshold, centered high `0.3` does
  not) rather than a real fit, since this property needs an exact "crossed
  nonzero but not high" value a real logistic fit can't be guaranteed to
  land on: `discrete_v14_label` says "safe" (only `==2` matters) while
  `v14_overall_unsafe_score` is `0.45` — a real, verified disagreement, not
  an inference from reading the two formulas.

  **Fix found while building this slice, not a new decision:** `HazardResponse
  Classifier` had no `specialized_advice_hazards` field at all — IS-5's `save`
  froze it into `rules.json` correctly but never read it back, and `fit` had
  no parameter to set it, so a loaded artifact's `hazard_family` lookup (which
  `score_row`'s Step 0 and disclaimer rule both need) had no frozen source for
  this second set. Fixed: added the field, a same-shaped `fit` keyword
  parameter (unused for cell enumeration, D-18 only names the
  enablement-only set, but threaded through so the object is self-describing
  after either `fit` or `load`), and `load` now populates it; removed the
  now-redundant parameter from `save`. Updated the three affected IS-5 tests.
- **IS-8 — `hrc-evaluate` metric assembly. DONE (2026-07-25), CLI/file-I/O
  layer deferred.** Built `model.py`'s `evaluate_rows`: per row, calls
  `score_row` (IS-7) and catches `HardFailError`, tallying
  `excluded_unseen_hazard_count`/`excluded_skipped_cell_count` (D-14) and
  `continue`-ing before any ground-truth column is even read — this is what
  makes Finding A (a blank label on an excluded row never aborts) true by
  construction, not by a separate check. For surviving rows, applies D-26's
  family-aware blank-ground-truth validation (a known, non-enablement-only
  hazard's blank column raises a new `BlankGroundTruthError`, aborting the
  whole run per the user's original "error over exclude" choice — a
  **different** consequence from `HardFailError`'s per-row exclusion, and
  deliberately so). Partitions surviving rows via `metrics.py`'s already-built
  `partition_by_holdout` (D-13), warning when `holdout_recorded` is `False`.
  Assembles each non-empty population's report via `metrics.py`'s
  already-built `component_metrics` (Enablement unfiltered, Legitimization
  filtered through `legitimization_eligible_mask`, D-15) and
  `final_label_metrics` (D-17), feeding `ScoredRow`'s new `*_adjusted_high`
  fields as the AUC input D-16 specifies. **Locked D-13's own wording
  literally:** "reported... whenever both are non-empty" is read as *omit* an
  empty population's key entirely rather than emit a hollow, all-null object.

  **Resolved a second Awaiting-User-caliber blocker in this same pass, not a
  pause:** `is_safe_ground_truth`'s literal encoding was an Open Question
  since IS-1, and became a hard blocker here since `final_label_metrics`
  needs it as a boolean. Asked directly, user answered `"safe"`/`"unsafe"`,
  locked as **D-30**; added `schema.py`'s `parse_is_safe_ground_truth`.

  6 tests in `tests/unit/test_model_evaluate.py` (111 total, zero
  regressions): an excluded row **never enters either population**
  (confirmed via `n_rows`, not just the exclusion counters); empty holdout →
  warning + everything in `in_sample_unrecorded`, **no `held_out` key at
  all**; **blank label on an unseen hazard → excluded, not abort** (Finding
  A, the single most important ordering test here); blank label on a known,
  non-enablement-only hazard → `BlankGroundTruthError` (the abort case D-26
  actually requires, proving the two paths — exclude vs. abort — are
  genuinely distinct, not just theoretically); blank Legitimization tolerated
  for an enablement-only hazard, landing at `components.legitimization.n ==
  0`; and the full `metrics.json` shape (exact key sets at every level).

  **Deliberately not built here (an engineering sequencing choice, not a
  locked-decision question):** the actual `hrc-evaluate` argparse entry
  point, `--model-dir`/`--input`/`--output-dir` file I/O, and
  `metrics.csv`/`summary.txt` rendering — building a literal CLI script that
  cannot run against real data yet (no `embed.py`) would be a premature,
  untestable stub; deferred until `embed.py` exists, same reasoning as every
  prior slice's `embed.py` deferral. `--cv` (D-12) needs no code either way
  — it's an absence, not a feature.
- **IS-9 — Parity harness (§8.2)** — the science forcing function for the whole
  stack. Frozen-fit metrics match the toy's held-out reference within tolerance;
  fixture trained with **non-zero** `--holdout-seed-fraction`, compared against
  the `held_out` population (D-2 amendment); **computes both AUCs and matches the
  reference against both** (D-16 note / **Finding B** — settles the provenance);
  monotonicity-gate tolerance (D-10). Confirms D-1/D-2/D-6/D-7/D-8/D-10/D-16 at
  once against real numbers.

  **BLOCKED on missing data, attempted 2026-07-25.** Checked the toy repo
  (`security-evaluator`) directly for what this harness would need: (1) a
  fixed labeled fixture to train on — the toy's raw CSVs
  (`inputs/neyman_review_queue.csv`, `inputs/keys/batch_*_key.csv`) are
  explicitly excluded from the repo (its own `inputs/README.md`: "Do not
  commit source CSV data... provide the files at run time") and are not
  present anywhere in this environment; (2) the toy's actual BGE
  hazard-weighted run's cached output
  (`results/mechanism_sentence_bge_base_hazard_weighted_heads_v1/`) —
  also absent, only a handful of unrelated `results/` subdirectories exist.
  The reference numbers themselves **are** real and confirmed present (the
  toy's `README.md` "Expected Checks" table: Legitimization exact 0.645503 /
  AUC 0.808393 / QWK 0.522552; Enablement exact 0.592040 / AUC 0.782737 /
  QWK 0.411720 — matching `PLAN.md` §8.2's quoted figures exactly), but there
  is no input data to reproduce a run from, and no code fix changes that.

  **User directed, given three options (provide real data / build `embed.py`
  now and defer parity / skip to Phase 5):** build `embed.py` now. Landed
  (see `model.py`'s bullet above) — `embed_sentences` against a real,
  downloaded `BAAI/bge-base-en-v1.5`, `enablement_keep_mask`/
  `pool_response_vector`, both CPU-only (D-6). A `tests/integration/` test
  runs real text through `preprocess/*` → `embed.py` → `fit`/`save`/`load`/
  `score_row` end-to-end and passes — **this proves the mechanism works**,
  explicitly **not** that it reproduces the toy's science.

  **CLOSED 2026-07-25, satisfied by adjacent real data — see D-34.** The
  toy's original raw CSVs never materialized. User supplied a different,
  genuinely real labeled dataset (859 rows, 15 hazards, 30 seed groups,
  `/Users/kurt/ais/jb10_experiments/jb_1.0_1003_ground_truth_items_for_riki_eval.csv`)
  and directed running the full pipeline against it instead of continuing to
  wait. `scripts/run_real_data_is9.py` derives `seed_prompt_id` from
  `seed_prompt_text` grouping, then runs `preprocess/*` → one batched real
  `embed_sentences` call (19,556 segments) → `fit` (`--holdout-fraction
  0.2` at the seed-group level, 6/30 groups held out) → `evaluate_rows`.
  Zero rows excluded (no unseen hazards, no skipped cells). Held-out (n=270
  rows/6 seed groups) results: Enablement exact 0.619/AUC 0.759/QWK 0.421;
  Legitimization exact 0.551/AUC 0.678/QWK 0.329; final-label F1 0.836,
  precision 0.815, recall 0.858. In-sample (n=589) results are near-perfect
  as expected (training fit, not a generalization signal). Full report:
  `scripts/is9_real_data_metrics.json`.

  **This closes the mechanism+generalization half of IS-9** (the pipeline
  runs correctly end-to-end on real, non-synthetic, non-toy data and
  produces plausible, non-degenerate held-out metrics — in the same rough
  range as the toy's own published numbers, though not a byte-for-byte
  match, since this is a different dataset from a different source).
  **IS-9's original literal claim — frozen-fit metrics matching the toy's
  specific published reference numbers — is explicitly superseded, not
  achieved:** the toy's own raw CSVs remain unavailable in this environment,
  D-2's amendment and D-16's Finding B provenance question (which both
  depend on comparing against those exact reference numbers) stay
  genuinely unresolved, and are not expected to be resolved unless the
  toy's original files surface. User chose to close IS-9 on this basis
  rather than leave it open indefinitely pending data that may never
  arrive.

### Phase 5 — `hrc-predict`

- **IS-10 — `hrc-predict` batch logic. DONE (2026-07-25), CLI argparse layer
  deferred** (same reasoning as IS-8: a literal CLI script with no
  `hrc-train` to produce a real artifact would be premature). Built
  `model.py`'s `predict_rows`, architecturally mirroring `evaluate_rows`
  exactly: reuses `score_row` per row, catches `HardFailError`, but routes
  the row to a `failures` list (D-22) instead of an exclusion counter (D-14)
  — the same shared predicate, the other consequence. `PREDICTIONS_COLUMNS`/
  `FAILURES_COLUMNS` pin §6's exact per-row output order and D-25's
  corrected `failures.csv` shape (`prompt_uid, hazard, failure_reason` — no
  `seed_prompt_id`, **Finding C**). `to_predictions_frame`/
  `to_failures_frame` build a `pandas.DataFrame` with these columns
  explicit even for an empty row list, since `pd.DataFrame([])` alone has no
  columns for `to_csv` to derive a header from.

  6 tests in `tests/unit/test_model_predict.py` (123 total, zero
  regressions): unseen hazard → `failures` with `failure_reason ==
  "unseen_hazard"`; a genuinely skipped Legitimization cell (built the same
  single-class fixture as IS-6/IS-8) → `failures` with `"skipped_or_absent_
  cell"` — both of D-25's two reasons confirmed by value, not just "some
  failure happened"; a scoreable row → `predictions` with every expected
  field and type; a mixed batch (scoreable + both failure kinds together) →
  `len(predictions) + len(failures) == len(input rows)`, every `prompt_uid`
  accounted for exactly once — the real D-22 forcing function, not three
  isolated single-row tests; columns exact and `seed_prompt_id` absent from
  both; and an actual file write/read-back proving an empty batch's
  `failures.csv`/`predictions.csv` still carry a header, not just an empty
  file.

  **No new Awaiting-User finding** — the design reused already-built,
  already-tested pieces (`score_row`, `HardFailError`) with no fresh
  judgment calls (the `rule_reasons` CSV join delimiter, `"|"`, matches the
  convention `flags.py`'s `wrapper_label`/`disclaimer_label` already use, not
  a fresh choice).
- **IS-11 — `HazardResponseClassifier.score(rows)` Python API. DONE
  (2026-07-25) — the last slice in this backlog besides IS-9.** The
  single-row error contract was an explicitly pre-flagged Open Question
  (`PLAN.md` §11 item 5, critique P-N2, "deferred until the API is actually
  built") — asked directly before writing any code, per this entry's own
  instruction to "surface that decision, do not invent it." **User chose:
  never raise; one `RowResult` per input row** (matching D-14/D-22's
  established never-abort philosophy), locked as **D-31**. Concurrency
  safety is named in the same open question and remains genuinely
  unverified — documented as such in `score`'s own docstring, not tested or
  assumed either way.

  Built `HazardResponseClassifier.score` as a method (not a free function,
  matching `PLAN.md`'s own naming) plus `PredictRow` (raw prompt/response
  text input, unlike `score_row`'s already-pooled features) and `RowResult`.
  Internally: preprocess (`preprocess/*`, already built) → one batched
  `embed.embed_sentences` call across every row's segments together (not one
  call per row) → `embed.pool_response_vector` per row per component →
  `score_row` (IS-7), catching `HardFailError` into a `RowResult` instead of
  propagating it. Reads `self.embedding_model_name`/`embedding_model_revision`
  rather than a hardcoded default — see the D-23 fix below. Heavy imports
  (`embed.py`, therefore `torch`/`sentence-transformers`) are deferred to
  inside the method, so importing `hazard_classifier.model` itself never
  requires them.

  **"BGE model loaded once" is now a real, tested property, not just a
  docstring claim:** `embed.py`'s `_load_model` gained
  `@functools.lru_cache`, confirmed by a forcing-function test that calls
  `score` twice and checks `_load_model.cache_info()` directly — one miss
  (the first load), a hit on the second call, no second miss.

  **Fix found while building this slice, same pattern as IS-7's
  `specialized_advice_hazards` gap, not a new decision:**
  `HazardResponseClassifier` had no record of which BGE model/revision it
  was fit against — `score` needs to load the *same* model a caller
  embedded training data with (D-23), but there was no frozen source for it
  beyond a hardcoded default that could silently diverge from the real one.
  Fixed: `embedding_model_name`/`embedding_model_revision` fields on the
  classifier, matching `fit` keyword parameters, round-tripped through
  `manifest.json` by `save`/`load`. Moved `DEFAULT_MODEL_NAME` out of
  `embed.py` into `config.DEFAULT_EMBEDDING_MODEL_NAME` (which `embed.py`
  now imports) specifically so `model.py` never needs `torch`/
  `sentence-transformers` just to know the default model name.

  2 new tests in `tests/integration/test_score_api.py` (125 total, zero
  regressions, real BGE): a **mixed batch** (scoreable `hte` row, an unseen
  hazard, an enablement-only `prv` row) scored via `.score()` **never
  raises** and returns exactly 3 `RowResult`s in input order, each with the
  right shape (`scored`/`failure_reason` set correctly per D-31; the `prv`
  row's `legitimization_predicted is None`, D-18, confirmed even through
  this higher-level API, not just `score_row` directly); the model-caching
  forcing function above.

---

## Recommended execution order

1. **All "do now" slices are done:** ~~**IS-A**~~, ~~**IS-B**~~, ~~**IS-C**~~,
   ~~**IS-C2**~~, ~~**IS-C3**~~. D-23 is confirmed at the unit level across
   every call site in `rules.py` and `metrics.py`; neither module imports
   `hazard_classifier.config` anymore. The full-wiring half of IS-C/IS-C2/IS-C3
   (an actual artifact's frozen `rules.json`) is now **closed too** (IS-5).
   IS-B's `metrics.json` surfacing is **also closed now** (IS-8).
2. ~~**IS-1**~~ done (`schema.py`). ~~**IS-2**~~ done (`preprocess/*`) — **Phase
   1 is fully built.** ~~**IS-3**~~ done (`heads.py`). ~~**IS-4**~~ done
   (`model.py` `fit`). ~~**IS-5**~~ done (artifact save/load). ~~**IS-6**~~
   done (D-28 train-time gate) — **Phase 3 is fully built.** ~~**IS-7**~~
   done (predict/evaluate scoring pipeline, `score_row`). ~~**IS-8**~~ done
   (`hrc-evaluate` metric assembly, `evaluate_rows`). `embed.py` also **done**
   (real BGE, CPU-only). ~~**IS-9**~~ **closed 2026-07-25 (D-34)** — the
   toy's raw labeled data and cached run output never materialized, but
   rather than leave this open indefinitely, the user supplied a different
   real labeled dataset (859 rows) and directed running the full pipeline
   against it: `fit`/`evaluate_rows` against real BGE embeddings, a real
   seed-group holdout split, plausible non-degenerate held-out metrics
   (`scripts/run_real_data_is9.py`, `scripts/is9_real_data_metrics.json`).
   This closes the mechanism-plus-generalization half of IS-9; the toy's own
   literal reference-number match is explicitly **superseded, not
   achieved** — D-2's amendment and D-16's Finding B provenance question
   stay genuinely unresolved for the same reason (no toy data), and are not
   expected to resolve unless those files surface. ~~**IS-10**~~ done
   (`hrc-predict` batch logic, `predict_rows`). ~~**IS-11**~~ done
   (`HazardResponseClassifier.score(rows)`, D-31). **Every slice in this
   backlog is now done, including IS-9.**
3. ~~**IS-9**~~ closed via D-34 (adjacent real data) rather than the toy's
   original data, which never surfaced. If the toy's own raw CSVs ever do
   surface, re-running the literal parity comparison would still be
   worthwhile — D-34 doesn't rule that out, it just stopped waiting on it.
4. ~~**IS-10**~~ done. ~~**IS-11**~~ done. **Phase 5 is fully built.**
5. **The D-35 CLI skin is done (2026-07-25), landed as three ordered queue
   items, one per session:** shared `embed.build_component_features` +
   `hrc-train` (item 1); `hrc-evaluate` + `metrics.py`'s
   `flatten_metrics_report`/`render_summary` (item 2); `hrc-predict` (item
   3, reusing `predict_rows`/`to_predictions_frame`/`to_failures_frame`
   rather than `HazardResponseClassifier.score`, so all three CLIs share one
   feature-building code path). Every command verified two ways: mocked-BGE
   unit tests (142 total project-wide) and a real, non-mocked run via the
   installed console script against the real cached BGE model, each
   time.

Paper consistency is now well-covered (IC-1…IC-5 done). **Every
implementation slice in this backlog is now done, including IS-9 (closed
via D-34) and the D-35 CLI skin.** Every locked decision (D-1 through D-35)
has a landed implementation. There is nothing left queued in this project.
