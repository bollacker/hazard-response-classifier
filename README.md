# hazard-response-classifier

Production implementation of a two-component ordinal hazard-response
classifier: given an AI system's response to a hazardous prompt, score how
much it **Enabled** the hazard and how much it **Legitimized** it (each
0/1/2), and combine those into a final `safe`/`unsafe` label. This
productionizes a research prototype (internally called "the toy") into a
fit-once, frozen-artifact package with three command-line tools:

- `hrc-train` — fit a model artifact from a labeled CSV.
- `hrc-evaluate` — measure a trained artifact's accuracy against a labeled CSV.
- `hrc-predict` — score new, unlabeled responses with a trained artifact.

See [`docs/SCIENCE.md`](docs/SCIENCE.md) for what the model actually does and
every assumption behind it, and [`PLAN.md`](docs/planning/PLAN.md) for the
full normative spec this package implements.

## Status

Phases 0–5 of `PLAN.md`'s build plan are complete: all three CLIs are
installed console scripts, backed by 142 tests (unit, integration, and
science), verified against both synthetic fixtures and real, non-mocked BGE
model runs. Every design decision behind the implementation is recorded in
[`DECISIONS.md`](docs/planning/DECISIONS.md) (D-1 through D-37);
[`STATUS.md`](docs/planning/STATUS.md) tracks session-to-session progress.
Phase 6 (this documentation set, plus CI wiring) is the only remaining item
on `PLAN.md`'s own phase table.

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
| [`docs/SCIENCE.md`](docs/SCIENCE.md) | What the model does, the pipeline stages, and every stated assumption/known limitation |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Module layout, data flow, artifact format |
| [`docs/INSTALL.md`](docs/INSTALL.md) | Install, dependencies, first-run model download |
| [`docs/howto/hrc-train.md`](docs/howto/hrc-train.md) | Training a new artifact |
| [`docs/howto/hrc-evaluate.md`](docs/howto/hrc-evaluate.md) | Measuring a trained artifact |
| [`docs/howto/hrc-predict.md`](docs/howto/hrc-predict.md) | Scoring new, unlabeled responses |
| [`docs/examples/end_to_end_riki_eval.md`](docs/examples/end_to_end_riki_eval.md) | Full train → evaluate → predict walkthrough on a real 859-row dataset |

## Manifest

| Path | What it is |
|---|---|
| `src/hazard_classifier/` | The package: `schema.py` (input validation), `preprocess/` (deobfuscation, segmentation, flags), `embed.py` (BGE embedding + pooling), `heads.py` (per-cell logistic heads), `rules.py` (business rules + ordinal combination), `metrics.py` (evaluation metrics), `model.py` (fit/save/load/score orchestration), `cli/` (the three command-line tools) |
| `tests/` | 142 tests: `unit/`, `integration/` (needs the real BGE model, cached after first run), `science/` (statistical/metric correctness) |
| `examples/sample_input.csv` | 12-row synthetic fixture used in every doc's smoke-test example |
| `data/` | Real labeled datasets, not synthetic fixtures — see that directory's own note below |
| `scripts/` | One-off real-data validation script (`run_real_data_is9.py`) and its captured output (`is9_real_data_metrics.json`) |
| `docs/` | This documentation set |
| `docs/planning/` | The process apparatus this project runs on: |
| `docs/planning/PLAN.md` | The normative spec: what the package must do |
| `docs/planning/DECISIONS.md` | The locked decision ledger (D-1…D-37): every design choice, its rationale, and what was rejected |
| `docs/planning/STATUS.md` | Session-to-session queue and progress log |
| `docs/planning/VERIFICATION.md` | Decision → implementation/test coverage matrix |
| `docs/planning/META_PLAN.md` | The process contract governing how the four files above get updated |
| `docs/planning/critiques/` | Dated critique-pass records referenced by `DECISIONS.md` |

**Note on `data/`:** this directory holds real evaluation data (real
jailbreak-style prompts and hazard-relevant model responses used for
research/validation), not synthetic examples — treat it accordingly.

## Known limitations

The model deliberately preserves some of the original research prototype's
statistical quirks rather than silently fixing them (see `DECISIONS.md` D-2,
D-8). Real-data validation (D-34) confirms the pipeline works end-to-end and
produces plausible held-out metrics, but the original prototype's exact
published reference numbers were never reproduced bit-for-bit — its source
data never resurfaced. See [`docs/SCIENCE.md`](docs/SCIENCE.md)'s "Known
limitations and accepted risk" section for the full list.
