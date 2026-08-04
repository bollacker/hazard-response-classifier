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
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Current baseline module layout, data flow, and artifact format |
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
