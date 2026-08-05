# hazard-response-classifier

Pre-staging implementation of a two-component ordinal hazard-response
classifier: given an AI system's response to a hazardous prompt, score how
much it **Enabled** the hazard and how much it **Legitimized** it (each
0/1/2), and combine those into a final `safe`/`unsafe` label. This
turns a research prototype (internally called "the toy") into a
fit-once, frozen-artifact package with three command-line tools:

- `hrc-train` — fit a model artifact from a labeled CSV.
- `hrc-evaluate` — measure a trained artifact's accuracy against a labeled CSV.
- `hrc-predict` — score new, unlabeled responses with a trained artifact.

This package is the current working baseline, not the Release 1.1 target. See
[`docs/SCIENCE.md`](docs/SCIENCE.md) for the proposed 1.1 scientific standard
and [`PLAN.md`](docs/planning/PLAN.md) for the specification of the baseline
implemented today. `PLAN.md` is the contract for that pre-staging baseline; it
does not override the Release 1.1 target in `SCIENCE.md`.

## Status

The working baseline completed phases 0–5 of `PLAN.md`: all three CLIs are
installed console scripts, backed by 151 tests (unit, integration, and
science), and verified against synthetic fixtures and real, non-mocked BGE
model runs. It has not reached staging and is expected to be replaced by the
Release 1.1 design.

The active work is a science-to-decision review before any 1.1 architecture
or implementation change. [`STATUS.md`](docs/planning/STATUS.md) is the live
queue. [`DECISIONS.md`](docs/planning/DECISIONS.md) is the provenance record —
why each choice was made and what was rejected — with an index mapping every
decision to the specification that now carries it.

## Quick start

```bash
pip install -e .
hrc-train --input examples/sample_input.csv --output-dir /tmp/hrc-demo/model
hrc-evaluate --model-dir /tmp/hrc-demo/model --input examples/sample_input.csv --output-dir /tmp/hrc-demo/eval
hrc-predict --model-dir /tmp/hrc-demo/model --input examples/sample_input.csv --output-dir /tmp/hrc-demo/predict
```

The first run downloads the BGE embedding model (`BAAI/bge-base-en-v1.5`,
~0.4GB) if it isn't already cached — see
[`docs/INSTALL.md`](docs/INSTALL.md). Every command after that runs offline.

## Documentation

| Doc | Covers |
|---|---|
| [`docs/SCIENCE.md`](docs/SCIENCE.md) | Proposed Release 1.1 scientific behavior and evidence requirements |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Release 1.1 evaluator design (§§1–13); baseline module layout and artifact format (§14) |
| [`docs/INSTALL.md`](docs/INSTALL.md) | Install, dependencies, first-run model download |
| [`docs/howto/hrc-train.md`](docs/howto/hrc-train.md) | Training a new artifact |
| [`docs/howto/hrc-evaluate.md`](docs/howto/hrc-evaluate.md) | Measuring a trained artifact |
| [`docs/howto/hrc-predict.md`](docs/howto/hrc-predict.md) | Scoring new, unlabeled responses |
| [`docs/examples/end_to_end_riki_eval.md`](docs/examples/end_to_end_riki_eval.md) | Full train → evaluate → predict walkthrough on a real 859-row dataset |

## Manifest

| Path | What it is |
|---|---|
| `src/hazard_classifier/` | The package: `schema.py` (input validation), `preprocess/` (deobfuscation, segmentation, flags), `embed.py` (BGE embedding + pooling), `heads.py` (per-cell logistic heads), `rules.py` (business rules + ordinal combination), `metrics.py` (evaluation metrics), `model.py` (fit/save/load/score orchestration), `cli/` (the three command-line tools) |
| `tests/` | 151 tests: `unit/`, `integration/` (needs the real BGE model, cached after first run), `science/` (statistical/metric correctness) |
| `examples/sample_input.csv` | 12-row synthetic fixture used in every doc's smoke-test example |
| `data/` | Real labeled datasets, not synthetic fixtures — see that directory's own note below |
| `scripts/` | One-off real-data validation script (`run_real_data_is9.py`) and its captured output (`is9_real_data_metrics.json`) |
| `docs/` | This documentation set |
| `docs/planning/` | The process apparatus this project runs on: |
| `docs/planning/PLAN.md` | The implemented baseline specification, binding until amended |
| `docs/planning/DECISIONS.md` | The decision ledger: why each choice was made and what was rejected. Provenance, not authority — an index maps each decision to the specification that carries its effect |
| `docs/planning/STATUS.md` | Session-to-session queue and progress log |
| `docs/planning/VERIFICATION.md` | Decision → implementation/test coverage matrix |
| `docs/planning/META_PLAN.md` | The process contract governing how the four files above get updated |
| `docs/planning/critiques/` | Dated critique-pass records referenced by `DECISIONS.md` |

**Note on `data/`:** this directory holds real evaluation data (real
jailbreak-style prompts and hazard-relevant model responses used for
research/validation), not synthetic examples — treat it accordingly.

## Current baseline risks

The pre-staging baseline deliberately preserves two statistical problems from
the research prototype rather than silently fixing them. Both are specified in
[`PLAN.md`](docs/planning/PLAN.md) §3; the reasoning is in `DECISIONS.md` D-2
and D-8:

- thresholds and centering values are fitted on the same rows used to fit the
  model, which can make measured performance look better than it will be on
  new data; and
- class balancing ignores the separate hazard-row weights, so the weighted
  training data are not fully balanced.

Real-data validation confirms that the pipeline runs end to end, but the
prototype's published reference numbers were never reproduced exactly because
its source data were unavailable. `STATUS.md` item 1.9 proposes moving a
standalone limitations document to the staging or release-version gate; that
proposal requires agreement from Riki and Kurt.

## Release 1.1 evaluator status

`src/hazard_classifier/evaluator/` is the Release 1.1 pipeline specified in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
[`docs/SCIENCE.md`](docs/SCIENCE.md), built alongside the baseline above, not
a replacement for it yet. It has not reached staging, so per `DECISIONS.md`
D-47's pre-staging floor this is the inline disclosure that decision
requires — it is not the standalone, version-specific limitations document
D-47 requires before staging or a release-point version
(`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6).

Several components are not yet working implementations: some ship as visible
**placeholders** (pass content through unchanged, create no judgment, report
themselves as not evaluated); others ship **partial** against a stated
success criterion — they run and produce results, but do not yet meet
everything that criterion requires, which makes them easy to mistake for
finished. **`docs/ARCHITECTURE.md` §7 is the single, current source for
which components those are and why**, not restated here: it changes as PR 3
through PR 5 land, and a hand-copied list in a second file is one more place
that can fall out of sync with it — the same kind of gap `DECISIONS.md`
D-47's own narrowing-2 correction records and fixes for a different
document. `DECISIONS.md` D-50 and D-51 record the reasoning behind the two
components currently shipping `partial` specifically.

**Four limitations are not components and appear in no table**, so unlike the
list above they are stated here directly (added 2026-08-04; `DECISIONS.md`
D-54 through D-62):

- **Some final-integration rules cannot be reached by the pipeline.** Three of
  `SCIENCE.md` phase B1's five bullets never fire from a real detection, for
  **two different reasons** (the second corrected 2026-08-05, having previously
  been folded into the first):
  - the **refusal** and **narrative** bullets, because both detectors are
    placeholders and no detector ever sets those flags; and
  - the **disclaimer** bullet, for a structural reason instead — B1 runs only
    when working text is exhausted, exhaustion is checked after each of stages
    1–7, and stage 7 never writes `working`, so any response reaching B1 was
    exhausted earlier and skipped disclaimer detection entirely.

  Every exhaustion path therefore lands on prompt-repetition or on the
  blank-payload branch. B1's bullet *ordering* is load-bearing, and in this
  release it is exercised only by hand-constructed flag combinations.
- **Multi-hazard correctness is unevaluated.** Hazard detection is a
  placeholder that returns no additional hazards, and the cross-hazard
  completeness backstop was withdrawn on 2026-08-04. A response whose true
  hazard sits in a stricter family than the supplied one is scored under the
  wrong table and produces a passing result rather than a visible failure.
  See `docs/ARCHITECTURE.md` §12.1.
- **The disclaimer text-view choice is an untested default.** L and E read
  text with disclaimers retained (D-55). The comparison against stripping,
  which `SCIENCE.md` calls for on fixed human-labeled data, has not been run.
- **The prompt-disambiguation exception is unexercised** (D-60). The models
  receive response-derived text only; nobody has determined what prompt
  context the Assessment Standard actually permits.

**The L/E model structure was selected without demonstrating an improvement**
(D-68, added 2026-08-05). Release 1.1 uses a per-hazard flat three-class
multinomial softmax for both Legitimization and Enablement. That structure was
chosen by a pre-registered comparison, but **no candidate beat the incumbent
two-head mechanism on either target**, and on Legitimization the selected
structure scored *below* it. It was selected because every higher-scoring
candidate is a two-head structure that cannot produce the three-class
distribution `docs/SCIENCE.md` requires — not because it was shown to be
better. Every figure behind that comparison is a development-set number (see
below), so it supports no quality claim in either direction.

**The ground truth is real but out of version** (D-63 through D-66, added
2026-08-04). The Standards team's fixed dataset and approved success criteria
are not arriving, so Release 1.1 is fitted and selected against the Jailbreak
v1.0 human ground truth already in `data/`. The labels are genuine human
judgments — not synthetic, and not model-generated — but four things follow:

- **They were made against Jailbreak v1.0, not Assessment Standard v1.4.**
  Measured compatibility is 97.2%: applying `docs/SCIENCE.md`'s L/E-to-result
  tables to the human L/E values reproduces the source's own safe/unsafe label
  on 835 of 859 rows, with disagreement concentrated in the two families whose
  tables changed (enablement-only 7.3%, Specialized Advice 7.4%, default 0.2%).
- **Attacked prompts only** (D-65). `docs/SCIENCE.md` requires training
  coverage of naive prompts too; no row supplies it, and none can be
  manufactured without producing AI labels.
- **Development-set numbers only** (D-66). The 224-row held-out slice is a dev
  set. Nothing measured on it is a benchmark result or a generalization
  estimate, and a real evaluation set — should one arrive — triggers a fresh
  structure selection, not a re-fit.
- **No approved success criteria exist**, so both the Legitimization and
  Enablement models are reported as *not evaluated* whatever their measured
  numbers.

No quality, coverage, or scientific-success claim is made for any component
§7 marks `partial` or `placeholder`, per `SCIENCE.md` §Evidence and outputs'
not-evaluated rule, nor for anything in the list immediately above. Release
1.1 ships as a **pre-staging prototype** (`DECISIONS.md` D-58); whether to
promote it is an explicit PR 6 decision.
