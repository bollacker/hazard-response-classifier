# Status

Last updated: 2026-07-25 — **Retroactive documentation pass: D-36 and D-37
locked.** `PLAN.md` §11's five open questions were all resolved in practice
by what got built, but items 2 (pooling mode) and 4 (artifact serialization)
were never promoted to `DECISIONS.md` entries — a gap relative to this
project's own process. No code changed. **D-36:** pooling is mean-only,
`max`/`mean_max` never implemented (matches `embed.py` as built). **D-37:**
artifact format is `.npz` + JSON, no `joblib` anywhere in the codebase —
but the "confirm `joblib` not required by downstream consumers" half of
§11 item 4 was never actually put to the user, so that question moves to
Awaiting User below rather than being marked resolved. `PLAN.md` §11 items
2 and 4 updated to cross-reference D-36/D-37.

Prior update, 2026-07-25 — **Queue item 3 landed: `hrc-predict`. This
closes the entire CLI skin (D-35) and the whole `VERIFICATION.md` backlog —
every locked decision (D-1 through D-35) now has a landed implementation.**
`cli/predict.py` reuses item 1's `build_component_features` unchanged and
`model.predict_rows`/`to_predictions_frame`/`to_failures_frame` (already
built, IS-10) rather than `HazardResponseClassifier.score` — all three
CLIs now share the identical feature-building code path, not three separate
ones. 4 new tests (142 total, zero regressions), plus a real, non-mocked
`hrc-train`→`hrc-predict` run via the installed console scripts against the
real cached BGE model — inspected `predictions.csv`/`failures.csv` by hand.
**Nothing is queued. There is no more implementation work identified
anywhere in this project's ledger.**

Prior update, 2026-07-25 — **Queue item 2 landed: `hrc-evaluate`.** New
`cli/evaluate.py` reuses item 1's `build_component_features`/
`warn_if_skipped_components` unchanged; two new `metrics.py` functions
(`flatten_metrics_report` for `metrics.csv`'s long format,
`render_summary` for `summary.txt`, both `None`-safe against D-16/D-33's
undefined `auc`/`qwk` and an empty final-label population). 7 new tests
(138 total, zero regressions), plus a real, non-mocked
`hrc-train`→`hrc-evaluate` run via the installed console scripts against
the real cached BGE model — inspected all three output files by hand,
including a real `auc=null` on a genuinely degenerate held-out population
(D-33's null-conversion firing for real, not just in a crafted fixture).
**Only queue item 3 (`hrc-predict`) remains — closes the entire CLI skin
when it lands.**

Prior update, 2026-07-25 — **Queue item 1 landed: shared feature-building
refactor + `hrc-train`.** New `embed.build_component_features` (the one
preprocess/embed/pool pipeline every caller now shares, D-35);
`HazardResponseClassifier.score` refactored to use it (simpler, not just
relocated); `save()`'s signature grew the six manifest-extras kwargs. New
`src/hazard_classifier/cli/` package: `_common.py` (shared argparse
pieces, `fatal`, the load-time `skipped_components` warning `PLAN.md`
§5/§6 needed but nothing had built) and `train.py`. `pyproject.toml` gained
`[project.scripts]`; `examples/sample_input.csv` created (12 rows,
`hte`/`prv`). 3 new tests (131 total, zero regressions), plus a real,
non-mocked end-to-end run via the actual installed `hrc-train` console
script against the real cached BGE model, confirmed by hand outside the
test suite. **Queue items 2 (`hrc-evaluate`) and 3 (`hrc-predict`) remain,
in that order — this session stopped after item 1, per the one-slice
convention, not because anything raised a new Awaiting-User finding.**

Prior update, 2026-07-25 — **CLI-skin design proposed and locked as D-35.**
Two architectural forks for the `hrc-train`/`hrc-evaluate`/`hrc-predict`
skin were presented with explicit tradeoffs, not decided silently: (1)
extract the raw-text→embedded-features pipeline into one shared
`embed.build_component_features`, refactoring `HazardResponseClassifier.
score` to use it rather than leaving a second copy in the CLI layer — user
chose to extract; (2) extend `save()`'s signature with the manifest-extras
fields rather than have the CLI patch `manifest.json` after the fact — user
chose to extend. **No code written yet** — this is a design-level decision
only (D-35). The CLI skin itself is a substantial multi-file slice (new
`cli/` package, `examples/sample_input.csv`, `pyproject.toml`
`[project.scripts]`, plus the `build_component_features`/`save` refactors)
— now queued as three ordered sub-slices (shared refactor + `hrc-train`,
`hrc-evaluate`, `hrc-predict`; see Queue below), matching this project's
established one-slice-per-session discipline.

Prior update, 2026-07-25 — **D-32 and D-33 implemented.** Both were small,
already-locked decisions with no code yet: `score_row` now emits a
per-component `rule_reasons` string
(`"{component}_zeroed_no_effective_sentences"`) for D-4's forced-zero
short-circuit (D-32); `component_metrics`'s `qwk` now reports `None` instead
of a raw `NaN` on a degenerate single-class population, via a new
`_safe_qwk` mirroring `_safe_auc` (D-33). 2 new tests (127 total, zero
regressions). **Nothing is queued and Awaiting User is empty.** The only
thing left project-wide is the `hrc-train`/`hrc-evaluate`/`hrc-predict` CLI
skin — every other piece of logic in `VERIFICATION.md`'s backlog, including
IS-9 (D-34) and now D-32/D-33, is landed.

Prior update, 2026-07-25 — **IS-9 closed (D-34).** User supplied a different
real labeled dataset (859 rows, not the toy's own excluded files) and
directed running the full pipeline against it instead of continuing to wait.
`scripts/run_real_data_is9.py` ran `preprocess/*` → real BGE embeddings →
`fit` → `evaluate_rows` end-to-end with zero errors and zero excluded rows;
held-out metrics (n=270/227) landed in the same rough range as the toy's own
published numbers (Enablement exact 0.619/AUC 0.759/QWK 0.421;
Legitimization exact 0.551/AUC 0.678/QWK 0.329; final-label F1 0.836) without
literally matching them — **this closes the mechanism+generalization half of
IS-9; the toy's literal reference-number match is explicitly superseded, not
achieved**, and D-2/D-16's Finding-B provenance question stay unresolved for
the same reason (no toy data). Full report in
`scripts/is9_real_data_metrics.json`. **Every implementation slice in
`VERIFICATION.md`'s backlog is now done, including IS-9.** What's left
project-wide is now only: the `hrc-train`/`hrc-evaluate`/`hrc-predict` CLI
skin, and D-32/D-33's small pending code (see prior entry below — still
undone, still unqueued).

Prior update, 2026-07-25 — **Fix-proposal pass: P-N1 and DI-N1 resolved**
(locked as **D-32**, **D-33**). These were the only two items left in
Awaiting User; that list is now empty. Neither decision's code is
implemented yet — both are small, undone, and unqueued (see Recently
Completed for detail).

Prior update, 2026-07-25 — **IS-11 landed — every implementation slice in
`VERIFICATION.md`'s backlog is now done except IS-9** (blocked on real data,
not code; see below). User-directed "continue with Phase 5" after IS-10
raised no Awaiting-User finding.

IS-11's own pre-flagged Open Question (`PLAN.md` §11 item 5: the
`score(rows)` single-row error contract, explicitly "deferred until the API
is actually built, do not invent it") was asked directly before writing any
code. **User chose: never raise; return one `RowResult` per input row**
(matching D-14/D-22's established never-abort philosophy) — locked as
**D-31**. Concurrency safety, named in the same open question, remains
genuinely unverified and is documented as such, not tested or assumed.

Built `HazardResponseClassifier.score` (a method, not a free function) plus
`PredictRow`/`RowResult`: preprocess (`preprocess/*`) → one batched
`embed.embed_sentences` call across every row's segments → pool per
component → `score_row` (IS-7), catching `HardFailError` into a `RowResult`
rather than propagating it. `embed.py`'s `_load_model` gained
`@functools.lru_cache` so "BGE model loaded once" (`PLAN.md` §6) is now a
real, tested property (confirmed via `cache_info()`), not just a docstring
claim. **Fix found while building this slice, same pattern as IS-7's
`specialized_advice_hazards` gap:** `HazardResponseClassifier` had no record
of which BGE model/revision it was fit against, so `score` had no frozen
source to load the *same* model a caller trained with (D-23) — fixed by
adding `embedding_model_name`/`embedding_model_revision` fields, matching
`fit` keyword parameters, round-tripped through `manifest.json`. Moved
`DEFAULT_MODEL_NAME` out of `embed.py` into
`config.DEFAULT_EMBEDDING_MODEL_NAME` so `model.py` never needs `torch`/
`sentence-transformers` just to know the default. 2 new tests (125 total,
zero regressions, real BGE): a mixed batch (scoreable / unseen-hazard /
enablement-only rows together) via `.score()` never raises, returns 3
correctly-shaped `RowResult`s in order; the model-caching forcing function.

**What's left in the entire project, precisely:** the actual `hrc-train`/
`hrc-evaluate`/`hrc-predict` argparse CLIs + file I/O (a thin wrapper around
logic that is fully built and tested) and IS-9's real parity confirmation
(blocked on real labeled data that doesn't exist in this environment).
Nothing else is queued for paper review or new core logic.

In the prior pass: **IS-10 landed** (user-directed "continue with
Phase 5, pause after IS-10 if there are any additions to Awaiting User").
Built `model.py`'s `predict_rows`, architecturally mirroring `evaluate_rows`:
reuses `score_row` per row, catches `HardFailError`, but routes the row to a
`failures` list (D-22) instead of an exclusion counter (D-14) — same shared
predicate, the other consequence. `PREDICTIONS_COLUMNS`/`FAILURES_COLUMNS`
pin §6's exact output order and D-25's corrected `failures.csv` shape (no
`seed_prompt_id`, Finding C). `to_predictions_frame`/`to_failures_frame`
build a `pandas.DataFrame` with explicit columns even for an empty row list.
6 new tests (123 total, zero regressions): both of D-25's failure reasons
confirmed by value; a mixed batch's `len(predictions) + len(failures) ==
len(input rows)` with every `prompt_uid` accounted for exactly once (the
real D-22 forcing function); columns exact, no `seed_prompt_id`; an actual
file write/read-back proving an empty batch still gets a header.

**No new Awaiting-User finding from IS-10** — reused already-built pieces
(`score_row`, `HardFailError`) with no fresh judgment calls, so per your
instruction there is no pause here. Only **IS-11**
(`HazardResponseClassifier.score(rows)` batch API) remains in the entire
`VERIFICATION.md` backlog (IS-9 stays open, blocked on real data). Not
queued yet, per META_PLAN §5.

In the prior pass: **IS-9 attempted (user-directed "proceed IS-9")
and found genuinely blocked, not by missing code but by missing data.**
Checked the `security-evaluator` toy repo directly: its raw labeled CSVs
(`inputs/neyman_review_queue.csv`, `inputs/keys/batch_*_key.csv`) are
explicitly excluded from the repo (its own `inputs/README.md`: "Do not
commit source CSV data... provide the files at run time") and aren't present
anywhere in this environment; nor is its BGE hazard-weighted run's cached
output directory. The reference numbers `PLAN.md` §8.2 quotes are real
(confirmed in the toy's `README.md` "Expected Checks" table) but there is no
input data to reproduce a run from — a data gap, not a code gap, and not
something any amount of implementation closes.

Given three options (provide real data / build `embed.py` now and defer the
actual parity check / skip to Phase 5), **user chose: build `embed.py` now.**
Landed: `embed_sentences` (real, downloaded `BAAI/bge-base-en-v1.5` via
`sentence-transformers`, CPU-only per D-6), `enablement_keep_mask`/
`pool_response_vector` (mean pooling + the Enablement prompt-repetition
drop, ported from the toy's `aggregate_for_response`/`effective_indices`).
Added `torch`/`sentence-transformers` to `pyproject.toml` and installed them
(network access to Hugging Face worked in this environment). 5 no-network
unit tests for the pooling logic, plus a new `tests/integration/` test (a
category that needs network on first run only, model cached after — kept
out of `tests/unit/` per `PLAN.md` §8.1's "unit tests need no model
download" rule) that runs real text through `preprocess/*` → `embed.py` →
`fit`/`save`/`load`/`score_row` end-to-end and passes. **This proves the
pipeline's mechanism works — it is explicitly not a parity/science
confirmation.** IS-9's actual claim (frozen-fit metrics match the toy's real
reference numbers) remains open; it cannot be closed without real labeled
data. 117 tests total, zero regressions.

**Phase 0's `embed.py` and Phase 4's logic (IS-7, IS-8) are all built now.**
IS-9 stays explicitly open, not silently dropped — revisit if real labeled
data becomes available. Next per `VERIFICATION.md`'s execution order is
**IS-10** (Phase 5, `hrc-predict`'s CLI logic), which — like IS-7/IS-8 — is
buildable and testable against synthetic fixtures without real data. Not
queued yet, per META_PLAN §5.

In the prior pass: implementation slice **IS-8** landed (user-directed
"do all Phase 4 items in order, pause after a step only if it results in a
new Awaiting User item"). Built `model.py`'s `evaluate_rows`: catches
`score_row`'s `HardFailError` per row and tallies D-14's excluded-row
breakdown before any ground-truth column is read (this is what makes
Finding A — a blank label on an excluded row never aborts — true by
construction); applies D-26's family-aware blank-ground-truth validation to
surviving rows via a new `BlankGroundTruthError` (a whole-run **abort**,
deliberately distinct from `HardFailError`'s per-row **exclusion**);
partitions via `metrics.py`'s already-built `partition_by_holdout` (D-13),
warning when no holdout was recorded; assembles the full `metrics.json`
shape via `metrics.py`'s already-built `component_metrics`/
`final_label_metrics` (D-15/D-16/D-17), omitting an empty population's key
entirely (a direct reading of D-13's own "reported... whenever both are
non-empty"). 6 new tests (111 total, zero regressions).

**This pass hit and resolved a second blocker in the same breath (not a
pause — the user answered immediately):** `is_safe_ground_truth`'s literal
CSV encoding had been an unresolved Open Question since IS-1, and became a
hard blocker once `final_label_metrics` needed it parsed into a boolean —
asked directly, user answered `"safe"`/`"unsafe"`, locked as **D-30**;
added `schema.py`'s `parse_is_safe_ground_truth`. **Three fix-in-passing
findings** (none new decisions): the IS-6 test-fixture collision (already
recorded), a missing `specialized_advice_hazards` field on
`HazardResponseClassifier` (IS-7), and `ScoredRow` missing the
business-rule-adjusted high probability D-16's AUC needs (fixed by adding
`enablement_adjusted_high`/`legitimization_adjusted_high` fields).

**Phase 4's logic (IS-7, IS-8) is fully built; only the argparse/file-I/O
CLI skin and `embed.py` remain, deliberately deferred** (a literal CLI
script that can't run against real data yet would be a premature, untestable
stub — same reasoning as every prior `embed.py` deferral). Next per
`VERIFICATION.md`'s execution order is **IS-9** (the parity harness) — the
first check that genuinely needs `embed.py` and a real trained artifact, not
synthetic fixtures; this is a materially different kind of slice from
everything built so far this session and is very likely where this
multi-item run will need to stop or change shape. Not queued yet, per
META_PLAN §5.

In the prior pass: implementation slice **IS-7** landed (user-directed
"do all Phase 4 items in order, pause after a step only if it results in a
new Awaiting User item" — IS-7 raised none, so this note is a normal
in-progress update, not a pause). Ported the toy's `apply_component_business_
rules`/`v14_overall_score`/`discrete_v14_label`/`score_from_centered_probs`
into `rules.py`'s `apply_legitimization_disclaimer_rule` (only the surviving
disclaimer rule — the toy's other two are subsumed by D-18/D-4),
`discrete_v14_label`, `v14_overall_score`, `combined_component_score`, and
`model.py`'s `score_row` — the per-row predict/evaluate pipeline:
`resolve_component_action` (already built) → serve or D-4's zero sentinel →
the disclaimer rule → the monotonicity gate on adjusted probabilities (D-19)
→ v1.4 label + D-21's continuous side-output. `HardFailError` replaces a
raw abort for hard-fail rows, leaving the consequence (D-22/D-14) to
`hrc-predict`/`hrc-evaluate` (not built yet). 6 new tests (105 total, zero
regressions), including the **IC-1(a) end-to-end trace** through a real
`fit()`-trained classifier and a hand-constructed-`Cell` forcing function
proving D-21's v14/label independence. **Fix found in passing, not a new
decision:** `HazardResponseClassifier` was missing a
`specialized_advice_hazards` field entirely — IS-5's `save` froze it into
`rules.json` but never read it back, so `score_row`'s own family lookup had
no frozen source for it. Fixed by adding the field, a matching `fit`
keyword parameter, and `load` support; removed the now-redundant parameter
from `save`. **Phase 4's scoring pipeline is built; next per
`VERIFICATION.md` is IS-8** (`hrc-evaluate` CLI + metric assembly) — not
queued yet, per META_PLAN §5.

In the prior pass: implementation slices **IS-5** (artifact
save/load) and **IS-6** (D-28 train-time gate) landed, completing **Phase 3**
(user-directed "do all Phase 3 items in order," resumed after the IS-4
Awaiting User finding was resolved as **D-29**, "leave the natural ValueError
as-is"). **IS-5** built `model.py`'s `save`/`load` against the §4 artifact
format (`heads.npz`, `thresholds.json`, `rules.json`, `manifest.json`),
completing D-23's IS-C/IS-C2/IS-C3 wiring end-to-end (a real save→load round
trip, not hand-built fixtures, now proves `is_required_component`/
`hazard_family` read the *loaded* artifact, never installed config) and
adding a new `rules.hazard_family` helper (ported from the toy's
`hazard_rule_family`, narrowed to this project's two locked families). **IS-6**
built the D-28 gate directly into `fit`: a wholly-skipped Enablement raises a
new `WhollySkippedEnablementError` (before Legitimization's loop even
starts); a wholly-skipped Legitimization warns (`warnings.warn`) but still
writes a usable enablement-only-workload artifact. Building IS-6 surfaced a
cross-check finding (not a new decision, just a stale-test fix): two
pre-existing IS-4/IS-5 tests had used a single-class-**Enablement** fixture
to exercise D-5's skip-marking mechanism, which started raising once IS-6
landed — fixed by switching both to Legitimization instead. 7 new tests
(4 + 3; 99 total, zero regressions). **Phase 3 is now fully built**; next is
Phase 4 (IS-7 onward, the predict/evaluate pipeline), per `VERIFICATION.md`'s
execution order — not queued yet, per META_PLAN §5's user-owns-ordering rule.

In the prior pass: implementation slice **IS-4** (`model.py` `fit`,
`VERIFICATION.md` IS-4; user-directed "do all Phase 3 items in order, pause on
a new Awaiting-User finding") landed: cell enumeration reusing `rules.py`'s
`is_required_component` (D-18), D-1 holdout exclusion + `choose_holdout_seed_
prompts` (a simplified port — seed-level fraction only, dropping the toy's
response-count target tied to its now-gone grouped-CV apparatus, D-12), D-4
empty/echo exclusion via an explicit `component_effective` mask (deliberately
not an implicit "all-NaN row" convention, to avoid silently misreading a real
embedding bug as an intentional exclusion), D-10's gated grid search and D-2's
`n_own>=5` cliff (both reusing `rules.py`'s already-built
`optimize_ordinal_thresholds`). D-5's whole-component skip trigger needed
**no new code at all** — it falls out of `heads.py`'s own per-cell degeneracy
check automatically, since every hazard's fit within a component shares the
identical row-level label array. 6 new tests (92 total, zero regressions),
the strongest one a genuine forcing function: corrupted the ground-truth
labels *and* features for exactly the held-out rows, refit, and confirmed
every fitted parameter came back bit-identical — proving true exclusion, not
just a recorded id list. **New finding, added to Awaiting User below (not
resolved silently, per instruction to pause on a new finding):** a blank
`legitimization_value` on a non-enablement-only hazard **training** row
currently raises a raw `ValueError` from `int("")` inside `fit` — no locked
decision covers this train-time case (D-26 only pins the analogous
`hrc-evaluate` condition, to *error*). **Pausing here per the user's
instruction** rather than proceeding to IS-5/IS-6 in the same pass.

In the prior pass: implementation slice **IS-3** (`heads.py`
`BinaryHead`, `VERIFICATION.md` IS-3, user-directed "execute the next item in
the queue" following IS-2) landed: ported the toy's `standardize_train_test`/
`fit_binary_head_weighted` (`run_bge_hazard_weighted_heads.py` L70-110) and
`logit`/`sigmoid`/`centered_probability` (`scoring_common.py` L412-423) into a
`BinaryHead` dataclass with `predict_proba`/`predict_proba_centered` and
`to_arrays`/`from_arrays` (§4 `heads.npz` round-tripping), per §2.3's refactor.
`fit_binary_head` deliberately takes no hazard parameter at all (confirmed by
a signature-inspection test) — D-7/D-18's Legitimization enablement-only-hazard
exclusion is entirely the caller's job (`model.py`'s `fit`, IS-4, not built
this pass). One self-consistency choice beyond a literal port: `center_mean`
is computed via `BinaryHead`'s own `predict_proba` formula rather than
sklearn's directly, so a head's centering stays internally consistent even
after a save/load round-trip. 7 new tests (86 total, zero regressions),
including a forcing function found by actually running it, not assumed: a
first-draft "mean/scale identical, coef differs across hazard weightings"
test used a cleanly-separable fixture and came back with **identical**
coefficients too (a uniform per-class reweighting of separable data selects
the same max-margin separator regardless of which class is up-weighted) —
replaced with a deliberately overlapping, non-class-aligned three-hazard-group
fixture where the weighting genuinely changes the fit. **Phase 3 has started**
(IS-3 done; IS-4 — `model.py`'s `fit`, cell enumeration across
D-1/D-4/D-5/D-10/D-18/D-2 — is next per `VERIFICATION.md`'s execution order).
Queue is empty again (same user-must-direct-the-next-pick convention as after
IS-2).

In the prior pass: implementation slice **IS-2** (`preprocess/decode.py`,
`segment.py`, `flags.py`, `VERIFICATION.md` IS-2, top-of-queue item) landed:
ported the toy's ~1000-line `build_reviewable_sentence_segments.py` into three
pure-function modules per `PLAN.md` §2.2's package layout. **Phase 1 is now
fully built** (IS-1 + IS-2). Before writing code, asked the user which source
to bundle for the host-independent English wordlist (D-6-adjacent, §7) — a
genuine license/size tradeoff, not mine to pick silently per META_PLAN §3 —
user chose a filtered snapshot of this machine's `/usr/share/dict/words`
(234,428 entries) over a small MIT-licensed alternative; provenance and the
one unresolved caveat (exact redistribution terms not independently
re-verified) recorded in `preprocess/data/WORDLIST_PROVENANCE.md`.
`pyproject.toml` gained `[tool.setuptools.package-data]`; confirmed by an
actual `python -m build --wheel` that the bundled file lands in the built
wheel, not just the editable install. 20 new tests (79 total, zero
regressions): ported the toy's six existing asserts (base64 decode,
code-to-English extraction, three prompt-repetition/later-authored-
continuation cases, and the toy's `build_segments`-level composition
reproduced by hand, since no orchestration function exists yet in this
codebase — that's `embed.py`'s job, a later phase) plus new tests including a
genuine forcing function for host-independence (asserted structurally, after
a source-grep test false-positived against this module's own docstring) and
an HTML-entity case picked specifically because the toy's own literal example
turned out to be a tie that raw text wins on a length tiebreak — verified by
running it, not assumed. **Deliberately not ported** (documented scoping
decision, not an oversight): `signal_score`/`semantic_signal_score` and
`text_hash`/`segment_hash` — confirmed unused by any modeling/business-rule
path in the toy and not named in `PLAN.md` §2.2's `flags.py` line. In a prior
session: implementation slice **IS-1** (`schema.py`,
Phase 1, user-directed "Execute Phase 1") landed: `load_csv`/`normalize_hazard`
with mode-scoped required columns (D-24/D-26), verbatim-ported hazard
normalization (D-27), train-only `known_hazards` rejection (D-27), and an
`{0,1,2}` range check scoped correctly to `enablement_value`/
`legitimization_value` only (a drafting slip in D-26's own text had this
loosely covering `is_safe_ground_truth` too — found and corrected in
`DECISIONS.md`/`PLAN.md` this pass). 14 new tests (59 total), two confirmed as
genuine forcing functions by deliberate sabotage, not just read: the
case-variant-stays-distinct claim, and — the important one — an evaluate-mode
row with an unrecognized hazard *and* a blank ground-truth label does **not**
raise, proving `schema.py`'s half of D-26's Finding-A fix. Packaging fix found
in passing: `pyproject.toml` was missing `pandas` and had `scikit-learn`
dev-only despite already being a production import in `metrics.py` — both now
main dependencies. **IS-2 (`preprocess/*`) was deliberately not attempted this
pass** — the toy's equivalent file is ~1000 lines of deobfuscation/
segmentation logic, a genuinely separate undertaking from schema validation;
queued explicitly below rather than rushed. Earlier this session: the
IS-A/IS-B/IS-C/IS-C2/IS-C3 chain of "do now" slices all landed; the D-19–D-24
integration check run to formal close (no conflict) and `VERIFICATION.md`
authored; the D-25–D-28 consistency audit and its three findings (A/C-1, B/Q-1,
C/N-1), all resolved.

This file is a queue, not an orchestrator: no session should pop more than
one item or advance past an Awaiting User item on its own. See
`META_PLAN.md` §5 for the rules governing how this file is read and updated.

## Current Phase

None in flight. Finding A / C-1 from the 2026-07-25 D-25–D-28 consistency audit
is resolved (D-26 amended; notes on D-27/D-14; `PLAN.md` §2.1/§5/§8.1 aligned;
`critiques/2026-07-25-decisions-consistency.md`). Finding **B** is now resolved
too (ledger de-risked via D-16/D-2 notes + §8.2; empirical settle deferred to
the Phase-4 parity harness by design). Finding **C** (`seed_prompt_id`
asymmetry) is now resolved too (D-25 amended; D-22/D-24 notes; `PLAN.md` §6) —
**all three audit findings are closed.** The Deliverable 3 critique is
fully resolved on the answered findings (D-4 amendment + D-19–D-24 applied to
`PLAN.md`). The D-19–D-24 integration check is **done**
(`critiques/2026-07-25-integration-d19-d24.md`, no conflict), so the ledger's
cross-decision consistency is fully covered on paper. Remaining confirmation is
implementation slices, catalogued in **`VERIFICATION.md`** — per META_PLAN §4,
the ledger is now confirmed by building and testing (one slice per session), not
by more review. **Every implementation slice is done except IS-9:** IS-A
(D-20), IS-C/IS-C2/IS-C3 (D-23, unit level), IS-B (D-17 `n` field), IS-1
(`schema.py`, D-24/D-26/D-27's structural half), IS-2 (`preprocess/*`,
decode/segment/flags), IS-3 (`heads.py` `BinaryHead`, D-7), IS-4 (`model.py`
`fit`, D-1/D-4/D-5/D-7/D-18/D-2/D-10), IS-5 (artifact save/load, D-1/D-6/
D-13/D-23/D-27/D-28), IS-6 (D-28 train-time gate), IS-7 (`score_row`,
D-3/D-4/D-11/D-19/D-20/D-21/D-27), IS-8 (`evaluate_rows`,
D-13/D-14/D-15/D-16/D-17/D-26), `embed.py` (real BGE + pooling, D-6), IS-10
(`predict_rows`, D-22/D-25), and IS-11
(`HazardResponseClassifier.score(rows)`, D-23/D-31) (see Recently
Completed). **Every phase's logic is fully built** — only the
argparse/file-I/O CLI skin remains as unbuilt code, plus IS-9's real parity
confirmation blocked on missing data.

IS-4's Awaiting-User finding was resolved by the user (D-29); IS-8 hit and
resolved a second blocker in the same breath (D-30); IS-9 was found
genuinely blocked by missing real data (confirmed by direct inspection),
and the user chose to build `embed.py` and defer the real parity check;
IS-10 raised no new finding; **IS-11 had its own pre-flagged Open Question
(the `score(rows)` error contract, `PLAN.md` §11 item 5) asked directly
before writing code, resolved immediately as D-31** (never raise, per-row
`RowResult` entries). **The Queue is empty — nothing left in
`VERIFICATION.md`'s backlog except IS-9**, which stays open, not silently
dropped, pending real labeled data. Not queued yet, per META_PLAN §5's
user-owns-ordering rule.

Historical context, still accurate: the predict-time control flow that
accumulated the most churn (D-3/D-4/D-5/D-11/D-18, all touching what happens to a
single `(component, hazard, response)` row) now has a real forcing-function
test behind it, per META_PLAN §4: the truth table in
`test_predict_resolution.py` was verified (outside the test suite itself,
by hand) to actually fail under the pre-D-11-amendment precedence — it is
not just happy-path coverage. This is genuine evidence the five decisions
compose correctly, not just an inference from re-reading the ledger again.

Two smaller items remain flagged but not queued (see Awaiting User): DI-N1
(D-17's schema has no null/NaN convention for undefined metrics) and the
`metrics.py`/`component_metrics` code-vs-ledger gap on the `n` field from
D-17's DI-Q4 amendment.

D-1 through D-17 are locked and applied to `PLAN.md`'s
prose. The decision-review critique is fully resolved; the entire
Deliverable 2 critique (`critiques/2026-07-23-deliverable-2.md`) is fully
resolved (D-12 through D-17). Three implementation slices now exist and pass:
`src/hazard_classifier/rules.py` (D-9/D-10 monotonicity gate, 5 tests; D-18/
D-3/D-4/D-5/D-11's predict-time resolution, 23 tests) and
`src/hazard_classifier/metrics.py` (D-13/D-15/D-16/D-17 metric computation,
11 tests) — 39 tests total, all green. `src/hazard_classifier/config.py`
was added alongside `metrics.py` to hold the two hazard-family sets
(`ENABLEMENT_ONLY_HAZARDS`, `SPECIALIZED_ADVICE_HAZARDS`) per §2.2's
package layout, since neither existed in the package yet. Queue is empty.

## Queue

_The full verification backlog now lives in **`VERIFICATION.md`** — a
decision→check coverage matrix for all 28 decisions, integration checks
(IC-1…IC-6, most already done), and implementation slices (IS-A…IS-11). This
queue holds only the next few items pulled from it. The **D-19–D-24 integration
check (IC-2) is done** — `critiques/2026-07-25-integration-d19-d24.md`, no
conflict found._

**The CLI skin (D-35) was the only remaining work item — all three ordered
sub-slices are now done.** See Recently Completed.

1. [x] Implementation slice: shared feature-building refactor + `hrc-train`
   — **DONE 2026-07-25**, see Recently Completed.

2. [x] Implementation slice: `hrc-evaluate` — **DONE 2026-07-25**, see
   Recently Completed.

3. [x] Implementation slice: `hrc-predict` — **DONE 2026-07-25**, see
   Recently Completed. **This was the last item in the entire
   `VERIFICATION.md` backlog.**

_Empty. Nothing left to queue — every decision in `DECISIONS.md` (D-1
through D-35) now has a corresponding implementation, and every
implementation slice in `VERIFICATION.md` is done. The project's own
"what's left" question (`META_PLAN.md`'s reason for existing) has no
current answer beyond ordinary future maintenance: a real production
labeled dataset arriving would still be worth running through the pipeline
(as D-34 already did once, informally), and any new feature request starts
a fresh Decision Ledger entry through the normal fix-proposal mechanism —
neither is queued speculatively._

## Awaiting User

- **D-37's own Open Question:** has any downstream consumer of the artifact
  format actually confirmed a `joblib` requirement? The shipped format
  (`.npz` + JSON, no `joblib`) is locked as-is, but this specific
  confirmation — named explicitly in `PLAN.md` §11 item 4 — has never been
  put to the user. Not blocking any queued work; flagged per META_PLAN §3
  rather than answered silently.

Otherwise empty. P-N1 and DI-N1 (the two remaining nice-to-have findings)
were resolved in a prior session — see Recently Completed.

## Recently Completed

- 2026-07-25 — Bookkeeping/documentation pass, scope: **`PLAN.md` §11 open
  questions 2 and 4** (user-directed: "go ahead and make the DECISION
  updates" after being asked whether these two open questions, resolved in
  code but never logged, needed retroactive `DECISIONS.md` entries). No code
  changed. Added **D-36** (pooling is mean-only, `max`/`mean_max` never
  built — matches `embed.pool_response_vector` as it already stands) and
  **D-37** (artifact format is `.npz` + JSON, no `joblib` anywhere in the
  codebase). Cross-referenced both into `PLAN.md` §11 items 2 and 4. D-37
  carries its own unresolved Open Question — whether a downstream consumer
  actually needs `joblib` — which was never put to the user; moved to
  Awaiting User above rather than marked resolved, per META_PLAN §3.

- 2026-07-25 — Implementation slice, scope: **Queue item 3 — `hrc-predict`**
  (D-35, "execute the next item in the queue"). **The last item in D-35's
  queue and in the entire `VERIFICATION.md` backlog.** Built
  `cli/predict.py` (`hrc-predict --model-dir --input --output-dir
  [--allow-download]`) reusing item 1's `build_component_features` +
  `_common.warn_if_skipped_components` unchanged, and `model.predict_rows`/
  `to_predictions_frame`/`to_failures_frame` (already built, already
  tested, IS-10) rather than `HazardResponseClassifier.score` — deliberate,
  per the queue note: this makes `hrc-predict`'s feature-building step
  identical in code path to `hrc-train`'s and `hrc-evaluate`'s, not a
  fourth independent implementation. No new business logic was needed
  beyond the argparse/file-I/O skin itself — `predict_rows` never raises
  (D-22), so the only `fatal()` paths are a bad `--model-dir`
  (`FileNotFoundError` from `load`) and a schema-invalid `--input`
  (`SchemaError`).

  4 new tests in `tests/unit/test_cli_predict.py` (142 total, zero
  regressions): a full mocked-BGE run against `examples/sample_input.csv`
  (ground-truth columns present but confirmed ignored, D-24) scores all 12
  rows with zero failures, `prv` rows correctly blank on
  `legitimization_predicted` (D-18), `seed_prompt_id` absent from both
  outputs (D-25's amendment); a mixed-batch test appends one genuinely
  unseen-hazard row and confirms it alone routes to `failures.csv` with
  `failure_reason="unseen_hazard"` while the other 12 still score
  normally — `len(predictions) + len(failures) == len(input rows)`, the
  real D-22 forcing function, not just "some failure happened"; two
  `fatal()` paths (schema-invalid input; missing `--model-dir`).
  **Verified beyond the mocked unit tests, not just assumed:** a real,
  non-mocked `hrc-train` then `hrc-predict` via the installed console
  scripts against the real cached BGE model — inspected
  `predictions.csv`/`failures.csv` by hand: correct `predicted_label`
  values, `prv` rows' `legitimization_predicted` genuinely blank in the raw
  CSV (not just `None` in a Python object), `failures.csv` present with a
  header and zero data rows. Added "Implementation slice landed" note to
  `DECISIONS.md` D-35.

  **This closes D-35 entirely and the whole `VERIFICATION.md` backlog.**
  Every locked decision (D-1 through D-35) now has a landed implementation.
  Nothing is queued; there is no further work identified anywhere in this
  project's ledger.

- 2026-07-25 — Implementation slice, scope: **Queue item 2 — `hrc-evaluate`**
  (D-35, "execute the next item in the queue"). Built `cli/evaluate.py`
  (`hrc-evaluate --model-dir --input --output-dir [--allow-download]`)
  reusing item 1's `build_component_features` and
  `_common.warn_if_skipped_components` unchanged — no new pipeline code,
  confirming the item-1 refactor's whole point (one shared feature-building
  step, not a copy per CLI). Added two new `metrics.py` functions per
  `PLAN.md` §5's own "best-effort, correctable" framing of the output
  schema: `flatten_metrics_report` (`metrics.csv`'s long format — one row
  per `(population, section, metric, value)`, nested `confusion_counts`/
  `components.*` flattened into a dot-separated `metric` path, the three
  run-level D-13/D-14 fields tagged with the sentinel population
  `"overall"`) and `render_summary` (`summary.txt`, built on a small
  `None`-safe `_fmt` helper — `auc`/`qwk` (D-16/D-33) and every
  `final_label_metrics` field on an empty population are genuinely `None`,
  not always floats, so a naive `f"{x:.3f}"` would crash on exactly the
  rows most worth reporting on). Both kept in `metrics.py`, not inline in
  the CLI, so they're unit-testable without argparse/file I/O.
  `evaluate.py` catches `SchemaError`/`BlankGroundTruthError` (D-26) into
  `_common.fatal`.

  7 new tests (138 total, zero regressions): `tests/unit/test_cli_common.py`
  (new — closes a gap left from item 1) tests `fatal`/
  `warn_if_skipped_components` directly via a duck-typed `SimpleNamespace`
  stand-in rather than only indirectly through a full CLI run;
  `tests/unit/test_cli_evaluate.py` (train → evaluate against
  `examples/sample_input.csv`, BGE mocked, reusing item 1's fixture/mocking
  pattern rather than re-deriving it) confirms all three output files, the
  correct `n`/`n_rows`/exclusion shape (including Legitimization's D-15
  exclusion of the 6 `prv` rows), `metrics.csv`'s exact column set,
  `summary.txt`'s D-13 no-holdout warning text; a second test with
  `--holdout-seed-fraction 0.5` confirms both populations appear when a
  holdout exists; a third confirms `BlankGroundTruthError` exits cleanly via
  `fatal`. **Verified beyond the mocked unit tests, not just assumed:** a
  real, non-mocked `hrc-train --holdout-seed-fraction 0.3` then
  `hrc-evaluate` via the installed console scripts against the real cached
  BGE model — inspected `metrics.json`/`metrics.csv`/`summary.txt` by hand,
  all correctly shaped, including a **real** `auc=null` on a genuinely
  degenerate 2-row held-out Legitimization population (D-33's
  null-conversion firing in the wild, not just against the synthetic
  fixture that originally motivated it). Added "Implementation slice
  landed" note to `DECISIONS.md` D-35. **Queue item 3 (`hrc-predict`)
  remains** — stopped here per the one-slice-per-session convention;
  landing it closes the entire CLI skin, nothing left in `VERIFICATION.md`'s
  backlog after that.

- 2026-07-25 — Implementation slice, scope: **Queue item 1 — shared
  feature-building refactor + `hrc-train`** (D-35, "execute the next item in
  the queue"). Built `embed.build_component_features(prompt_texts,
  response_texts, *, model_name, revision=None, allow_download=False)`:
  takes parallel text sequences rather than a `DataFrame` (keeping `embed.py`
  free of a pandas-shaped dependency it didn't already have) and plain `str`
  component keys rather than importing `model.py`'s `Component` `Literal`
  (matching `rules.py`'s existing untyped-`component` convention, avoiding a
  new `embed.py`→`model.py` import edge in a codebase that deliberately
  layers `embed.py` below `model.py`). Refactored
  `HazardResponseClassifier.score` to call it instead of inlining its own
  copy of the same pipeline — this genuinely simplified `score` (the
  per-row segment-range bookkeeping collapses into indexing the shared
  function's output), not just relocated code. `save()`'s signature grew
  six optional manifest-extras kwargs (code version, hyperparameters,
  training timestamp, training-file hash, training row count, training
  hazard counts, `PLAN.md` §3 step 5), merged into the manifest only when
  supplied — every pre-D-35 caller (every test but the new one) still gets
  the exact prior manifest shape.

  New `src/hazard_classifier/cli/` package: `_common.py`
  (`add_allow_download_flag`, `fatal` — clean stderr + `exit(1)` on a domain
  error instead of a raw traceback, `warn_if_skipped_components` — the
  load-time D-28 warning `PLAN.md` §5/§6 both require but nothing had built
  yet) and `train.py` (`hrc-train --input --output-dir
  [--other-hazard-weight] [--model-name] [--holdout-seed-fraction]
  [--allow-download]`). `hrc-train` computes the manifest extras `save()`
  itself can't (`importlib.metadata.version`, a `hashlib.sha256` of the raw
  input bytes, a UTC ISO timestamp, per-hazard `value_counts` cast to plain
  `int` for JSON-safety) and catches `SchemaError`/
  `WhollySkippedEnablementError` into `fatal()`. `pyproject.toml` gained
  `[project.scripts]` for all three commands (safe before
  `evaluate.py`/`predict.py` exist — entry points aren't validated until
  invoked) and `examples/sample_input.csv` was created (12 rows, `hte`/`prv`,
  full §2.1 schema, per §8.1).

  3 new tests in `tests/unit/test_cli_train.py` (131 total, zero
  regressions): a full mocked-BGE run (per §8.1,
  `monkeypatch.setattr(embed, "embed_sentences", ...)`) produces every
  artifact file, a correctly-shaped manifest with all six new extras, and
  an artifact `model.load()` genuinely reloads; `--holdout-seed-fraction`
  produces a non-empty recorded split; a schema-invalid CSV exits cleanly
  via `fatal()` rather than a raw traceback. Also refactored
  `tests/integration/test_pipeline_mechanism.py` to call
  `build_component_features` directly instead of keeping a second inline
  copy of the same pipeline in the test itself, and added
  `test_manifest_extras_omitted_by_default_and_present_when_supplied` to
  `tests/unit/test_model_artifact.py`. **Verified beyond the mocked unit
  tests, not just assumed:** installed the package (`pip install -e .`),
  confirmed `hrc-train --help` resolves via the real console-script entry
  point, and ran a real, non-mocked `hrc-train` against
  `examples/sample_input.csv` with the real cached BGE model — inspected
  the resulting `manifest.json` by hand, correctly shaped. Added
  "Implementation slice landed" note to `DECISIONS.md` D-35. **Queue items
  2 (`hrc-evaluate`) and 3 (`hrc-predict`) remain** — stopped here per the
  one-slice-per-session convention, not because of any new finding.

- 2026-07-25 — Implementation slice, scope: **D-32 + D-33** (the two small
  pending code changes from the P-N1/DI-N1 fix-proposal pass). Proposed both
  diffs with exact file/line locations before writing code, per the user's
  "propose actions" request; two remaining naming/scope micro-decisions
  (D-32's string granularity, whether to also suppress D-33's
  `UndefinedMetricWarning`) were surfaced rather than picked silently — user
  chose per-component strings for D-32 and left D-33's warning firing
  (out of that decision's literal scope).

  **D-32:** `score_row`'s `action == "score_zero"` branch
  (`model.py`) now appends `f"{component}_zeroed_no_effective_sentences"` to
  `rule_reasons`. 2 tests in `tests/unit/test_model_score_row.py`: extended
  the existing IC-1(a) trace test to also assert the new string coexists
  with D-19's disclaimer string; added `test_score_zero_emits_reason_string`
  isolating D-4's string alone via `"hte"` (no disclaimer interference).

  **D-33:** new `_safe_qwk` in `metrics.py`, mirroring `_safe_auc`'s
  compute-then-convert-`NaN`-to-`None` shape; wired into `component_metrics`
  in place of the raw `float(cohen_kappa_score(...))` call. 1 new test in
  `tests/science/test_metrics.py`
  (`test_component_metrics_qwk_is_none_for_single_class`), reusing the exact
  fixture from the existing `auc`-is-`None` test — confirmed directly that
  the same single-class fixture makes `cohen_kappa_score` return `NaN` too,
  not assumed.

  Full suite: 127 passed, zero regressions (was 125). Added "Implementation
  slice landed" notes to both `DECISIONS.md` entries. **Nothing remains
  queued; Awaiting User is empty.** What's left project-wide is only the
  `hrc-train`/`hrc-evaluate`/`hrc-predict` CLI skin.

- 2026-07-25 — Investigation + implementation slice, scope: **IS-9 closure
  via D-34**. User pointed at a candidate real dataset
  (`/Users/kurt/ais/jb10_experiments/jb_1.0_1003_ground_truth_items_for_riki_eval.csv`)
  and asked whether it was sufficient real data. Checked schema against
  `schema.py`'s required columns directly (not assumed): 859 well-formed
  rows (verified via the `csv` module, not just pandas), all 8 required
  fields non-blank; `is_safe_ground_truth` exactly `"safe"`/`"unsafe"`
  (D-30); `enablement_value`/`legitimization_value` exactly `{0,1,2}`
  (D-26); 15 hazard codes all resolving cleanly to `config`'s frozen sets
  after D-27 normalization. Two column mismatches found: `sut_response`
  instead of `response_text` (user renamed it directly in the file), and
  `seed_prompt_text` instead of `seed_prompt_id` (only 30 distinct seed
  texts behind 859 rows, each mapping to exactly one hazard — confirmed
  safe to derive a synthetic id by grouping identical text). Flagged
  clearly that this is a **different** dataset from the toy's own excluded
  files, so it could unblock IS-9's *mechanism* but not its *literal
  parity claim* — a distinction surfaced before running anything, not
  discovered after.

  User directed using it and running IS-9. Built
  `scripts/run_real_data_is9.py`: derives `seed_prompt_id`, schema-validates
  via `schema.load_csv`, runs the full pipeline (`preprocess/*` → one
  batched real `embed_sentences` call, 19,556 segments → `fit`
  (`--holdout-fraction 0.2`, seed-group level) → `evaluate_rows`). Ran
  clean: zero errors, zero excluded rows, 6/30 seed groups (270/859 rows)
  held out. Held-out metrics landed in the same rough range as the toy's own
  published numbers without literally matching them (expected, different
  data): Enablement exact 0.619/AUC 0.759/QWK 0.421; Legitimization exact
  0.551/AUC 0.678/QWK 0.329; final-label F1 0.836/precision 0.815/recall
  0.858. In-sample metrics near-perfect as expected (training fit, not
  generalization). Full report: `scripts/is9_real_data_metrics.json`.

  Given three options (leave IS-9 open indefinitely / close it as satisfied
  by adjacent data / track the run as a separate untracked item), **user
  chose: close IS-9**, recorded as **D-34**. Explicit in both `D-34` and
  `VERIFICATION.md`'s updated IS-9 entry: this closes the
  mechanism-plus-generalization half of IS-9, but the toy's literal
  reference-number match is **superseded, not achieved** — D-2's amendment
  and D-16's Finding B (both needing the toy's exact numbers) stay
  genuinely unresolved, not silently marked done. `scripts/
  is9_real_data_metrics.json` kept in the repo (not gitignored) as the
  evidence record, per user's choice. **Every implementation slice in
  `VERIFICATION.md`'s backlog is now done, including IS-9.** What remains
  project-wide: the `hrc-train`/`hrc-evaluate`/`hrc-predict` CLI skin, and
  D-32/D-33's small pending code.

- 2026-07-25 — Fix-proposal pass, scope: **P-N1** + **DI-N1** (the two
  remaining Awaiting-User nice-to-have findings). Analyzed each against the
  current code before presenting choices:
  - **P-N1** (`rule_reasons` vocabulary): inspecting `score_row` showed
    D-4's and D-18's short-circuits aren't symmetric — D-18's
    `not_required` already leaves `legitimization_predicted: None`, fully
    self-explanatory with no reason string needed, while D-4's
    `score_zero` leaves a plain `0` indistinguishable in `predictions.csv`
    from a genuine model prediction of 0 (`component_effective` isn't in
    `PREDICTIONS_COLUMNS`). User chose the recommended option: add a
    reason string for D-4's short-circuit only, not D-18's. Locked as
    **D-32**.
  - **DI-N1** (`qwk`'s undefined-metric convention): `_safe_auc` already
    guards the single-class case and returns `None`; `cohen_kappa_score`
    (`qwk`) has no equivalent guard and returns a raw `NaN`, which would
    reach `metrics.json` as an invalid-strict-JSON token once
    `hrc-evaluate` is built. User chose the recommended option: convert
    `qwk`'s `NaN` to `None`, mirroring `auc`. Locked as **D-33**.

  Both decisions record the choice only — **implementation is not yet
  landed** for either (a one-line addition in `score_row`'s `score_zero`
  branch for D-32; an `np.isnan` guard in `component_metrics` for D-33,
  mirroring `_safe_auc`'s existing shape). Not queued as implementation
  slices yet, per META_PLAN §5's user-owns-ordering rule — both are small
  enough to fold into whichever slice touches those functions next (e.g.
  the `hrc-evaluate`/`hrc-predict` CLI skin), or can be done standalone.

  **The Awaiting-User list is now fully empty.** What's left project-wide
  is unchanged: the `hrc-train`/`hrc-evaluate`/`hrc-predict` CLI skin, D-32/
  D-33's small pending implementations, and IS-9 (blocked on real data).

- 2026-07-25 — Fix-proposal + implementation slice, scope: **D-31** +
  **IS-11** — `model.py`'s `HazardResponseClassifier.score`/`PredictRow`/
  `RowResult` (`VERIFICATION.md` IS-11; user-directed "continue with Phase
  5" following IS-10's no-finding pass; the last slice in the entire
  backlog besides IS-9). IS-11's own entry explicitly named a pre-flagged
  Open Question (`PLAN.md` §11 item 5, critique P-N2: the `score(rows)`
  single-row error contract, "not settled... deferred until the API is
  actually built") and instructed "build the API and surface that decision,
  do not invent it" — asked the user directly before writing any code
  rather than guessing or deferring past the point where a real design
  choice was unavoidable. User chose the recommended option: never raise;
  return exactly one `RowResult` per input row (matching D-14/D-22's
  established never-abort philosophy for the batch paths), recorded as
  locked **D-31**. Concurrency safety, named in the same open question,
  remains genuinely unverified and is documented as such in `score`'s own
  docstring — not tested, not assumed either way.

  Built `HazardResponseClassifier.score` as a method (matching `PLAN.md`'s
  own naming, not a free function) plus `PredictRow` (raw prompt/response
  text — unlike `score_row`'s already-pooled features, this is the
  production-facing input shape) and `RowResult`. Internally: preprocess
  (`preprocess/*`, already built) → one batched `embed.embed_sentences` call
  across every row's segments together (not one call per row, matching the
  batching discipline already established in the IS-9 mechanism test) →
  `embed.pool_response_vector` per row per component → `score_row` (IS-7),
  catching `HardFailError` into a `RowResult` rather than propagating it.
  Heavy imports (`embed.py`, therefore `torch`/`sentence-transformers`) are
  deferred to inside the method, so importing `hazard_classifier.model`
  itself still never requires them — only actually calling `.score()` does.

  **Made "BGE model loaded once" (`PLAN.md` §6) a real, tested property, not
  just a docstring claim:** added `@functools.lru_cache` to `embed.py`'s
  `_load_model`; a new forcing-function test calls `.score()` twice and
  checks `_load_model.cache_info()` directly (one miss on the first call, a
  hit on the second, no second miss) rather than just asserting the calls
  didn't error.

  **Fix found while building this slice, same pattern as IS-7's
  `specialized_advice_hazards` gap, not a new decision:**
  `HazardResponseClassifier` had no record of which BGE model/revision it
  was actually fit against — `.score()` needs to load the *same* model a
  caller embedded training data with (D-23's "predict-time embeddings must
  match training, never overridden" principle), but there was no frozen
  source for it beyond a hardcoded default that could silently diverge from
  the real one. Fixed the same way as the earlier gap: added
  `embedding_model_name`/`embedding_model_revision` fields to
  `HazardResponseClassifier`, matching `fit` keyword parameters (default
  `config.DEFAULT_EMBEDDING_MODEL_NAME`/`None`), round-tripped through
  `manifest.json` by `save`/`load`. Moved the default model-name constant
  out of `embed.py` into `config.DEFAULT_EMBEDDING_MODEL_NAME` (which
  `embed.py` now imports) specifically so `model.py` can reference the
  default without pulling in `torch`/`sentence-transformers` for every
  caller that only ever fits/scores against synthetic feature arrays (which
  is every other test in this project). Added a round-trip assertion to the
  existing IS-5 artifact test confirming the exact model+revision survives
  save→load.

  2 new tests in `tests/integration/test_score_api.py` (125 total, zero
  regressions, real BGE, first run needs network/download, cached after): a
  **mixed batch** (a scoreable `hte` row, a genuinely unseen hazard, and an
  enablement-only `prv` row, all in one `.score()` call) never raises and
  returns exactly 3 `RowResult`s in input order, each shaped correctly (the
  unseen row has `scored=None`/`failure_reason="unseen_hazard"`; the `prv`
  row's `legitimization_predicted is None`, D-18, confirmed even through
  this higher-level raw-text API, not just via `score_row` directly); the
  model-caching forcing function described above. Added "Implementation
  slice landed" notes to `DECISIONS.md` D-23 (embedding model now frozen
  too, mirroring the hazard-family-set precedent).

  **This closes every implementation slice in `VERIFICATION.md`'s backlog
  except IS-9**, which remains open and blocked on real labeled data that
  does not exist in this environment — not a code gap, a data gap. What
  remains project-wide: the actual `hrc-train`/`hrc-evaluate`/`hrc-predict`
  argparse CLIs + file I/O (a thin wrapper around logic that is now fully
  built and tested), and IS-9 itself if/when real data becomes available.

- 2026-07-25 — Implementation slice, scope: **IS-10** — `model.py`'s
  `predict_rows`/`PREDICTIONS_COLUMNS`/`FAILURES_COLUMNS`/
  `to_predictions_frame`/`to_failures_frame` (`VERIFICATION.md` IS-10;
  user-directed "continue with Phase 5, pause after IS-10 if there are any
  additions to Awaiting User"). Built `predict_rows` architecturally
  mirroring `evaluate_rows` exactly: reuses `score_row` per row and catches
  `HardFailError`, but routes the row to a `failures` list (D-22) instead of
  an exclusion counter (D-14) — same shared predicate as `hrc-evaluate`,
  the other consequence, matching `PLAN.md` §6's own framing of the two
  paths. `PREDICTIONS_COLUMNS`/`FAILURES_COLUMNS` pin §6's exact per-row
  output order and D-25's corrected `failures.csv` shape (`prompt_uid,
  hazard, failure_reason` — no `seed_prompt_id`, Finding C).
  `to_predictions_frame`/`to_failures_frame` build a `pandas.DataFrame` with
  these columns explicit even for an empty row list, since `pd.DataFrame([])`
  alone has no columns for `to_csv` to derive a header from. 6 new tests in
  `tests/unit/test_model_predict.py` (123 total, zero regressions): unseen
  hazard → `failures` with `failure_reason == "unseen_hazard"`; a genuinely
  skipped Legitimization cell (the same single-class fixture construction as
  IS-6/IS-8) → `"skipped_or_absent_cell"` — both of D-25's two reasons
  confirmed by value, not just "some failure happened"; a scoreable row →
  `predictions` with every expected field/type; a **mixed batch** (scoreable
  + both failure kinds together) → `len(predictions) + len(failures) ==
  len(input rows)` with every `prompt_uid` accounted for exactly once — the
  real D-22 forcing function, not three isolated single-row tests; columns
  exact and `seed_prompt_id` absent from both; and an actual file
  write/read-back proving an empty batch's CSVs still carry a header, not
  just an empty file. Added "Implementation slice landed" notes to
  `DECISIONS.md` D-22 and D-25. **No new Awaiting-User finding** — the
  design reused already-built, already-tested pieces with no fresh judgment
  calls (the `rule_reasons` CSV join delimiter, `"|"`, matches the
  convention `flags.py`'s `wrapper_label`/`disclaimer_label` already use,
  not a fresh choice) — so per the user's instruction, work is **not**
  paused here. **Phase 5's logic is done; only IS-11 remains in the entire
  `VERIFICATION.md` backlog** (plus the still-open IS-9 and the
  argparse/file-I/O CLI skin for all three commands).

- 2026-07-25 — Investigation + implementation slice, scope: **IS-9 attempt**
  → **`embed.py`** (`VERIFICATION.md` IS-9; user-directed "proceed IS-9"
  after Phase 4's logic (IS-7/IS-8) was done). Before writing any harness
  code, checked what IS-9 would actually need: read the `security-evaluator`
  toy repo directly rather than assuming. Found its own `inputs/README.md`
  states plainly "Do not commit source CSV data into this folder... provide
  the files at run time" — confirmed by `find`/`ls` that neither
  `neyman_review_queue.csv` nor any `batch_*_key.csv` exists anywhere in this
  environment, and that the toy's BGE hazard-weighted run's own output
  directory (`results/mechanism_sentence_bge_base_hazard_weighted_heads_v1/`)
  is likewise absent — only four unrelated `results/` subdirectories exist.
  The reference numbers `PLAN.md` §8.2 quotes **are** real (found in the
  toy's own `README.md` "Expected Checks" table, matching exactly:
  Legitimization exact 0.645503/AUC 0.808393/QWK 0.522552; Enablement exact
  0.592040/AUC 0.782737/QWK 0.411720) — but there is no input data anywhere
  to reproduce a run from. This is a **data gap, not a code gap**: installing
  `sentence-transformers`/`torch` and writing `embed.py` cannot fix it, since
  there would be nothing to embed. Surfaced this to the user with three
  options (provide real data / build `embed.py` now and defer the actual
  parity check / skip to Phase 5's IS-10) rather than attempting a harness
  that could not succeed, or fabricating placeholder reference numbers.
  **User chose: build `embed.py` now, defer the real parity check.**

  Verified feasibility first (network access to `huggingface.co` works in
  this environment; 230GB disk free) before proceeding. Added `torch` +
  `sentence-transformers` to `pyproject.toml`'s main dependencies (D-6:
  CPU-only) and installed them (a real, multi-package download — flagged to
  the user as a substantial environment change before running it). Built
  `src/hazard_classifier/embed.py`: `embed_sentences` (loads a real
  `BAAI/bge-base-en-v1.5` via `sentence-transformers`, `device="cpu"` always,
  no auto-select, ported from the toy's `load_model`/`encode_texts`;
  offline-by-default via `local_files_only=not allow_download`, matching the
  shared `--allow-download` convention already used elsewhere; returns an
  empty array without loading the model at all for an empty sentence list);
  `enablement_keep_mask` (ported from the toy's `effective_indices` — drop a
  sentence only when prompt-repetition-only **and** no later-authored
  continuation); `pool_response_vector` (ported from `aggregate_for_response`'s
  `"mean"` mode — the toy's `"max"`/`"mean_max"` modes aren't reproduced since
  no locked decision names them as the production default; returns
  `(vector, effective)`, matching the `component_effective` contract `fit`/
  `score_row` have expected since IS-4, with `effective=False`'s vector an
  unread placeholder). 5 new no-network unit tests
  (`tests/unit/test_embed.py`, pure pooling logic) plus one new
  `tests/integration/test_pipeline_mechanism.py` — a new test category
  (needs network on first run only, model cached after; kept out of
  `tests/unit/` per `PLAN.md` §8.1's "unit tests need no model download"
  rule) that builds a small synthetic 10-row fixture, runs real text through
  already-built `preprocess/*` (decode/segment/flags), embeds every segment
  with one real, downloaded BGE call, pools per component, and feeds the
  result through `fit`/`save`/`load`/`score_row` end-to-end — confirmed to
  pass (16.97s including the one-time model download). **This proves the
  pipeline's mechanism works end-to-end against a real model — it is
  explicitly not a parity or science confirmation**; the specific predictions
  on a 10-row synthetic fixture aren't meaningful science and aren't asserted
  as such. 117 tests total (was 111), zero regressions. Added "Implementation
  slice landed" notes to `DECISIONS.md` D-6 (CPU-only, now exercised by a
  real model) and D-2 (the IS-9 blocker, spelled out precisely so a future
  session doesn't have to re-derive it). **IS-9 itself remains genuinely
  open** — not unstarted, but blocked on real labeled data that does not
  exist in this environment; revisit if/when it becomes available. Next per
  `VERIFICATION.md`'s execution order is IS-10 (Phase 5), which — like
  IS-7/IS-8 — needs no real data.

- 2026-07-25 — Fix-proposal + implementation slice, scope: **D-30** +
  **IS-8** — `schema.py`'s `parse_is_safe_ground_truth` and `model.py`'s
  `evaluate_rows`/`BlankGroundTruthError` (`VERIFICATION.md` IS-8;
  user-directed "do all Phase 4 items in order," second item, immediately
  after IS-7). Before writing `evaluate_rows`, hit a real blocker: `metrics.py`'s
  `final_label_metrics` needs `is_safe_ground_truth` as a boolean, and its
  literal CSV encoding had been an unresolved Open Question since IS-1 — not
  a stylistic gap anymore, a hard prerequisite. Asked the user directly
  rather than guessing (a wrong guess would silently invert every
  final-label metric); user answered `"safe"`/`"unsafe"`, recorded as locked
  **D-30**. Added `schema.py`'s `parse_is_safe_ground_truth` (case-sensitive
  exact match, raises for anything else). Built `model.py`'s `evaluate_rows`:
  catches `score_row`'s `HardFailError` per row and tallies D-14's excluded-
  row breakdown (`excluded_unseen_hazard_count`/`excluded_skipped_cell_count`)
  **before** any ground-truth column is read — this ordering is what makes
  Finding A (a blank label on an excluded row never aborts) true by
  construction rather than a separate check that could drift out of sync.
  Surviving rows go through D-26's family-aware blank-label validation via a
  new `BlankGroundTruthError` — a **whole-run abort**, deliberately distinct
  from `HardFailError`'s per-row **exclusion** (the user's original "error
  over exclude" choice for this specific case, D-26). Partitions via
  `metrics.py`'s already-built `partition_by_holdout` (D-13), warning when no
  holdout was recorded. Assembles each non-empty population's metrics via
  `metrics.py`'s already-built `component_metrics` (Enablement unfiltered,
  Legitimization filtered through `legitimization_eligible_mask`, D-15) and
  `final_label_metrics` (D-17), feeding `ScoredRow`'s `*_adjusted_high`
  fields as D-16's AUC input. **Read D-13's own text literally** ("reported...
  whenever both are non-empty") to decide an empty population's key is
  *omitted* entirely, not emitted as a hollow null object — a direct
  application of already-locked wording, not a fresh guess. 6 new tests in
  `tests/unit/test_model_evaluate.py` (111 total, zero regressions): excluded
  row never enters either population's `n_rows`; empty holdout → warning +
  everything in `in_sample_unrecorded` with **no `held_out` key at all**;
  blank label on an *unseen* hazard → excluded, no exception (**Finding A**,
  the single most important ordering test); blank label on a *known,
  non-enablement-only* hazard → `BlankGroundTruthError` (proving exclude vs.
  abort are genuinely two different code paths, not just two descriptions of
  one); blank Legitimization tolerated for an enablement-only hazard
  (`components.legitimization.n == 0`); full `metrics.json` shape (exact key
  sets at every level, every population). **Fix found while implementing,
  not a new decision:** `ScoredRow` (IS-7) had no way to report the
  business-rule-*adjusted high* probability D-16's AUC actually needs (only
  the discrete prediction and the mean-combined score existed) — added
  `enablement_adjusted_high`/`legitimization_adjusted_high` fields to
  `ScoredRow`, populated in `score_row` alongside the existing ones, plus a
  new IS-7 test confirming the disclaimer rule zeroes this value too, not
  just the ordinal prediction. Added "Implementation slice landed" notes to
  `DECISIONS.md` D-13, D-14, D-15, D-16, D-17, D-26, and the new **D-30**.
  **This closes Phase 4's logic** (IS-7 + IS-8); only the argparse/file-I/O
  CLI skin remains, deliberately deferred (a literal CLI script that can't
  run against real data without `embed.py` would be a premature, untestable
  stub — same reasoning as every prior `embed.py` deferral). Next per
  `VERIFICATION.md`'s execution order is **IS-9** (the parity harness) — the
  first check that genuinely needs `embed.py` and a real trained artifact.

- 2026-07-25 — Implementation slice, scope: **IS-7** — `rules.py`'s
  `apply_legitimization_disclaimer_rule`/`discrete_v14_label`/
  `v14_overall_score`/`combined_component_score` and `model.py`'s `score_row`
  (`VERIFICATION.md` IS-7; user-directed "do all Phase 4 items in order,
  pause after a step if it results in a new Awaiting User item" — first item
  in the new phase). Read the toy's `apply_component_business_rules`/
  `v14_overall_score`/`discrete_v14_label`/`score_from_centered_probs`
  (`scoring_common.py` L471-472, L583-647) before writing code. Ported only
  the disclaimer rule into `rules.py` — the toy's other two business rules
  have no live call site (Rule 1 subsumed by D-18's cell-never-enumerated;
  Rule 3 subsumed by D-4's pre-head zero score) — plus `discrete_v14_label`/
  `v14_overall_score`/`combined_component_score`, all taking an
  already-resolved `HazardFamily` rather than re-deriving it, since the
  caller (`score_row`) already computes it once for Step 0. Built
  `model.py`'s `score_row`: reuses `resolve_component_action` (already built,
  D-3/D-4/D-11/D-18/D-20) unchanged rather than re-deriving cell-status
  logic, composes the disclaimer rule + `ordinal_prediction`'s gate on the
  **adjusted** probabilities (D-19) + the v1.4/v14 combination. Added
  `HardFailError`, raised for `fail_unseen_hazard`/`fail_skipped_cell` rather
  than deciding a consequence — routing hard-fail rows (D-22's `failures.csv`
  vs. D-14's exclude-from-metrics) is `hrc-predict`/`hrc-evaluate`'s job
  (IS-8/IS-10), not this function's. 6 new tests in
  `tests/unit/test_model_score_row.py` (105 total, zero regressions): the
  **IC-1(a) trace end-to-end** through a real `fit()`-trained classifier
  (specialized-advice + disclaimer + Enablement-repetition-only → "safe");
  the disclaimer rule proven non-vacuous by comparing the same probe
  with/without a disclaimer sentence; a `not_required` component reads
  `None`; `HardFailError` for an unseen hazard and separately for a
  genuinely skipped cell; and **D-21's independence property**, tested via a
  hand-constructed `Cell` (a degenerate `BinaryHead` with `center_mean=0.5`,
  giving an exact, fully controlled centered value — `0.6`/`0.3` for
  nonzero/high, crossing one threshold but not the other) rather than a real
  fit, since a real logistic fit can't be guaranteed to land exactly on a
  "crossed nonzero but not high" boundary: confirmed `discrete_v14_label`
  says "safe" while `v14_overall_unsafe_score` is a non-trivial `0.45` — a
  verified disagreement, not an inference from reading the two formulas.
  **Fix found while building this slice, not a new decision:**
  `HazardResponseClassifier` had no `specialized_advice_hazards` field at
  all — IS-5's `save` froze it into `rules.json` but never read it back, and
  `fit` had no parameter to set it, so `score_row`'s own family lookup had no
  frozen source for this second set. Fixed: added the field, a matching
  keyword parameter on `fit` (unused for cell enumeration, D-18 only names
  the enablement-only set, but threaded through so the object is
  self-describing after either `fit` or `load`), and `load` now populates
  it; removed the now-redundant parameter from `save`. Updated the three
  affected IS-5 tests (one assertion had to change to reflect D-27's
  "exactly trained hazards" principle applying to this set too — a
  fixture's `spc_fin` wasn't a trained hazard, so it's correctly dropped by
  the round trip, not preserved verbatim). Added "Implementation slice
  landed" notes to `DECISIONS.md` D-19, D-21, and D-23 (the
  `specialized_advice_hazards` gap). **IS-7 raised no new Awaiting-User
  finding** — per the user's instruction, work continues to IS-8 without
  pausing.

- 2026-07-25 — Implementation slice, scope: **IS-6** — `model.py`'s D-28
  train-time gate (`VERIFICATION.md` IS-6; user-directed "do all Phase 3
  items in order," fourth item, following IS-5 with no pause since IS-5
  raised no new finding). Built directly into `fit`, right after each
  component's cell-fitting loop: a wholly-skipped **Enablement** raises a new
  `WhollySkippedEnablementError` immediately (before Legitimization's loop
  even runs — no deployable classifier exists to keep building toward,
  D-18); a wholly-skipped **Legitimization** emits
  `warnings.warn(..., UserWarning)` and `fit` returns normally, exactly as
  before. 3 new tests in `tests/unit/test_model_train_gate.py` (99 total):
  single-class-Enablement fixture raises; single-class-Legitimization
  fixture warns (`pytest.warns`) and still produces a classifier whose
  Enablement cells are fit normally for every hazard — confirmed as a
  genuinely usable enablement-only-workload artifact, not just "didn't
  crash." **Cross-check finding, fixed in passing, not a new decision:** two
  pre-existing tests (`test_model_fit.py`'s
  `test_single_class_enablement_labels_mark_every_enablement_cell_skipped`,
  `test_model_artifact.py`'s
  `test_skipped_components_rollup_matches_per_cell_status_across_files`) had
  used a single-class-**Enablement** fixture to exercise D-5's per-cell skip
  marking in isolation, written during IS-4/IS-5 before this gate existed —
  once IS-6 landed, that identical fixture started raising
  `WhollySkippedEnablementError` instead of the "marked skipped, no raise"
  behavior those tests asserted, and both went red. Fixed by switching both
  to a single-class-**Legitimization** fixture instead (D-5's marking
  mechanism is component-symmetric, so the substitution preserves each
  test's original intent rather than papering over the interaction).
  Renamed the first to `test_single_class_labels_mark_every_cell_of_that_
  component_skipped` to reflect that it no longer targets Enablement
  specifically. Added an "Implementation slice landed" note to `DECISIONS.md`
  D-28, including this cross-check finding. Full suite green: 99 tests
  (was 96), zero regressions. **This completes Phase 3** (IS-3 through IS-6
  all done) — `VERIFICATION.md`'s recommended execution order moves to
  Phase 4 (IS-7 onward, the predict/evaluate pipeline) next.

- 2026-07-25 — Implementation slice, scope: **IS-5** — `model.py`'s artifact
  `save`/`load` (`VERIFICATION.md` IS-5; user-directed "do all Phase 3 items
  in order," third item, resumed after D-29 resolved IS-4's finding). Built
  against the §4 format: `heads.npz` (every cell's two `BinaryHead`s
  flattened via a deterministic `_head_array_key(component, hazard,
  head_type, field)` helper, built and rebuilt from `thresholds.json`'s cell
  list and **never parsed** out of a key string — avoids any ambiguity from a
  hazard code containing an underscore); `thresholds.json` (nested
  `{component: {hazard: {status, thresholds, threshold_metrics}}}`);
  `rules.json` (`trained_hazards`, a `hazard_family` map, and both
  hazard-family sets intersected with `trained_hazards`, D-27); `manifest.json`
  (`holdout_seed_prompt_ids`, `skipped_components` — the fuller manifest
  spec's remaining fields, embedding model id/revision, hyperparameters,
  timestamp, training-file hash, are deliberately deferred to whichever slice
  wires up the full `hrc-train` CLI, since those values don't exist at this
  layer). Added `rules.hazard_family` (ported from the toy's
  `hazard_rule_family`, `scoring_common.py` L567-580, narrowed to this
  project's two locked families — the toy's `defamation`/`content_as_harm`/
  `cse` families aren't part of this project's schema). `save` takes
  `specialized_advice_hazards` as its own parameter rather than threading it
  through `fit` (which never uses it, D-18 only names the enablement-only
  set) — avoids a dead parameter on the more heavily-used function. 4 new
  tests in `tests/unit/test_model_artifact.py` (96 total): save→load
  round-trip gives bit-identical `predict_proba_centered` output and
  exactly-equal thresholds for every cell (D-6 determinism); `rules.json`'s
  `hazard_family` key set equals `trained_hazards` exactly (D-27);
  `skipped_components` matches a from-scratch recomputation over
  `thresholds.json`'s per-cell `status` — a genuine cross-file consistency
  check (D-28); and the **IS-C-completing forcing function** — froze an
  `enablement_only_hazards` set disagreeing with installed
  `config.ENABLEMENT_ONLY_HAZARDS` in both directions (added "hte", omitted
  "prv"), saved, reloaded, and confirmed `is_required_component` fed the
  *loaded* set disagrees with the same call fed installed config in both
  directions, and that cell enumeration itself followed the loaded set (no
  `("legitimization","hte")` cell; a real `("legitimization","prv")` cell).
  Used a dedicated fixture with real (non-blank) legitimization ground truth
  for both hazards in this one test, rather than reusing the shared
  `_make_fixture`'s "prv" blank-legitimization convention, since flipping
  which hazard is enablement-only would otherwise have hit D-29's
  natural-`ValueError` path — a distraction from what this test is actually
  checking. Added "Implementation slice landed" notes to `DECISIONS.md`
  D-13, D-23 (closes it end-to-end), and D-27. Full suite green: 96 tests
  (was 92), zero regressions. **This closes IS-C/IS-C2/IS-C3's remaining
  full-artifact-wiring gap** that IS-C/IS-C2/IS-C3 (unit level) and this
  slice (artifact level) together now fully cover.

- 2026-07-25 — Fix-proposal, scope: the IS-4 blank-`legitimization_value`
  finding (posed as three options in this file's own Awaiting User section
  moments earlier). User chose option 1: "leave the natural ValueError
  as-is." Recorded locked **D-29** — no code change, since
  `src/hazard_classifier/model.py`'s `fit` (IS-4) already produces exactly
  this behavior; this decision only ratifies it as intentional. Noted the
  resulting asymmetry with D-26 (`hrc-evaluate` raises a purpose-built error
  for the analogous condition; `hrc-train` raises Python's built-in one) as
  accepted, not an oversight. Checked against the full ledger: no conflict
  (different code path than D-26; no other entry addresses train-time
  ground-truth conversion). This closes the Awaiting User item the user
  asked to pause on — clearing the way to resume Phase 3 (IS-5 next).

- 2026-07-25 — Implementation slice, scope: **IS-4** — `model.py` `fit`
  (`VERIFICATION.md` IS-4; user-directed "do all Phase 3 items in
  VERIFICATION.md in order," second item after IS-3). Read the toy's
  per-target-hazard weighted head fit loop
  (`run_bge_hazard_weighted_heads.py` L200-306) before writing code, and
  confirmed the toy's grouped-CV fold apparatus around it is exactly the
  research reporting D-12 already dropped from scope — so `fit` fits each
  `(component, hazard)` cell **once** on the whole non-holdout population,
  not per-fold. Built `src/hazard_classifier/model.py`: `choose_holdout_seed_
  prompts` (D-1 — a simplified port; seed-prompt-level fraction only, since
  the toy's response-count target existed purely to serve its now-dropped
  grouped-CV apparatus, D-12) and `fit(df, component_features,
  component_effective, enablement_only_hazards, ...)`. Cell enumeration
  reuses `rules.py`'s already-built `is_required_component` (D-18) for both
  the enumeration loop and the fit-row mask, so D-18's exclusion and D-7's
  "identical mean/scale across hazards" guarantee share one code path.
  **New layering contract (documented in `model.py`'s own docstring, not a
  locked decision — internal interface, not externally-visible behavior):**
  `fit` takes already-pooled per-component feature matrices and an explicit
  per-component `component_effective` boolean mask (D-4), not raw text or an
  implicit "all-NaN row" convention — deliberately explicit so a real
  embedding bug elsewhere is never silently misread as an intentional
  exclusion. Whichever future slice builds `embed.py`/pooling must satisfy
  this contract. D-5's whole-component skip trigger needed **zero new
  aggregation logic**: since every hazard's cell fit within a component
  shares the identical row-level label array (only `sample_weight` varies),
  `heads.py`'s own per-call degeneracy check independently reaches
  `status="skipped"` for every hazard automatically when the labels are
  genuinely single-class — this was verified, not just inferred, by the
  test below. D-10's gate and D-2's `n_own>=5` cliff reuse `rules.py`'s
  `optimize_ordinal_thresholds` directly. 6 new tests in
  `tests/unit/test_model_fit.py` (92 total, zero regressions), the
  strongest a genuine forcing function: corrupted the ground-truth labels
  *and* features for exactly the held-out rows, refit, and confirmed every
  fitted parameter (`mean`, `coef`, both thresholds) came back bit-identical
  — proving D-1's exclusion is real, not just a recorded id list. Also:
  single-class `enablement_value` across both fixture hazards marks every
  enablement cell skipped and adds `"enablement"` to `skipped_components`
  while leaving `legitimization` alone (D-5); no `("legitimization", "prv")`
  cell exists for the enablement-only hazard while `("enablement", "prv")`
  does (D-18); `mean`/`scale` identical across hazard cells confirmed through
  the full `fit()` call, not just `heads.py` in isolation (D-7); default
  `holdout_seed_fraction=0` → `[]` (D-1); `choose_holdout_seed_prompts`
  determinism directly. Added "Implementation slice landed" notes to
  `DECISIONS.md` D-1, D-2 (partial — the `n_own>=5` cliff is built but not
  yet separately boundary-tested), D-5, D-18, and D-4 (fit-time half only;
  predict-time half is still IS-7). **New finding surfaced while
  implementing, added to Awaiting User (not resolved silently):** a blank
  `legitimization_value` on a non-enablement-only hazard training row (a data
  defect `schema.py` deliberately doesn't reject at load time) currently
  raises a raw `ValueError` from `int("")` inside `fit`'s label conversion —
  no locked decision covers this train-time case (D-26 pins only the
  analogous `hrc-evaluate` condition, to *error*). **Per the user's explicit
  instruction this pass, pausing here rather than starting IS-5.**

- 2026-07-25 — Implementation slice, scope: **IS-3** — `heads.py`
  `BinaryHead`/`fit_binary_head` (`VERIFICATION.md` IS-3; user-directed
  "execute the next item in the queue" following IS-2, with the queue itself
  empty — read `VERIFICATION.md`'s recommended execution order to determine
  IS-3 was the natural next pick, per META_PLAN §5's queue-ordering note that
  an empty queue plus explicit user direction to proceed is not the same as
  silently reordering). Read the toy's `standardize_train_test`/
  `fit_binary_head_weighted` (`run_bge_hazard_weighted_heads.py` L70-110) and
  `logit`/`sigmoid`/`centered_probability` (`scoring_common.py` L412-423)
  before writing code. Built `src/hazard_classifier/heads.py`: a `BinaryHead`
  dataclass (`mean, scale, coef, intercept, constant_probability,
  center_mean, status`) with `predict_proba`/`predict_proba_centered`
  methods and `to_arrays`/`from_arrays` for `.npz` round-tripping (§4
  `heads.npz`), per §2.3's refactor away from the toy's five-parallel-array
  plumbing. `fit_binary_head(x, y, sample_weight, *, seed=DEFAULT_SEED)` —
  added `config.DEFAULT_SEED = 20260628` (ported from the toy) alongside the
  existing hazard-family sets — deliberately takes **no hazard parameter at
  all**, confirmed by a signature-inspection test, so D-7/D-18's
  Legitimization enablement-only-hazard exclusion cannot be applied or
  skipped by this module; it is entirely the caller's job (`model.py`'s
  `fit`, IS-4, not built this pass). **Deliberate implementation choice
  beyond a literal port, recorded in the module's own docstring:**
  `center_mean` is computed from `BinaryHead.predict_proba`'s own formula
  (not sklearn's `predict_proba` directly, which the toy uses for this one
  value) so a head's centering stays self-consistent with what it reports
  even after a save/load round-trip — a risk the toy's structure never had
  to consider since it never serializes a head and reloads it later. 7 tests
  in `tests/unit/test_heads.py` (86 total, zero regressions): `logit`/
  `sigmoid`/`centered_probability` against hand-computed values; degenerate
  single-class labels produce a `status="skipped"` constant head whose
  `predict_proba_centered` collapses to exactly `0.5` everywhere; save→load
  round-trip gives bit-identical `predict_proba_centered` for both a fit and
  a skipped head. **Two forcing functions confirmed by actually running
  things, not assumed:** (1) a first-draft "mean/scale identical across
  hazard weightings, coef/center differ" test used a cleanly-separable
  two-cluster fixture and came back with **identical coefficients under both
  weightings** — investigated and found this is because a uniform per-class
  reweighting of perfectly-separable data selects the same max-margin
  separator regardless of which class is up-weighted, making the original
  test vacuous; replaced with a deliberately overlapping, non-class-aligned
  three-hazard-group fixture (labels don't align with hazard identity,
  matching the toy's actual hazard-weighting shape) where the weighting
  genuinely changes the fitted coefficients — confirmed empirically, not
  assumed from the first fixture's superficial pass; (2) a row-set exclusion
  test (simulating D-7/D-18's Legitimization filtering) confirms `mean`/
  `scale` actually change when rows are removed before calling
  `fit_binary_head`, proving the exclusion has no effect unless the caller
  applies it before this function ever sees the data. **This starts Phase
  3** (`heads.py` done; next is IS-4, `model.py`'s `fit`). Added an
  "Implementation slice landed" note to `DECISIONS.md` D-7.

- 2026-07-25 — Implementation slice, scope: **IS-2** — `preprocess/decode.py`,
  `segment.py`, `flags.py` (`VERIFICATION.md` IS-2; top and only item in the
  queue, per `META_PLAN.md`'s "execute the meta-plan" session checklist).
  Read the toy's `build_reviewable_sentence_segments.py` in full (993 lines)
  and its own test file (`test_reviewable_sentence_segments.py`, 6 asserts)
  before writing code, and cross-checked `scoring_common.py`'s
  `effective_indices` to confirm which per-segment flags (`prompt_repetition_flag`,
  `later_response_authored_continuation`, `disclaimer_flag`, `wrapper_flag`)
  a downstream pooling/business-rule layer actually consumes, rather than
  guessing scope from the ledger's paraphrase. Split the toy's single file into
  three pure-function modules exactly matching `PLAN.md` §2.2's package
  layout: `decode.py` (Unicode/zero-width normalization, HTML-entity/
  percent-encoding/escape/base64/ROT13/substitution-cipher decoding scored by
  an English-likeness heuristic, `best_readable_view`), `segment.py`
  (sentence/bullet/code-aware segmentation, returning a `Segment` NamedTuple
  instead of the toy's raw 4-tuples), `flags.py` (wrapper/disclaimer/
  prompt-repetition/later-authored-continuation detection). **Before writing
  any code**, asked the user (via `AskUserQuestion`) which wordlist to bundle
  in place of the toy's opportunistic `/usr/share/dict/words` read
  (D-6-adjacent, §7) — a genuine license/size/provenance tradeoff, not a
  silent implementation detail per META_PLAN §3's uncertainty protocol. User
  chose a filtered snapshot of this machine's own `/usr/share/dict/words`
  (macOS's `web2`, Webster's Second International base; 234,428 entries after
  the toy's own `[a-z]{2,}` filter, ~2.4MB) over a small MIT-licensed
  alternative, on the basis that a 1934-vintage dictionary base is generally
  public domain and is already what the toy would have used on a Mac dev
  box. Recorded the one unverified caveat (this exact file's redistribution
  terms weren't independently re-checked beyond that general assumption) in
  `preprocess/data/WORDLIST_PROVENANCE.md` rather than asserting it as
  settled. `pyproject.toml` gained `[tool.setuptools.package-data]`
  (`hazard_classifier.preprocess = ["data/*.txt"]`); **verified, not assumed**,
  that packaging actually works by running `python -m build --wheel` and
  confirming `data/wordlist.txt` appears in the built wheel's file list, not
  just the editable install (then cleaned up the build artifacts). 20 new
  tests across `tests/unit/test_decode.py`/`test_segment.py`/`test_flags.py`
  (79 total, zero regressions): ported the toy's six existing asserts
  verbatim (base64 decode; code-to-English extraction; the three
  `prompt_repetition_features`/`later_authored_continuation` cases —
  verbatim/decoded, prompt-plus-continuation, topical-overlap-is-not-
  repetition; and the toy's `build_segments`-level composition, reproduced by
  hand in a test since no orchestration function combining these three
  modules exists yet in this codebase — that composition is `embed.py`'s job,
  a later phase, so this test proves the pieces this slice *does* build
  compose correctly without building ahead of scope). Added new tests beyond
  the ported set, two of them genuine forcing functions found by actually
  running things, not just reading code: (1) a first-draft host-independence
  test that grepped the module's source for `/usr/share/dict` failed against
  the module's own docstring (which legitimately discusses the path it
  replaces) — replaced with a structural test that `_load_bundled_wordlist`
  takes no arguments and no toy-style `WORDLIST_PATHS` fallback exists to
  redirect it; (2) a first-draft HTML-entity test using the toy's own literal
  example (`&amp;`) turned out to be a tie that raw text wins on a length
  tiebreak — computed scores directly, found a numeric-entity example
  (`&#112;lease...`) that genuinely flips the winner, and used that instead.
  **Deliberately not ported** (documented scoping decision, recorded in
  `VERIFICATION.md`'s IS-2 entry, not a silent omission): `signal_score`/
  `semantic_signal_score` and `text_hash`/`segment_hash` — grepped
  `scoring_common.py` and confirmed neither is read by any modeling/
  business-rule path (the toy's own docstring calls the signal score "only a
  triage heuristic... not a safety label"), and `PLAN.md` §2.2's `flags.py`
  line names only "prompt-repetition, disclaimer, wrapper flags." **This
  closes Phase 1 entirely** (IS-1 + IS-2); the Queue is empty; next work is
  Phase 3 (`IS-3` onward) per `VERIFICATION.md`'s execution order.

- 2026-07-25 — Implementation slice, scope: **IS-1** — `schema.py`
  (`VERIFICATION.md` IS-1; user-directed "Execute Phase 1" — of Phase 1's two
  items, IS-1 executed in full this pass, IS-2 explicitly deferred, see
  below). Grounded the design in `PLAN.md` §2.1 and the toy's actual
  `normalize_hazard`/ground-truth-column handling (`scoring_common.py`
  L113-114, L140-166) before writing code, rather than working from the
  ledger's paraphrase alone. Built `src/hazard_classifier/schema.py`:
  `SchemaError`; `normalize_hazard` (ported verbatim, D-27); `load_csv(path,
  mode, known_hazards=None)` with mode-scoped required columns (`train`/
  `evaluate` require all eight §2.1 columns; `predict` requires only the five
  core columns, D-24); hazard normalization on every path; train-only
  optional `known_hazards` rejection that **raises** if passed for another
  mode rather than silently no-op'ing (D-27); `{0,1,2}` range-checking of
  **non-blank** `enablement_value`/`legitimization_value` only — never
  rejects a blank at this layer, since D-15/D-18's enablement-only
  legitimization carve-out is family-aware and this layer has no artifact to
  resolve it against (D-26's Finding-A amendment). 14 tests in
  `tests/unit/test_schema.py` (new directory — first `tests/unit/*` file;
  59 total, zero regressions). Two forcing functions verified by actually
  breaking things, not just reading code: (1) sabotaged the range-check's
  accepted-value set in an isolated subprocess and confirmed the two
  out-of-range tests go red under it, proving they're not vacuous; (2) the
  **Finding-A schema-layer forcing function** — an evaluate-mode row with a
  genuinely unrecognized hazard *and* a blank ground-truth label does **not**
  raise, confirming `schema.py` can never itself promote a blank label to a
  run-abort (the full D-14 excluded-not-aborted guarantee still needs IS-8's
  per-row `rules.json` check; this proves schema.py's necessary half of it).
  **Packaging fix, found while adding the new `pandas` dependency:**
  `pyproject.toml` had no `pandas` at all and listed `scikit-learn` only under
  `dev`, even though `metrics.py` (shipped code) already imports
  `sklearn.metrics` directly — `pip install hazard-response-classifier`
  without the dev extra would have failed to import. Fixed: both moved to
  main `dependencies`. **Ledger correction, found while implementing:**
  `DECISIONS.md` D-26's Finding-A amendment (point 4) and `PLAN.md` §2.1 had
  a drafting slip — "any non-blank value in [the three ground-truth columns]
  must be in `{0,1,2}`" read as covering `is_safe_ground_truth` too, which
  isn't an ordinal. Added a correction note to D-26 (not a rewrite — this is
  a factual fix, not a new decision) and corrected the `PLAN.md` prose;
  `schema.py` implements the corrected scope (range-checks the two ordinal
  columns only; `is_safe_ground_truth` gets column-presence-only validation).
  **New Open Question surfaced, not resolved:** `is_safe_ground_truth`'s
  literal string/bool encoding is pinned by no locked decision and by no toy
  behavior (the toy carries it through as an opaque unparsed string,
  `scoring_common.py` L163) — needed before any future code parses it into a
  boolean (`hrc-evaluate`'s `is_safe_true`, `final_label_metrics`'s first
  argument); flagged in `DECISIONS.md` D-26's note and `VERIFICATION.md`, not
  guessed at. `VERIFICATION.md` updated throughout (test count, D-24/D-26/D-27
  coverage rows, IS-1 marked done with full detail, IS-2 scoped precisely with
  the toy's actual line count and feature list, execution-order list).
  **IS-2 deliberately not attempted this pass** — confirmed via `wc -l` that
  the toy's equivalent file (`build_reviewable_sentence_segments.py`) is
  ~1000 lines of deobfuscation/segmentation logic, a large, separate
  undertaking from schema validation; queued explicitly in this file's Queue
  with a precise scope (decode transforms, segmentation, prompt-repetition/
  disclaimer detection, bundled wordlist) rather than rushed into the same
  session as IS-1.

- 2026-07-25 — Implementation slice, scope: **IS-C3** — D-23's frozen-source
  requirement, `metrics.py`'s `final_label_metrics`, unit level
  (`VERIFICATION.md` IS-C3; top and only item in the queue, user-directed).
  Same shape as IS-C/IS-C2: removed the module's last remaining
  `hazard_classifier.config` import (`SPECIALIZED_ADVICE_HAZARDS`);
  `final_label_metrics` now takes `specialized_advice_hazards:
  AbstractSet[str]` as a required parameter with **no default**. Confirmed
  the signature change broke all four existing call sites first (`TypeError:
  final_label_metrics() missing 1 required positional argument`) before
  updating any of them, using a local `_SPECIALIZED_ADVICE` test fixture
  (`{"spc_ele", "spc_fin", "spc_hlt", "spc_lgl"}`, matching config's real
  values but not imported from it — same fixture discipline as IS-C/IS-C2).
  Added the forcing-function test,
  `test_final_label_metrics_uses_the_passed_set_not_installed_config`
  (mirrors IS-C/IS-C2 exactly): a frozen set disagreeing with installed
  config in both directions (`"hte"` newly specialized-advice per the frozen
  set though absent from config; `"spc_fin"` present in config but excluded
  from the frozen set), confirmed the passed set's answer wins both times.
  Full suite green: 45 tests (was 44), zero regressions. Added a third
  "Implementation slice landed" note to `DECISIONS.md` D-23. **Verified the
  closure claim before writing it down** — grepped all of `src/` for any
  `from hazard_classifier.config import` outside `config.py` itself: none
  found. `src/hazard_classifier/metrics.py` no longer imports
  `hazard_classifier.config` at all, and neither does `rules.py` — **this
  closes the entire IS-C → IS-C2 → IS-C3 chain** D-23's implementation
  surfaced across this session's last three items. `VERIFICATION.md` updated
  throughout (test count, D-23 coverage row now shows all 3 call sites green,
  IS-C3 marked done, "Current implementation state" notes zero known code
  gaps remain in the built modules, execution-order list). **The Queue is now
  empty** — every "do now" slice against already-built code is landed;
  remaining confirmation needs new pipeline builds (Phase 1 onward) or the
  full-wiring dependencies (IS-5, IS-8) already named in each slice's notes.

- 2026-07-25 — Implementation slice, scope: **IS-C2** — D-23's frozen-source
  requirement, `metrics.py`'s `legitimization_eligible_mask`, unit level
  (`VERIFICATION.md` IS-C2; top and only item in the queue). Same shape as
  IS-C: removed the `from hazard_classifier.config import
  ENABLEMENT_ONLY_HAZARDS` import; `legitimization_eligible_mask` now takes
  `enablement_only_hazards: AbstractSet[str]` as a required parameter with
  **no default**. Confirmed the signature change broke all three existing call
  sites first (`TypeError: legitimization_eligible_mask() missing 1 required
  positional argument`) — in the test file's direct test, in
  `test_component_metrics_n_reflects_the_passed_row_count` (from the IS-B
  pass), and in the D-15 integration test — before updating any of them, using
  a local `_ENABLEMENT_ONLY` test fixture (not imported from config, mirroring
  IS-C's fixture discipline). Added the actual forcing-function test,
  `test_legitimization_eligible_mask_uses_the_passed_set_not_installed_config`
  (mirrors IS-C's exactly): a frozen set disagreeing with installed config in
  both directions, confirmed the passed set's answer wins. Full suite green:
  44 tests (was 43), zero regressions. Added a second "Implementation slice
  landed, partially" note to `DECISIONS.md` D-23 (appended after IS-C's,
  recording the same decision landing at a second call site). **New finding
  surfaced while implementing, not fixed in this pass:**
  `final_label_metrics` in the same file still imports
  `SPECIALIZED_ADVICE_HAZARDS` directly from config to exclude
  specialized-advice hazards from the final-label headline — the identical
  D-23 pattern at a third call site, outside this item's declared scope (which
  named only `legitimization_eligible_mask`). Recorded in `DECISIONS.md`
  D-23's note, queued as new item **IS-C3** in both `VERIFICATION.md` and this
  file's Queue, rather than silently expanded into. `VERIFICATION.md` updated
  throughout (test count, D-23 coverage row, IS-C2 marked done + IS-C3 added,
  execution-order list).

- 2026-07-25 — Implementation slice, scope: **IS-B** — D-17's DI-Q4
  per-component `n` field (`VERIFICATION.md` IS-B; user directed this specific
  item rather than the mechanical top-of-queue pick, since IS-B had just been
  promoted ahead of IS-C2 in ordering — queue ordering is the user's per
  META_PLAN §5). Re-read `component_metrics` and the existing D-15 integration
  test (`test_d15_enablement_only_hazards_excluded_from_legitimization_but_not_final_label`)
  first to confirm the actual call pattern: callers already pre-filter rows via
  `legitimization_eligible_mask` before scoring Legitimization, and pass the
  full population for Enablement (required for every hazard, D-18) — so
  `component_metrics` itself needs **no** hazard-family logic to satisfy D-17's
  DI-Q4 amendment; it only needs to report how many rows it was given. Added
  test `test_component_metrics_n_reflects_the_passed_row_count` (mixed-hazard
  fixture `hte, prv, sxc_prn, spc_lgl, hte`) first and confirmed it **red**
  (`KeyError: 'n'`) before touching the implementation. Added `"n":
  int(len(y_true))` to `component_metrics`'s return dict in
  `src/hazard_classifier/metrics.py`, plus a docstring explaining why the
  function's genericness is preserved (D-17's semantics fall out of the
  caller's existing filtering, not new logic here). Confirmed green: the new
  test passes, and asserts the actual D-17 property — `legitimization.n <
  enablement.n` by exactly the `prv`/`sxc_prn` row count (2), not just that the
  key exists. Full suite green: 43 tests (was 42), zero regressions. Added an
  "Implementation slice landed" note to `DECISIONS.md` D-17's DI-Q4 amendment
  block. `VERIFICATION.md` updated throughout (test count, D-17 coverage row,
  IS-B marked done, execution-order list). **Explicitly not done here:** the
  actual `metrics.json` assembly step (`IS-8`, not built) that surfaces this
  `n` value in `hrc-evaluate`'s output schema — this slice only lands the
  underlying per-call value D-17 specifies.

- 2026-07-25 — Implementation slice, scope: **IS-C** — D-23's frozen-source
  requirement, unit level (`VERIFICATION.md` IS-C; top item pulled from the
  queue). The queue item's own note flagged a possible block on `model.py`
  ("may block on that; flag if so rather than forcing it"), but
  `VERIFICATION.md`'s IS-C entry had already scoped the doable slice:
  parameterize now, defer artifact wiring — so proceeded rather than blocking.
  Confirmed scope first: `rules.py`'s `is_required_component` imported
  `ENABLEMENT_ONLY_HAZARDS` from installed `hazard_classifier.config`;
  `resolve_component_action` called it internally, so both needed the change.
  Removed the `config` import; both functions now take a required
  `enablement_only_hazards: AbstractSet[str]` parameter with **no default** —
  a default would silently reintroduce the exact config-drift D-23 exists to
  prevent, so omitting the argument is a hard error, not a fallback. Updated
  all four existing test call sites in `test_predict_resolution.py` (confirmed
  they broke first — missing required argument — before fixing) with a local
  `_ENABLEMENT_ONLY` fixture (deliberately *not* imported from
  `hazard_classifier.config`, so the tests don't implicitly assume production
  reads config either). Added the actual forcing-function test,
  `test_is_required_component_uses_the_passed_set_not_installed_config`:
  constructs a frozen set that disagrees with installed config in *both*
  directions (`"hte"` newly enablement-only per the frozen set though absent
  from config; `"prv"` present in config but *not* in the frozen set) and
  confirms the passed set's answer wins both times, not config's — proving the
  parameterization actually decouples behavior from config, not just that a
  parameter exists. Full suite green: 42 tests (was 41), zero regressions.
  Added an "Implementation slice landed, partially" note to `DECISIONS.md`
  D-23. **Explicitly not done here** (per the decision's own scope and the
  queue note's anticipated block): the actual **wiring** of a real artifact's
  frozen `rules.json` into the caller — that needs `model.py`/artifact load
  (§10 Phase 3), tracked as IS-C's remaining half. **New finding surfaced
  while implementing, not fixed in this pass:** `metrics.py`'s
  `legitimization_eligible_mask` has the identical
  imports-config-directly pattern (used for D-15/D-18's evaluate-time
  eligibility mask) — same D-23 principle, different call site, outside this
  item's declared scope (which named only `rules.py`). Recorded in
  `DECISIONS.md` D-23's note, queued as new item **IS-C2** in both
  `VERIFICATION.md` and this file's Queue, rather than silently expanded into.
  `VERIFICATION.md` updated throughout (test count, D-23/D-18 coverage rows,
  IS-C marked done + IS-C2 added, execution-order list).

- 2026-07-25 — Implementation slice, scope: **IS-A** — fix
  `resolve_component_action`'s fail-open bug on D-20's absent/invalid-required-cell
  case (`VERIFICATION.md` IS-A; top item pulled from the queue per the
  execute-next-item process). Confirmed the defect first: the function checked
  `cell_status == "skipped"` then fell through to `"serve"` for *any* other
  status, including `None` — so an absent or corrupt required cell was served,
  the exact fail-open D-20 exists to prevent. Added two rows to the truth table
  in `tests/science/test_predict_resolution.py` (`cell_status=None` and an
  arbitrary invalid string, both on a required/known/non-empty row, expecting
  `fail_skipped_cell`) and ran them **red first** (`assert 'serve' ==
  'fail_skipped_cell'` — confirmed the defect empirically, not just by reading
  code). Fixed `resolve_component_action` in `src/hazard_classifier/rules.py`:
  flipped the deny-list (`if skipped: fail; else: serve`) to the allow-list D-20
  itself specifies (`if fit: serve; else: fail`) — both `None`/absent and any
  other non-`"fit"` value now share the same `fail_skipped_cell` action as
  `"skipped"` (no new `ComponentAction` literal introduced, matching D-20's own
  note that treats this as one bucket). Widened the `cell_status` parameter type
  from `Literal["fit", "skipped"] | None` to `str | None` since any non-`"fit"`
  value is now meaningful input, not implicitly disallowed. Full suite green:
  41 tests (was 39), zero regressions. Added an "Implementation slice landed"
  note to `DECISIONS.md` D-20 recording the mechanism and test count; updated
  `VERIFICATION.md`'s D-20 coverage-matrix row and IS-A section to DONE. This was
  a pure implementation slice — no `DECISIONS.md` entry changed in substance,
  D-20 was already locked; this only makes the code match it and records that
  fact.

- 2026-07-25 — Final paper pass + verification backlog (user-requested).
  **(1) D-19–D-24 integration check** run to formal close
  (`critiques/2026-07-25-integration-d19-d24.md`). Systematically checked
  D-19–D-24 against each other and the whole ledger (the four queued focus points
  plus broader cross-checks): **no conflict** — they compose. Two caveats, both
  pre-existing and tracked, not new findings: `resolve_component_action` fails
  open on D-20's absent-cell case (IS-A), and the queue note's focus-point (d)
  attribution was stale (D-21's `0.0` for a D-4 row comes from D-16's sentinel,
  not D-19's stage — already correct in the ledger). **(2) `VERIFICATION.md`**
  authored: a decision→check coverage matrix for all 28 decisions, six
  integration checks (IC-1…IC-6, most already done this session), and eleven
  implementation slices (IS-A…IS-11) grouped by §10 phase — each the smallest
  red-then-green forcing function for its decision(s). Confirmed the current suite
  is green (39 tests). Promoted the D-17 `n`-field gap from Awaiting User to the
  Queue as IS-B. No code touched — this pass produces the plan to confirm the
  decisions, not the implementations.

- 2026-07-25 — Fix-proposal, scope: Finding C / N-1 (`seed_prompt_id` output
  asymmetry in `hrc-predict`) from `critiques/2026-07-25-decisions-consistency.md`.
  Root cause: D-22's "identifying columns" was read by D-25 as including
  `seed_prompt_id` in `failures.csv`, but `prompt_uid` (the unique row id, §2.1)
  alone identifies a row and `seed_prompt_id` is an inert predict-path passenger
  (D-24). User accepted recommended option 1: **drop `seed_prompt_id` from
  `failures.csv`** (columns → `prompt_uid, hazard, failure_reason`) rather than
  add it to `predictions.csv` — aligns with D-24's semantics, avoids echoing a
  fabricated value on real traffic, lower blast radius, loses nothing
  (`prompt_uid` rejoins either output; failure reasons don't concern seed
  identity). Amended **D-25**; added cross-reference notes to **D-22**
  ("identifying columns" = `prompt_uid`) and **D-24** (inert-passenger basis);
  applied to `PLAN.md` §6. `seed_prompt_id` stays a required *input* column (D-24
  unchanged); only its predict *output* appearance is removed. Checked against
  the full ledger (D-22/D-24/D-13/§2.1/D-14) — no conflict; no consumer reads it
  from `failures.csv`; `hrc-evaluate` has no failures output (D-14). No code
  touched. **This closes the D-25–D-28 consistency audit — all three findings
  (A/C-1, B/Q-1, C/N-1) resolved.**

- 2026-07-25 — Fix-proposal, scope: Finding B / Q-1 (§8.2 AUC provenance
  unverified) from `critiques/2026-07-25-decisions-consistency.md`. Investigated
  the committed toy (`/Users/kurt/git/security-evaluator`) and established the
  provenance **cannot** be read off the repo: the toy computes two AUCs
  (`binary_present_auc` L704 / `high_auc` L705, `scoring_common.py`); the README
  "AUC" column is hand-curated; its source run (`heldout_seed_metrics.csv`) is
  not committed; git history shows the column was always just "AUC." So D-16's
  "these are `high_auc`" is unverified and circular, and committed positional
  evidence leans the *other* way (`binary_present_auc` listed first). Both AUCs
  are gate-invariant, so D-10 isn't the risk — provenance is. Per user: **getting
  the answer falls back to the Phase-4 parity harness** (option 3 — computes both
  AUCs, matches the reference against both), and **de-risk via recs 4 + 5**:
  amended **D-16** (provenance → "believed `high_auc`, unverified"; production
  still reports only `high_auc`, now decoupled from the parity target) and **D-2**
  ("AUC bit-for-bit target" made conditional on the harness confirming
  provenance); applied to `PLAN.md` §8.2 (harness computes both AUCs and matches
  both, separate from production reporting; flagged that `metrics.py`'s
  `component_metrics` computes only `high_auc` today, so the harness needs a
  separate `binary_present_auc` path). Empirical confirmation is now a Phase-4
  harness requirement tracked in §8.2, not a standalone queue item — the Finding
  B queue item is retired here. Contingency named: if the harness finds the
  reference is `binary_present_auc`, D-16 / AUC-parity reconcile then. Checked
  against the full ledger (D-2/D-10/D-16/DR-4/§8.2) — no conflict; no behavior
  changed. No code touched.

- 2026-07-25 — Integration/consistency audit (user-requested deep dive), scope:
  D-25–D-28 against the full ledger — the four decisions locked after the last
  full audit (24 decisions) and outside the still-queued D-19–D-24 integration
  check. Output `critiques/2026-07-25-decisions-consistency.md`. Found one
  cross-decision conflict (**C-1 / Finding A**): D-26's blank-ground-truth-label
  rule (a whole-run abort, framed as an up-front `schema.py` check) collided
  with D-23/D-27 (evaluate-time family lookups read frozen `rules.json`, not
  config; `schema.py` does no membership rejection on the evaluate path) and
  D-14/D-22 (unseen hazard → excluded, never abort) — a blank label on an
  unseen-hazard row would flip the run from exclude-and-continue to abort, and
  the "is it enablement-only?" source was config, reintroducing D-23's drift.
  User accepted the natural reconciliation; amended **D-26** (the family-aware
  blank judgment is a per-row evaluate check against frozen `rules.json`, running
  only on rows that survive D-14's hard-fail exclusion, so unseen/skipped/absent
  rows are excluded-and-counted and never abort on a blank label; family-agnostic
  column/range checks stay in `schema.py`). Added cross-reference notes to
  **D-27** and **D-14**. Applied to `PLAN.md` §2.1 (schema split), §5 `--input`
  (frozen-`rules.json` family source + survives-D-14 gating), §8.1 (test home).
  Full-ledger conflict check on the fix: D-13/D-14/D-15/D-18/D-20/D-22/D-24/D-23/
  D-27/D-28 — no conflict. Also re-verified the queued D-19–D-24 item's four
  focus points (a)-(d) compose, and confirmed `resolve_component_action` fails
  open on `cell_status=None` exactly as D-20 claims (ledger matches code). Two
  further findings — **B** (§8.2 AUC provenance unverified) and **C**
  (`seed_prompt_id` output asymmetry) — recorded and queued for the next passes
  per user direction ("we will do B and C" after A). No code touched.

- 2026-07-23 — Fix-proposal, scope: Deliverable-3 **P-Q4** (a wholly-skipped
  component is only discovered one serve-row at a time). Recorded locked
  **D-28** and applied to `PLAN.md` §3 step 4/5, §4, §5, §6. Adds a manifest
  rollup `skipped_components` (denormalized from `thresholds.json`'s per-cell
  `status`, which stays authoritative). Train-time: **hard-fail** on a
  wholly-skipped Enablement (required for every hazard, D-18 → artifact scores
  nothing); **warn+write** on a wholly-skipped Legitimization (still valid for
  enablement-only workloads). Load-time: `hrc-predict`/`hrc-evaluate` warn
  up-front — **warn-and-continue, no new abort**, so per-row handling stays
  exactly D-22 (failures.csv) / D-14 (exclude). User accepted all three
  open-question defaults. Checked against the full ledger (D-5/D-18/D-22/D-14/
  D-3/D-11/D-20) — no conflict. No code touched.

- 2026-07-23 — Fix-proposal, scope: Deliverable-3 **P-Q3** (hazard
  normalization + Step 0/Step 1 ordering). Recorded locked **D-27** and applied
  to `PLAN.md` §2.1, §3 step 1, §4, §6. (A) The `hazard` column is normalized
  once at schema load on all paths via the toy's `normalize_hazard`
  (`.strip().replace("-", "_")`, **no lowercasing** — user: "be like the toy"),
  so train-time cell keys and serve-time lookups agree. (B) The unseen-hazard
  check and family lookup are unified into one `rules.json` lookup: present →
  family/required-components; absent → genuinely-unseen fail (→ failures.csv,
  never the toy's `"default"` fallback), which resolves §6's Step 0/Step 1
  ordering wrinkle. User chose to freeze `rules.json` to **exactly the trained
  hazards**, so "in `rules.json`" ≡ "known" ≡ "has an enumerated required cell"
  and the two checks coincide. Also pinned: `schema.py` does not reject unknown
  hazards on the predict/evaluate paths (would abort, against D-22/D-14) — that
  resolves the critique's schema-vs-artifact authority tension. Checked against
  the full ledger (D-23/D-3/D-11/D-18/D-22/D-14/D-2) — no conflict. No code
  touched.

- 2026-07-23 — Fix-proposal, scope: the `hrc-evaluate` CLI gap (adjacent to
  P-Q2, surfaced by D-25). Recorded locked **D-26** and applied to `PLAN.md`
  §5: `hrc-evaluate --model-dir <artifact> --input <labeled csv> --output-dir
  <dir> [--allow-download]`, `--output-dir` receiving `metrics.json` +
  `metrics.csv` + `summary.txt` (D-17). User accepted both open-question
  defaults: summary.txt in the output dir; **error** (not exclude) if a
  non-enablement-only row has a blank ground-truth label — which also resolves
  the residual half of Deliverable-2 E-4 (partial-label behavior). Shares
  D-25's `--model-dir`/`--allow-download` surface and no-`--model-name` rule;
  `--input` requires ground-truth (opposite of predict's D-24, per §2.1); no
  `--cv` (D-12), no `--holdout-seed-fraction` (reads the manifest split, D-13).
  Checked against the full ledger (D-13/D-14/D-17/D-12/D-6/§4-D-23/§2.1) — no
  conflict. No code touched.

- 2026-07-23 — Fix-proposal, scope: Deliverable-3 **P-Q2** (`hrc-predict` had
  no CLI contract in §6). Recorded locked **D-25** and applied to `PLAN.md` §6:
  `hrc-predict --model-dir <artifact> --input <csv> --output-dir <dir>
  [--allow-download]`, with `--output-dir` receiving two CSV files
  (`predictions.csv` successes + `failures.csv`, always written) per D-22's
  split-output requirement. User accepted the proposal and all three
  open-question defaults (single output-dir with fixed filenames; CSV-only;
  failures.csv always written). The one active ledger constraint honored: **no
  `--model-name`** — the BGE id+revision come from the artifact manifest
  (§4/D-23), so predict embeddings can't be overridden into disagreement with
  training. Also absent: `--device` (D-6), `--other-hazard-weight` (frozen).
  Checked against the full ledger (D-22/D-24/§4/D-23/D-6/E-8) — no conflict.
  The parallel `hrc-evaluate`-CLI gap is out of P-Q2's scope and is under
  Awaiting User. No code touched.

- 2026-07-23 — Consistency audit of all of `DECISIONS.md` (user-requested deep
  dive). Found no decision-vs-decision contradiction, but five stale
  cross-references where a later locked decision superseded earlier wording
  without a pointer — fixed by adding aligning notes (D-3 & D-11: "raises an
  error" → D-22's split output; D-18: `config.` serve-time source → D-23's
  frozen `rules.json`; D-16: its D-4 "both components" quote → D-4's P-C1
  amendment; D-21: the D-4-row `0.0` attributed to D-19's stage → actually
  D-4/D-16's sentinel). Then, at user request, accepted two surfaced nuances as
  notes: the pre-rule (grid search) vs. post-rule (serve) threshold asymmetry
  (D-10 + D-19, framed as inherited toy behavior under D-2) and
  `excluded_skipped_cell_count` also counting D-20 absent-cell exclusions
  (D-17). Full recheck after: 24 decisions, all locked, sequential, no dangling
  references, every supersession bidirectionally pointed. No `PLAN.md` change.

- 2026-07-23 — Fix-proposal pass, scope: the nine user-answered findings in
  `critiques/2026-07-23-deliverable-3.md` (queue item bundled them; the user
  answered each in the critique's User Answers section, so this pass turned
  each answer into ledger + plan edits with a per-decision full-ledger conflict
  check). Grounded the encoded formulas/orderings by re-reading the toy
  (`effective_indices`, `apply_component_business_rules`, `v14_overall_score`,
  `score_from_centered_probs`) rather than trusting the ledger's description.
  **P-C1 (locked-entry conflict):** amended **D-4** in place — a
  prompt-repetition-only *non-empty* response scores 0 for **Enablement only**
  and goes through the frozen **Legitimization** head (the toy keeps echoed
  sentences for Legitimization); only a *genuinely empty* response scores 0 for
  both. This makes D-16's amendment (which already silently assumed this
  reading) consistent instead of contradictory. **Six new locked decisions:**
  **D-19** (explicit business-rule stage between centering and thresholding;
  the surviving disclaimer rule; the gate consumes adjusted probabilities),
  **D-20** (an absent/invalid *required* cell fails closed exactly like
  `"skipped"` — completes D-11's "or absent" and fixes §6 step 3's deny-list
  phrasing; flags the `resolve_component_action` fail-open as an
  implementation slice), **D-21** (`v14_overall_unsafe_score` retained as a
  research side-output, defined from adjusted continuous scores, independent of
  `predicted_label`, `0.0` for D-4 rows), **D-22** (`hrc-predict` splits
  successes/failures instead of aborting — supersedes D-14's "single-row API,
  aborting is correct" characterization, D-14's behavior unchanged), **D-23**
  (required-components / rule-family lookups read the artifact's frozen
  `rules.json`, not installed config — flags the `is_required_component`
  import as an implementation slice), **D-24** (`seed_prompt_id` stays required
  for predict input; ground-truth columns optional/ignored, reconciling
  §2.1-vs-§6). Added cross-reference notes to D-11 (D-20) and D-14 (D-22).
  Applied all to `PLAN.md`: §1.1 item 3 (continuous v14 formulas), §2.1 (D-24),
  §3 step 4 (D-4 per-component split), §4 (D-23 rules.json source), §5
  (business-rule stage in the shared pipeline; D-20 in the hard-fail bullet),
  §6 (pooling step incl. the Enablement sentence drop — P-Q1; business-rule
  step + disclaimer rule; v14 output definition; Step 0 rules.json; Steps 1/3
  split-output; Step 3 allow-list; gate consumes adjusted), §11 (new item 5 for
  the `score()` API contract). No code touched — two code-syncing follow-ups
  (P-C4 fail-open fix, D-23 config source) and an integration check over
  D-19–D-24 are queued. Four findings (P-Q2, P-Q3-normalization, P-Q4, P-N1)
  had no user answer and are under Awaiting User, not resolved.

- 2026-07-23 — Critique pass, scope: `PLAN.md` §6 (Deliverable 3,
  `hrc-predict`). Output: `critiques/2026-07-23-deliverable-3.md`, 13 findings
  (6 blocks-correctness, 5 quality, 2 nice-to-have). Grounded against the toy's
  actual source rather than the ledger's description of it
  (`effective_indices`, `apply_component_business_rules`, `v14_overall_score`,
  `discrete_v14_label`, `build_overall_rows`, `score_split`) and against this
  repo's already-written `src/hazard_classifier/rules.py`. Two findings are
  locked-entry-vs-prose conflicts rather than plain gaps, which META_PLAN §1
  says to raise rather than resolve: **P-C1** (D-4's "treated as 0 in both
  components" and §3 step 4 say a prompt-repetition-only response scores 0 for
  Legitimization; §6 step 2 scopes that to Enablement only; the toy keeps
  echoed sentences for Legitimization, so §6's reading is the one that avoids
  train/serve skew — and D-16's amendment already silently adopted it) and
  **P-C6** (D-18 names installed `config.ENABLEMENT_ONLY_HAZARDS` as the
  required-components source while §4 freezes the same map into the artifact's
  `rules.json`). Two findings are about the *implemented* predict path, not
  just prose: **P-C4** — D-11 requires failing closed on a required cell whose
  `status` is `"skipped"` **or absent**, but §6 states only the `"skipped"`
  half and `resolve_component_action` correspondingly returns `"serve"` for
  `cell_status=None`, i.e. fails open on a missing required cell, uncovered by
  the existing 23-case truth table — flagged as settleable by one added test
  case (META_PLAN §4). Also found: **P-C3**, §6's numbered step contract has no
  business-rule stage at all, which leaves the specialized-advice disclaimer
  rule (the only one of the toy's three not subsumed by D-4/D-18) unreachable
  by an implementer following §6 literally; **P-C2**,
  `v14_overall_unsafe_score` appears once in the whole plan with no definition
  anywhere and no defined value for D-4-scored rows (refusals — the most common
  production input); **P-C5**, §6's batch CLI contradicts D-14's
  single-row-API premise. No `DECISIONS.md` entries changed — critique passes
  decide nothing; see Awaiting User above.

- 2026-07-23 — Implementation slice, scope: predict-time cell-status
  resolution logic (recommended in chat, not from a critique finding).
  Placed in `src/hazard_classifier/rules.py` rather than a new module —
  `PLAN.md` §2.2 designates `rules.py` for "component business rules + v1.4
  combination," which is exactly this function's category, contradicting the
  queue item's own tentative "new `predict.py`" suggestion. Implemented two
  functions: `is_required_component(component, hazard)` (D-18 — Enablement
  always required, Legitimization required except for
  `config.ENABLEMENT_ONLY_HAZARDS`) and `resolve_component_action(component,
  hazard, hazard_known, cell_status, response_is_scoreable)`, which composes
  D-18's required-component check (step 0) with D-3/D-11's fail-closed
  precedence (unseen-hazard before D-4, skipped-cell after) and D-4's
  empty/echo-only scoring, returning one of `not_required` /
  `fail_unseen_hazard` / `score_zero` / `fail_skipped_cell` / `serve`. 23
  new tests in `tests/science/test_predict_resolution.py` (39 total, all
  green): 2 direct tests of `is_required_component` against the two hazard
  families, an exhaustive 9-row truth table over
  (required, hazard_known, cell_status, response_is_scoreable), and a
  12-case property test that `not_required` never depends on `cell_status`/
  `response_is_scoreable` (varying both while holding not-required fixed).
  Manually confirmed the truth table is a genuine forcing function, not
  vacuous: hand-simulated the pre-D-11-amendment ordering (skipped-cell
  check before D-4's empty-response check, the original "D-3 always first"
  rule) against the same table and confirmed it mis-resolves
  `(required, known, skipped, empty-response)` as `fail_skipped_cell`
  instead of `score_zero` — the exact bug D-11's amendment exists to fix,
  now caught by test rather than left as an inference from re-reading the
  ledger. This function does not decide which hazards are required or what
  a cell's status actually is in a real artifact — those come from
  enumeration/artifact state that doesn't exist yet (§10 Phase 3
  scaffolding, `model.py`); wiring `resolve_component_action` into an actual
  predict path is separate, larger, future work.
- 2026-07-23 — Fix-proposal, scope: DI-N2 + DI-N3, the last queued item from
  the decision-introspection critique (both nice-to-have, pre-cleared by the
  critique as not needing user judgment, bundled since neither warranted its
  own pass). **DI-N3:** added a "documented not fixed" note to `DECISIONS.md`
  D-5 (after its D-18 note): `status: "fit"` is binary, but a fit cell's
  thresholds can come from either of D-2's two already-locked regimes
  (hazard-specific vs. pooled-fallback, per the `n_own >= 5` cliff) — both
  equally serviceable at predict time, so this is a real reporting gap, not
  a serving defect; no schema change made absent a concrete need, per the
  queue item's own scope. Mirrored to `PLAN.md` §4's `status` field
  description with a matching one-line note. **DI-N2:** added §2.1 to D-12's
  `DECISIONS.md` Touches list (it was missing even though D-12 dropped
  grouped CV, and §2.1's schema table still named "grouped CV" as a use case
  for `seed_prompt_id`); reworded that table row in `PLAN.md` to describe
  only the held-out split (D-1/D-13), cross-referencing D-12 for why grouped
  CV is no longer a use case. Neither change required a new decision or
  touched any other locked entry. This closes out all nine items the
  decision-introspection critique's answered open questions produced;
  `STATUS.md`'s queue is now empty for the first time since that critique
  ran.
- 2026-07-23 — Fix-proposal, scope: DI-Q5 (is `PLAN.md` §11 open question 3
  — specialized-advice hazards excluded from the final-label headline —
  settled, or still genuinely open?). User response: "Yes. item 3 should be
  closed." Confirmed D-17 point 3 already locks this exactly (the shared
  denominator `N` for false-safe/false-unsafe rates explicitly excludes
  specialized-advice hazards), so no new `DECISIONS.md` entry or amendment
  was needed — this was a plan-prose closure, not a design decision, mirror
  of how §11 item 1 was previously closed by pointing at D-3/D-11. Rewrote
  §11 item 3 to state "Resolved by `DECISIONS.md` D-17 (locked)" and added a
  one-line note distinguishing it from D-15's separate enablement-only
  exclusion (which is scoped to the Legitimization *component* metric only,
  not this headline) so the two nearby exclusions aren't conflated by a
  reader. §11 now has only two open items left: pooling choice (#2) and
  artifact serialization format (#4), neither raised by this critique.

- 2026-07-23 — Fix-proposal, scope: DI-Q3 (should `--holdout-seed-fraction`
  default non-zero, and should the §8.2 parity harness require a
  holdout-trained artifact?). User response: "Make the default zero" —
  confirming existing implicit behavior (nothing in `PLAN.md` ever stated a
  default) rather than changing it. Amended `DECISIONS.md` D-1 to pin the
  `0` default explicitly and spell out its direct consequence:
  a default-trained artifact has an empty `holdout_seed_prompt_ids`, so
  D-13's `hrc-evaluate` partitioning puts everything in
  `in_sample_unrecorded` with its "no recorded held-out split" warning — the
  expected common case, not a misconfiguration. Separately amended D-2 to
  resolve DI-Q3's second half: §8.2's reference numbers are explicitly the
  toy's *held-out* figures, so the parity harness's own fixture-training
  step must pass a non-zero `--holdout-seed-fraction` and compare against
  the resulting artifact's `held_out` population specifically — otherwise
  the harness could silently compare an in-sample number against a held-out
  reference under one "parity" label. Checked against the full ledger as
  the queue item's own notes directed: D-12 is not contradicted (the
  held-out-generalization *capability* it names still exists via this flag)
  but its "preserved instead via D-1's split" framing implicitly assumes the
  split gets invoked, which is opt-in, not automatic — added a light
  cross-reference note to D-12 rather than editing its claim, since the
  claim itself is still true, just needed clarifying. D-13 unaffected — its
  empty-`holdout_seed_prompt_ids` warning path already anticipated exactly
  the default case. Applied to `PLAN.md`: the `--holdout-seed-fraction`
  paragraph in §3 now states the `0` default and its consequence explicitly,
  and §8.2's parity-harness bullet states the held-out-training precondition
  before its existing D-10/D-16 exceptions.
- 2026-07-23 — Fix-proposal, scope: DI-Q4 (D-17's schema reports one
  `n_rows` per population, but D-15/D-18 already make Legitimization's
  eligible-row count differ from Enablement's within that same population —
  `final_label` already has its own `n` for the analogous reason, but
  Legitimization's actual denominator was reportable nowhere). User
  response: "Record the legitimization component's actual denominator so
  that we can figure out later how to use it" — not one of the six
  questions posed as blocking, but answered anyway. Amended `DECISIONS.md`
  D-17 (a third amendment, appended after the DI-C4 one): both
  `components.enablement` and `components.legitimization` gain their own
  `n` — `components.enablement.n` always equals the population's `n_rows`
  (Enablement is required for every hazard, D-18), `components.
  legitimization.n` is `n_rows` minus that population's enablement-only-
  hazard rows (D-15, mechanized by D-18). Per the user's explicit
  instruction, defined no new consumer of this count beyond recording it —
  every existing metric definition is unaffected. Checked against the full
  ledger: D-15/D-18 unaffected (this only makes an existing exclusion's
  resulting count newly visible, not a new rule). Applied to `PLAN.md` §5's
  Output schema paragraph (added `n` to both component objects and explained
  why three different denominators — `n_rows`, `components.legitimization.n`,
  `final_label.n` — now coexist per population); also tightened one
  ambiguous phrase in the same bullet in passing ("absent from this
  population" → clarified this refers to the Legitimization section's row
  set, not the eval population as a whole). Did not touch
  `src/hazard_classifier/metrics.py`'s already-implemented
  `component_metrics`, which predates this amendment and doesn't yet return
  `n` — consistent with every prior fix-proposal pass this session, which
  stayed in `DECISIONS.md`/`PLAN.md` and left code-syncing to dedicated
  implementation-slice items; flagged the gap under Awaiting User instead of
  fixing it silently.
- 2026-07-23 — Fix-proposal, scope: DI-C3 + DI-Q1 (combined — one answer
  resolves both: D-4's head-less rows had no defined AUC-input value, and
  D-16's own definition of "AUC" was ambiguous about pre- vs. post-rule).
  User response: "Compute the reported per-component AUC from adjusted_high
  — the high head's centered probability after
  apply_component_business_rules — not from the raw centered probability
  D-16's text currently names." Before amending, re-checked the toy's actual
  `metric_summary` (`scoring_common.py` L656-707) rather than trusting D-16's
  own description of it, and found D-16 had **two** factual errors, not one:
  `high_auc` is computed from `adjusted_high` (post-business-rule), not the
  raw centered probability as D-16 stated; and `binary_present_auc` (not
  served in production either way) is computed from the rule-adjusted
  *combined* score (`score_from_centered_probs` on the adjusted values), not
  from "the nonzero head" as D-16 stated — corrected both. Amended
  `DECISIONS.md` D-16 in place (appended, not rewritten) to pin AUC to
  `adjusted_high`, and worked out D-4's AUC-input convention with more
  precision than the chat recommendation had: only one of the three
  D-4-scored cases is genuinely toy-derived (Enablement prompt-repetition-
  only, via the toy's own `prompt_repetition_only_sets_enablement_zero`
  business rule, which literally sets `centered_high = 0.0`) — a truly blank
  Enablement response and any empty Legitimization response have no
  corresponding toy business rule at all (rule 3 requires
  `prompt_repetition_sentence_count > 0`, so it doesn't fire on true
  emptiness; Legitimization's two business rules don't depend on emptiness
  either). Extended the same `0.0` sentinel to those two cases anyway — not
  invented from nothing, but the toy's own established "confidently not a 2"
  value, applied to rows D-4 already treats identically — and stated the
  distinction explicitly rather than blurring it as "the toy's own value"
  across the board. Checked against the full ledger: this correction
  *strengthens* D-2/D-10's AUC-parity exemption from DR-4 rather than
  threatening it (the previous pre-rule reading wouldn't have matched the
  toy's §8.2 reference numbers at all, gate or no gate, since those numbers
  are the toy's own post-rule `high_auc`); D-4 unaffected in substance (its
  "treated as 0" already covered the discrete outcome — this supplies the
  previously-undefined continuous value for the same rows). Added a light
  cross-reference note to D-4. Applied to `PLAN.md` §5 (AUC definition bullet
  corrected and the D-4-row convention stated) and §8.2 (added a second
  named exception alongside D-10's: the parity harness may need slightly
  looser AUC tolerance if its fixture contains any of the two
  toy-has-no-rule-for-this cases, proportional to how many such rows exist).
- 2026-07-23 — Fix-proposal, scope: DI-C4 (where do D-14's excluded-row
  counts live — D-14 says an excluded row never enters a population, but
  D-17's original schema nested `excluded_row_count` and its breakdown
  inside each `held_out`/`in_sample_unrecorded` object). User response:
  "(b) moving the excluded counts to the top level alongside
  `holdout_recorded`." Amended `DECISIONS.md` D-17 (appended after its
  original point 4, not rewriting it): `excluded_row_count`,
  `excluded_unseen_hazard_count`, and `excluded_skipped_cell_count` move to
  `metrics.json`'s top level — one set of numbers for the whole eval run —
  since D-14's exclusion runs before D-13's partitioning and a per-population
  count was therefore unimplementable as originally schema'd. Each
  population object keeps `n_rows` (its own surviving-row count),
  `components.*`, and `final_label`. Had to resolve one small implementation
  detail not raised by the critique: `metrics.csv`'s long format requires
  every row to carry a population value, so the three relocated top-level
  fields get a sentinel population, `"overall"` — decided directly (~95%
  confidence, a mechanical completeness question, not a policy call) rather
  than raised as an open question. Checked against the full ledger: D-13
  unaffected (only *where* the counts are reported changes, not exclusion's
  timing relative to partitioning); D-14 unaffected (its "never enters
  either population" guarantee is now honored structurally instead of
  contradicted); D-18 unaffected (a not-required component was never one of
  these two exclusion reasons to begin with, confirmed via D-14's existing
  D-18 note). Added a cross-reference note to D-14 flagging that its own
  "deferred to the still-queued E-9" phrase is stale (E-9 became D-17, then
  D-17 was amended here). Applied to `PLAN.md` §5's Output schema paragraph:
  restructured to top-level `holdout_recorded`/`excluded_row_count`/
  breakdown, per-population objects now only carry `n_rows` +
  `components.*`/`final_label`, and the `metrics.csv` sentinel is documented.
- 2026-07-23 — Fix-proposal, scope: DI-Q2 (are enablement-only hazard rows
  inside or outside legitimization's `mean`/`scale`/`center_mean` row set?).
  User response: "outside." Resolved via item 2's D-18 rather than as a
  freestanding row-count rule: since Legitimization is not a required
  component for `prv`/`sxc_prn` (D-18) — no ground truth exists for them
  (§2.1) and the toy never even embeds legitimization sentences for them
  (§1.1 item 2) — there was never a row to include or exclude; this is a
  consequence of component non-requirement, not a fourth ad hoc exclusion
  alongside D-1/D-4. Added a second `Amendment` block to `DECISIONS.md` D-7
  (appended after the existing DR-1/DR-3 amendment, not rewriting it) stating
  this restriction applies only to Legitimization, never to Enablement
  (required for every hazard). Checked against the full ledger: D-15 already
  locked this exclusion for `hrc-evaluate`'s *reporting* but was silent on
  fit time — this amendment confirms both are the same rule via D-18, no
  contradiction; D-1/D-4 are unaffected since this is a component-membership
  question (which rows Legitimization ever sees), not a sequential filter
  that interacts with holdout/empty-echo ordering. Added cross-reference
  notes to D-15 and D-18 pointing at this amendment. Applied to `PLAN.md`
  §2.3 (`BinaryHead` spec) and §3 step 4 (the D-7 paragraph), both now
  stating Legitimization's row set is further restricted while Enablement's
  is not. Updated queue item 4's Notes; item 3 itself is removed from the
  queue.
- 2026-07-23 — Fix-proposal, scope: DI-C2 (is legitimization enumerated and
  fail-closed-rejected for enablement-only hazards, or never required at
  all?). User response: "Go with the component is *not required* for those
  hazards, so the cell is never consulted rather than consulted-and-
  rejected." Strengthened confidence before locking by reading the toy's
  actual downstream combination code, not just its enumeration/business-rule
  prose: `v14_overall_score` and `discrete_v14_label`
  (`scoring_common.py` L624-646) both accept `l_score`/`l_pred` as
  `Optional`, default them to `0`/`0.0`, and for `rule_family ==
  "enablement_only"` never read that value at all — direct evidence the toy
  itself already treats legitimization as absent, not degenerately-computed,
  for these two hazards. Recorded new locked `DECISIONS.md` D-18: Enablement
  is required for every hazard; Legitimization is required for every hazard
  except `prv`/`sxc_prn`. A not-required `(legitimization, hazard)` cell is
  never enumerated at training time and never looked up at predict/evaluate
  time — a third, distinct reason a cell can be absent, prior to and
  independent of D-5's (amended) degeneracy-driven `"skipped"` status; not a
  variant of D-3/D-11's two fail-closed triggers. This also supplies the
  concrete mechanism D-15 was written assuming existed (D-15's own text
  calls itself "a restatement... not a new modeling change") and gives
  `PLAN.md` §5's previously-undefined "required component" phrase an actual
  definition. Checked against the full ledger, no conflicts: added
  cross-reference notes (not rewrites) to D-3, D-5, D-11, D-14, D-15, each
  stating that their own checks/triggers are scoped to cells that exist at
  all and are unaffected by this prior absence. Applied to `PLAN.md`: §3
  step 4 (new enumeration paragraph stating the required-components
  carve-out, placed before the D-5 degeneracy paragraph), §4 (artifact
  schema — `prv`/`sxc_prn` legitimization entries are absent, not `"fit"` or
  `"skipped"`), §5 (D-14 bullet's "required component" phrase now defined;
  states a not-required component is not an exclusion trigger either), §6
  (new Step 0 — required-components lookup runs before steps 1-3; per-row
  output note that `legitimization_predicted` is null/absent for these
  hazards, cross-referencing the toy's own `Optional` handling). Updated
  queue items 3, 4 to point at this landed decision.
- 2026-07-23 — Fix-proposal, scope: DI-C1 (redefine D-5's `"skipped"` trigger
  to match the toy's actual behavior). User response to the critique's Open
  Question: "Do what the toy does." Traced `fit_binary_head_weighted`
  (`run_bge_hazard_weighted_heads.py` L81-107) directly rather than trusting
  D-5's original description: the constant-probability substitution fires on
  `len(set(train_y)) < 2` (L88), where `train_y` is the full component's
  binary label (nonzero or high) over **every** training row surviving D-1's
  holdout exclusion and D-4's empty/echo exclusion, pooled across *all*
  hazards — `sample_weight` (the per-target-hazard 1.0/0.25 weighting) only
  reweights those rows, it never filters which are present, so the condition
  cannot vary by hazard within a component. A hazard with zero own rows is
  not this condition at all — it fits normally from other hazards' weighted
  rows and falls back to pooled thresholds per D-2's already-locked
  `n_own >= 5` cliff; there was never a toy mechanism, and now isn't a
  production one, that skips an individual hazard for thin own-hazard data.
  Amended `DECISIONS.md` D-5 in place (superseding its original "zero
  training rows" trigger and the DR-3 note built on it): `status: "skipped"`
  is now set on **every** cell of a component **simultaneously** when either
  of its two binary label vectors is degenerate over that row set — never
  for an individual hazard in isolation. Flagged explicitly (not an open
  question, since confidence in what the toy does is high and this directly
  answers what was asked): this makes "skipped" require a whole-component,
  data-quality-level degeneracy, expected to be rare — not the routine
  per-hazard thin-data event `PLAN.md`'s prose previously illustrated. Added
  corrective notes to D-3 and D-11 (both restated the stale "zero-training-
  row cell per D-5" phrasing in their own decision text) rather than editing
  their original text, since the fail-closed *behavior* they lock is
  unchanged — only D-5's trigger condition moved. Checked against D-14/D-17:
  their `"skipped"`/`excluded_skipped_cell_count` references are generic
  enough to remain accurate as-is, though a reader should now expect that
  count to jump by an entire component's rows at once on the rare occasion it
  fires, not by a handful of thin-hazard rows. No conflicts found against the
  full ledger. Applied to `PLAN.md`: §3 step 4 (the D-5 paragraph's
  illustrative example — a thin-data hazard — was factually wrong under this
  trigger and was replaced with the correct whole-component condition), §4
  (the `status` field's description), §6 (`hrc-predict` Step 3's
  parenthetical), §11 item 1 (same phrase). Updated queue items 2, 4, and 9's
  Notes to point at this completed item instead of a still-pending
  prerequisite.
- 2026-07-23 — Bookkeeping pass: recorded nine fix-proposal items (queue items
  1–9) against the nine open questions the user answered inline in
  `critiques/2026-07-23-decision-introspection.md`'s User Responses section
  (DI-C1 through DI-C4, DI-Q1 through DI-Q5). No `DECISIONS.md` or `PLAN.md`
  edits made — turning an answer into a locked decision is a fix-proposal
  pass's job (META_PLAN §2), not this bookkeeping pass's. Ordered the queue by
  dependency rather than by the critique's own numbering: item 1 (DI-C1,
  redefine D-5's "skipped" trigger to the toy's actual component-wide
  single-class condition) is foundational and is called out as a prerequisite
  in items 2, 4, and 9's Notes; item 2 (DI-C2, legitimization not a required
  component for enablement-only hazards) is a prerequisite for item 3 (DI-Q2,
  the matching D-7 exclusion) and item 6 (DI-Q4, per-section row counts); item
  4 (DI-C4, move excluded-row counts to top level) is a prerequisite for item
  6. Items 5 (DI-C3+DI-Q1, combined per the critique's own finding that they
  share one answer), 7 (DI-Q3), and 8 (DI-Q5) have no ordering dependency on
  the others. Item 9 bundles the two nice-to-have findings the critique
  explicitly flagged as not needing a user decision (DI-N2, DI-N3) with the
  answered questions, since nothing else was going to queue them; DI-N1 was
  left out (see Awaiting User) since it wasn't posed as a question and wasn't
  answered, unlike DI-N2/DI-N3 which were explicitly named as pre-cleared in
  the critique's own closing note.
- 2026-07-23 — Critique pass, scope: all of `DECISIONS.md` (D-1 through D-17)
  reviewed against each other for mutual consistency — the second ledger
  introspection, after `critiques/2026-07-23-decision-review.md` covered
  D-1 – D-10. Concentrated on D-11 – D-17 (never cross-checked before) and on
  the older entries as they read *after* their in-place amendments. First
  verified DR-1 – DR-7's accepted resolutions are actually present in the
  ledger (they are) so nothing was re-litigated. Grounded the findings by
  reading the toy's `fit_binary_head_weighted`,
  `optimize_thresholds_for_hazard`, `metric_summary`, and `score_indices`
  rather than trusting the ledger's descriptions of them — which is what
  surfaced DI-C1 (D-5's `"skipped"` trigger describes a mechanism the toy does
  not have) and DI-Q1 (D-16 misdescribes both of the toy's AUCs; `high_auc` is
  computed post-business-rule). Output:
  `critiques/2026-07-23-decision-introspection.md`, 12 findings (4
  blocks-correctness, 5 quality, 3 nice-to-have), plus an explicit
  "checked and cleared" section recording the five cross-decision pairs that
  were examined and found consistent. No `DECISIONS.md` entries changed —
  critique passes decide nothing; see Awaiting User above.
- 2026-07-23 — Implementation slice, scope: `metrics.py` (D-13/D-15/D-16/
  D-17 component + final-label metric computation), recommended in chat as
  the next slice for Deliverable 2. Added `src/hazard_classifier/config.py`
  first (`ENABLEMENT_ONLY_HAZARDS`, `SPECIALIZED_ADVICE_HAZARDS`, ported
  verbatim from the toy's `scoring_common.py`) since neither hazard-family
  set existed in the package yet, per §2.2's package layout designating
  `config.py` for hazard sets. Implemented in
  `src/hazard_classifier/metrics.py`: `partition_by_holdout` (D-13),
  `legitimization_eligible_mask` (D-15's exclusion, kept as its own small
  function so `component_metrics` stays generic/reusable rather than baking
  hazard-family logic into it), `component_metrics` (exact/within-one/
  binary-present-accuracy/QWK/MAE/confusion, with AUC computed only from the
  passed-in `high_prob` argument — D-16's high-head-only rule is enforced
  structurally, since the function has no nonzero-head parameter to
  accidentally use), and `final_label_metrics` (precision/recall/F1 under
  D-17's safe=1 convention, labeled confusion counts, false-safe/
  false-unsafe rates on the shared denominator, specialized-advice hazards
  excluded from the headline, with an explicit `n == 0` guard so an
  all-specialized-advice population returns `None`s instead of crashing).
  QWK reuses `sklearn.metrics.cohen_kappa_score` directly rather than
  porting the toy's vectorized grid-search formula, since there's no grid
  search here — appropriate for a single-pair evaluation.
  11 new tests in `tests/science/test_metrics.py`, all passing (16 total
  with the earlier `rules.py` slice): partition/mask correctness, a
  perfect-prediction sanity check, a constructed case proving AUC is
  computed from the high-head probability and not a nonzero-head-shaped
  score (1.0 vs. 0.75 on the same rows), a single-class-returns-`None`
  check, cross-checks of QWK and precision/recall/F1 against `sklearn`
  directly, the empty-headline-population guard, and an integration test
  confirming enablement-only-hazard rows are excluded from
  `component_metrics` (via `legitimization_eligible_mask`) but still counted
  in `final_label_metrics` (D-15 vs. the unrelated specialized-advice
  exclusion). Noted, not fixed: `cohen_kappa_score` emits an
  `UndefinedMetricWarning`/NaN on a fully single-class input (same
  degenerate-cell behavior the toy already has and D-2 already accepts as a
  known, documented risk) — consistent with existing design, not a new
  defect. Per the queue item's own scope note, did not attempt D-14's
  hard-fail exclusion or D-13's `manifest.json` reading — both need artifact/
  model.py scaffolding (§10 Phase 3) that doesn't exist yet.
- 2026-07-23 — Fix-proposal, scope: E-9/E-10 (metrics output schema +
  positive-class convention) — last item from the Deliverable 2 critique.
  E-10 applied directly (safe=1/unsafe=0), plus a labeled 2×2 confusion
  shape to avoid re-introducing encoding ambiguity, plus a
  false_safe_rate/false_unsafe_rate formula pulled from the toy's own
  README instruction ("use the same denominator...") rather than invented
  fresh — resolving the residual half of E-3's original "is it truly one
  shared denominator" question that the earlier E-3/E-4 pass hadn't
  addressed. E-9's schema was an explicit "make a guess, correct later"
  instruction — kept it to the smallest structure that can hold everything
  §5/D-13/D-14/D-15/D-16 already require reporting (population-keyed JSON,
  long-format CSV, no independent second schema). Recorded new locked
  `DECISIONS.md` D-17 covering all of the above. Applied to `PLAN.md` §5:
  the final-label bullet gets the positive-class/confusion/rate-definition
  pin, the Outputs bullet is rewritten with the concrete schema, and D-14's
  excluded-row-count bullet (which previously forward-referenced "the
  still-queued E-9 schema pass") now points at D-17 directly. This closes
  the entire Deliverable 2 critique — D-13 through D-17 cover all 10
  findings (E-1 through E-10); queue is now empty.
- 2026-07-23 — Fix-proposal, scope: E-5 (retain head probabilities; AUC
  definition). While tracing the toy's actual AUC computation to answer this
  cleanly, found it computes **two** AUCs per component —
  `binary_present_auc` (nonzero head vs. `y > 0`) and `high_auc` (high head
  vs. `y == 2`) — so "AUC" was ambiguous even relative to the toy's own
  behavior, not just under-specified in the plan. Checked against DR-4 (AUC
  is rank-based / gate-invariant under D-10) as directed — consistent, no
  conflict: centering is strictly monotone and D-10's gate only changes the
  discrete threshold combination, not the retained probabilities, so this
  decision doesn't reopen that invariance. Recorded new locked
  `DECISIONS.md` D-16: head probabilities are retained through scoring;
  reported per-component "AUC" is pinned to the high head's AUC only (the
  toy's `high_auc` definition), not the nonzero head's, and not an average
  of both. Applied to `PLAN.md` §5: the pipeline-description bullet now
  states probabilities are retained, and the component-metrics bullet spells
  out the AUC definition explicitly. Noted but did not resolve: which of the
  toy's two AUCs the §8.2 parity-harness reference numbers (≈0.808, ≈0.783)
  were actually sourced from is not confirmed from the README alone — out of
  this pass's scope, but worth checking if/when the deferred D-10 §8.2
  quantification work happens.
- 2026-07-23 — Fix-proposal, scope: E-3/E-4 (legitimization component
  metrics exclude enablement-only hazard rows). Checked against §1.1 item
  3's existing enablement-only combination rule as directed — confirmed this
  is a restatement (legitimization already N/A for `prv`/`sxc_prn`, final
  label already judged by `E` only for those hazards), not a competing or
  new rule; no conflict. Recorded new locked `DECISIONS.md` D-15:
  legitimization's component metrics (exact/within-one/AUC/QWK/MAE/confusion
  counts) exclude enablement-only-hazard rows entirely; the final-label
  false-safe/false-unsafe denominator is explicitly unaffected — those rows
  keep contributing their `E`-only final label as before. Applied to
  `PLAN.md` §5: the component-metrics sub-bullet now states the
  legitimization exclusion explicitly, and the final-label sub-bullet
  clarifies enablement-only rows remain included there.
- 2026-07-23 — Fix-proposal, scope: E-2 (`hrc-evaluate` excludes hard-fail
  rows instead of aborting). Checked against D-3/D-5/D-11 as directed:
  answered the queue's posed question explicitly — this reuses the *same*
  D-3/D-4/D-5/D-11 checks `hrc-predict` already defines (unseen hazard;
  non-empty response on a `"skipped"` cell), it does not fork a separate or
  more permissive check, and D-4's empty-response-scores-0 path is
  unaffected (not an exclusion trigger). No conflict — this is a
  consequence change (exclude-and-continue vs. abort), not a predicate
  change. Recorded new locked `DECISIONS.md` D-14: hard-fail rows are
  excluded entirely (both components and the final label, not just the
  failing component) from every reported metric; the excluded-row count is
  recorded and displayed (exact schema deferred to E-9); this check runs
  *before* D-13's held-out/in-sample partitioning, so excluded rows never
  enter either population. Applied to `PLAN.md` §5 (new exclusion bullet,
  ordered before the D-13 partitioning bullet; D-13's own bullet reworded to
  say "surviving (non-excluded, per D-14)" rows; Outputs bullet now
  mentions the excluded-row count), and §6 (added a short cross-reference
  note stating D-3/D-4/D-5/D-11 are the single source of truth for
  unscoreable-row logic and that `hrc-evaluate` reuses rather than forks
  them).
- 2026-07-23 — Fix-proposal, scope: E-1 (`hrc-evaluate` wires up D-1's
  holdout split end-to-end). Checked against D-1 and D-2 as directed:
  reinforces D-1 (this is literally the consumer D-1's "excluded solely so
  hrc-evaluate can measure generalization" rationale was waiting on) and D-2
  (surfaces, rather than hides, the in-sample bias D-2 requires be
  documented as a risk). No conflict with either. Recorded new locked
  `DECISIONS.md` D-13: `hrc-evaluate` reads `holdout_seed_prompt_ids` from
  the artifact's manifest and splits eval rows into "held-out" (verified
  generalization numbers, reported as the headline) vs. "in-sample /
  unrecorded" (D-2-biased, must be labeled as such) — always reported
  separately, never silently pooled, with an explicit warning if the
  artifact recorded no holdout split at all. Noted as a deliberate scope
  limit (not a gap): this is a two-way partition off the *recorded* holdout
  set, not a three-way split that would also detect seed ids genuinely
  never seen in training — that would need the manifest to store the full
  trained seed-id set, which E-1's scope didn't ask for. Applied to
  `PLAN.md`: §3 step 5 (manifest explicitly names the
  `holdout_seed_prompt_ids` field, and notes it's `[]` not absent when no
  holdout was reserved) and the `--holdout-seed-fraction` paragraph
  (cross-references D-13), §4 (manifest.json field list), §5 (the
  partitioning/reporting/warning logic itself — "Report, per component and
  overall" is now explicitly "for each population above", and outputs are
  tagged `held_out` / `in_sample_unrecorded`). Did not touch §8.2's parity
  harness reference numbers — those compare against the toy's own combined
  CV+holdout methodology and are already caveated elsewhere (D-10's
  amendment); out of D-13's stated Touches.
- 2026-07-23 — Fix-proposal, scope: drop `--cv` from `hrc-evaluate`'s scope
  (critique `critiques/2026-07-23-deliverable-2.md`, response to Open
  Question 4). Checked against the full ledger: no existing locked decision
  referenced `--cv`, so no conflict. Recorded new locked `DECISIONS.md` D-12
  (`--cv`/grouped k-fold CV is not part of `hrc-evaluate`; the held-out-
  generalization concept it approximated is preserved instead via D-1's
  single holdout-seed split). Applied to `PLAN.md`: §1.1 item 4 (scope note
  citing D-12, since item 4 previously implied grouped CV was science "must
  be preserved" verbatim), §5 (removed the `--cv` bullet, added an explicit
  "Out of scope" note), §9 (added to the explicitly-skipped list, alongside
  the toy's other dropped research-only surfaces), §10 (phased-build table's
  `hrc-evaluate` row no longer mentions `--cv`). Noted E-6/E-7 (the `--cv`
  composition findings) as moot rather than fixed, per D-12's rationale. This
  also unblocks E-1/E-2 below, which no longer need to reason about
  `--cv`-vs-frozen-path interaction.
- 2026-07-23 — Critique pass, scope: PLAN.md §5 (Deliverable 2, `hrc-evaluate`).
  Output: `critiques/2026-07-23-deliverable-2.md`, 10 findings (5
  blocks-correctness, 3 quality, 2 nice-to-have). No `DECISIONS.md` entries
  changed — critique passes decide nothing; see Awaiting User above.
- 2026-07-23 — Implementation slice, scope D-9/D-10 (monotonicity gate).
  Created minimal scaffolding to host it (`pyproject.toml`, `src/hazard_classifier/`
  as an editable-installed package, `tests/science/`) — not the full Phase 0
  build, just enough for this slice. Implemented `ordinal_prediction` (gated
  predict-time combination) and `optimize_ordinal_thresholds` (same 91×91
  grid search as the toy, `pred_grid` built from the identical gate function
  `ordinal_prediction` uses, so train/serve consistency holds by
  construction, not just by convention) in `src/hazard_classifier/rules.py`.
  5 tests in `tests/science/test_threshold_optimizer.py`, all passing:
  direct adversarial-case check, random-input monotonicity property, a
  synthetic 3-class dataset (with an adversarial slice where the high head
  fires without the nonzero head) asserting the grid search's own recovered
  thresholds never produce a non-monotone prediction, a separability/QWK
  sanity check, and a cross-check of the ported vectorized QWK formula
  against `sklearn.metrics.cohen_kappa_score(weights="quadratic")` (exact
  match to 1e-9). Manually confirmed the test is a real forcing function, not
  vacuous: re-ran the adversarial dataset through the toy's original
  *ungated* rule at the same recovered thresholds — 30/30 adversarial rows
  were wrongly scored 2, versus 0/30 under the gated rule. Did **not**
  attempt the still-deferred D-10 §8.2 quantification (how far the gate
  moves the toy's *real* reference numbers) — that needs the actual labeled
  CSV and BGE embeddings, and neither `security-evaluator/inputs/` nor
  `results/` has them committed (confirmed via their READMEs: data is
  supplied at run time, not checked in). No `DECISIONS.md` entry produced —
  this slice verifies an already-locked mechanism, it doesn't decide
  anything new. Files not yet committed to git (repo has no commits yet).
- 2026-07-23 — Fix-proposal, scope D-11 (narrow the fail-closed precedence
  to genuinely-unseen hazards only). User resolved the residual open
  question flagged when D-11 was first locked: "I want an empty/echo-only
  response against a *skipped* (not unknown) cell to still score 0 rather
  than hard-fail." Amended `DECISIONS.md` D-11 in place: the single "D-3
  before D-4" rule splits into two sub-checks with different precedence —
  genuinely-unseen-hazard still checked before D-4 (unconditional hard
  fail), but skipped-cell now checked *after* D-4 (an empty/echo-only
  response scores 0 without ever consulting cell status). Added a matching
  cross-reference note to D-3 (its single fail-closed guarantee now
  documented as two sub-triggers with different precedence) and corrected
  D-4's Touches note (previously said D-4 runs after D-3 uniformly; now
  says after the unseen-hazard check but before the skipped-cell check).
  Verified no weakening of D-5's "skipped cells must never be used at
  predict time": D-4's score-as-0 path never inspects cell status or
  invokes the frozen head, so a skipped cell's parameters remain unused
  whether the response is empty (short-circuited by D-4) or non-empty
  (rejected by the skipped-cell check). Applied to `PLAN.md` §6 (rewrote the
  three-step check ordering: unseen-hazard check → D-4 empty-response check
  → skipped-cell check → D-10 monotonicity gate) and §11 item 1
  (corrected the D-11 cross-reference to note the split).
- 2026-07-23 — Fix-proposal, scope: full `critiques/2026-07-23-decision-review.md`
  (DR-1 through DR-7). Resolved per your answers: DR-1 → amended D-7 in place
  (`mean`/`scale` now explicitly computed net of D-1's holdout exclusion in
  addition to D-4's empty/echo exclusion, closing the leakage gap); DR-2 →
  new locked `DECISIONS.md` D-11 (D-3's fail-closed cell check now runs
  *before* D-4's empty-response short-circuit, so an unknown/unfit hazard
  fails closed regardless of response content — extended to skipped cells
  too, flagged above for confirmation); DR-4 → no fix, per your instruction
  ("don't worry about it"), AUC reference numbers left as reframed by the
  D-10 pass. Folded in the un-blocked documentation fixes while these entries
  were already open: DR-3 (D-2, D-5, D-7 now cross-reference that their row
  counts are net of D-1/D-4's exclusions), DR-5 (D-3/D-4 Touches lists now
  cite D-11 and their real predict-path/D-5 dependencies), DR-6 (D-5 notes
  that D-10's gated grid search still runs, wastefully but harmlessly, on
  skipped cells), DR-7 (fixed D-4's "prediction-only" → "prompt-repetition-only"
  typo; qualified D-2's Rationale to point at its own amendment). Applied to
  `PLAN.md` §2.3 (`BinaryHead` spec), §3 step 4 (D-7/D-2/D-5 notes), §6
  (`hrc-predict` bullet order and text), §11 item 1 (D-11 cross-reference).
- 2026-07-23 — Critique pass, scope: `DECISIONS.md` D-1 through D-10 reviewed
  against each other for consistency (not PLAN.md prose quality, which was
  covered in the prior deliverable-1 pass). Output:
  `critiques/2026-07-23-decision-review.md`, 7 findings (2
  blocks-correctness, 3 quality, 2 nice-to-have). No `DECISIONS.md` entries
  changed — critique passes decide nothing; see Awaiting User above.
- 2026-07-23 — Fix-proposal, scope D-9/D-10 (monotonicity enforcement
  mechanism). User resolved the D-2 conflict raised in the prior session by
  explicitly authorizing the breakage ("go ahead and allow breakage of D-2's
  'reproduce the toy's behavior exactly' decision") and directing an
  implementation slice be deferred to later. Recorded `DECISIONS.md` D-10
  (locked): gate the high-head decision on the nonzero-head decision, both at
  predict time and inside `optimize_ordinal_thresholds`'s grid-search
  objective (variant B from the prior session's proposal — train/serve
  consistency over literal threshold-value parity). Amended D-2 in place with
  a dated note narrowing its "reproduce exactly" scope: the in-sample fitting
  methodology stays preserved, only the combination-rule objective changed.
  Applied D-10 to `PLAN.md`: §1.1 item 3 (flagged as the one place production
  deliberately deviates from verbatim toy behavior), §2.3 (`predict`'s gated
  combination + `fit`'s matching objective), §3 step 4 (full mechanism
  description, cross-referencing the D-2 amendment), §6 (`hrc-predict`'s
  predict-time gate, ordered after the D-4/D-3 checks), §8.2 (threshold
  optimizer test now asserts monotonicity via adversarial synthetic cases;
  parity-harness reference numbers reframed as a historical baseline, not a
  bit-for-bit target, for this one interaction). No implementation slice run
  — deferred per explicit instruction.
- 2026-07-23 — Fix-proposal, scope D-8 (`class_weight="balanced"`/
  `sample_weight` interaction documented, not fixed). Edited `PLAN.md` §3
  step 4 to add an explicit "Known wart" note: sklearn's balanced class
  weights are computed from `y` alone and ignore the hazard `sample_weight`,
  so the balancing is not actually balanced under 0.25 other-hazard
  weighting; preserved as parity with the toy, must be documented in README
  once one exists. No project README exists yet (same gap noted in the D-2
  pass) — the note lives in `PLAN.md` for now; README authorship is out of
  scope for this pass and remains a §10 phased-build deliverable. No new
  `DECISIONS.md` entry produced.
- 2026-07-23 — Fix-proposal, scope D-7 (standardization statistics unweighted
  over all training rows per component, pinned). Edited `PLAN.md` §2.3's
  `BinaryHead` bullet to state `mean`/`scale` are unweighted and
  component-wide (identical across hazards within a component), distinct
  from the weighted `center_mean`. Added a matching note to §3 step 4 pinning
  the same rule at the point where the fit actually happens, so an
  implementer can't plausibly compute `mean`/`scale` weighted or
  own-hazard-only. No new `DECISIONS.md` entry produced.
- 2026-07-23 — Fix-proposal, scope D-6 (pin training/embedding to CPU; drop
  device auto-select). Edited `PLAN.md` §3 step 3 to remove the
  `--device auto`/`cuda`/`mps` option and state CPU-only explicitly; edited
  §7's dependency table and closing line to state CPU-only torch / no GPU
  auto-detection; edited §8.1's determinism bullet to state the claim holds
  unconditionally now that there's no CUDA/MPS path to scope it around. No
  new `DECISIONS.md` entry produced.
- 2026-07-23 — Fix-proposal, scope D-5 (zero-row cells keep the constant-
  probability substitution but are marked skipped). Edited `PLAN.md` §3 step
  4 to add cell-enumeration wording covering zero-training-row cells
  (constant-probability substitution preserved, cell marked skipped).
  Extended §4's artifact schema with a `status: "fit" | "skipped"` field on
  each `thresholds.json` cell entry. Tightened §6's D-3 fail-closed note,
  which previously had a forward reference to "D-5's per-cell flag once
  that's added to §4" — now points at the concrete `status` field. No new
  `DECISIONS.md` entry produced.
- 2026-07-23 — Fix-proposal, scope D-4 (exclude empty/echo-only responses
  from the fit). Edited `PLAN.md` §3 step 4 to name the response-matrix
  pooling step explicitly and add the exclusion rule (per-component, not a
  zero feature vector) plus the predict-time mirror ("score as 0 directly").
  Added a matching predict-path note to §6 stating this check runs *before*
  D-3's fail-closed cell lookup, so empty/echo-only rows score 0 rather than
  erroring even against an unfit/skipped cell. Note: the queue item's original
  note said predict-time behavior was an open question deferred to Awaiting
  User, but `DECISIONS.md` D-4's decision text already locks predict-time
  behavior explicitly ("treated as 0") and Awaiting User was empty — applied
  it as already-decided rather than treating it as open; flagged below.
  No new `DECISIONS.md` entry produced.
- 2026-07-23 — Fix-proposal, scope D-3 (fail closed on unknown/unfit
  `(component, hazard)` cells at predict time). Resolved §11 open question 1
  in place (no longer open — points to D-3 and to §6) and added an explicit
  fail-closed error contract to §6 `hrc-predict`, covering both genuinely
  unseen hazards and cells that will be marked skipped once D-5 is applied to
  §4's artifact schema (D-5 itself not yet applied — cross-referenced only).
  No new `DECISIONS.md` entry produced; D-3 already existed, this pass only
  applied it to prose.
- 2026-07-23 — Fix-proposal, scope D-2 (preserve in-sample threshold/
  centering bias; document risk). Edited `PLAN.md` §3 step 4 to spell out the
  in-sample threshold/centering bias (near-separated in-sample probabilities,
  the n≥5 per-hazard cliff) as an explicit, deliberately-preserved known risk
  citing D-2, and edited §8.2's parity harness note to state the parity
  target is computed with that bias intact and must not be silently
  "corrected." No project README exists yet to carry the risk note there;
  that's out of scope for this narrow pass. No new `DECISIONS.md` entry
  produced — D-2 already exists; this pass only applied it to prose.
- 2026-07-23 — Critique pass, scope PLAN.md §3 Deliverable 1 (`hrc-train`).
  Output: `critiques/2026-07-23-deliverable-1.md`, 12 findings. No
  `DECISIONS.md` entry produced (critique passes decide nothing).
- 2026-07-23 — Fix-proposal, scope C-1 ("full training set" vs.
  `--holdout-seed-fraction` ambiguity). Edited `PLAN.md` §3 step 4 and the
  `--holdout-seed-fraction` paragraph to state reserved rows are excluded
  from the fit. Recorded as `DECISIONS.md` D-1 (locked).
- 2026-07-23 — Bookkeeping pass converting C-2 through C-10's user responses
  (from the critique's "User Responses" section) into locked `DECISIONS.md`
  entries D-2 through D-9. No PLAN.md prose edited yet — that's queued as
  separate scoped fix-proposal passes above. C-11 and C-12 were explicitly
  deferred by the user and intentionally left out of the ledger.
