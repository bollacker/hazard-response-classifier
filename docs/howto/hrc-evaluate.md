# HOWTO: `hrc-evaluate`

Measure a trained artifact's accuracy against a labeled CSV — no retraining
(`PLAN.md` §5).

## Required input schema

Same eight columns as `hrc-train` (evaluate mode requires the same
ground-truth columns as train mode — see
[`hrc-train.md`](hrc-train.md#required-input-schema)).

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--model-dir` (required) | — | Artifact directory `hrc-train` wrote |
| `--input` (required) | — | Labeled evaluation CSV |
| `--output-dir` (required) | — | Directory to write `metrics.json`/`metrics.csv`/`summary.txt` to |
| `--allow-download` | off | Allow downloading BGE weights not already cached |

`--model-name` isn't a flag here — the artifact's own recorded
`embedding_model_name`/`embedding_model_revision` (`manifest.json`) is
always used, so evaluation is guaranteed to embed with the same model the
artifact was trained on (D-23).

## Output

- **`metrics.json`** — the full report: `holdout_recorded`,
  `excluded_row_count` (split into `excluded_unseen_hazard_count`/
  `excluded_skipped_cell_count`), then a `held_out` and/or
  `in_sample_unrecorded` section (only present if that population is
  non-empty), each with per-component metrics (`n`, `exact_accuracy`,
  `within_one_accuracy`, `binary_present_accuracy`, `auc`, `qwk`, `mae`,
  `confusion_counts`) and `final_label` metrics (`precision`, `recall`,
  `f1`, `false_safe_rate`, `false_unsafe_rate`).
- **`metrics.csv`** — the same report flattened to one row per
  `(population, section, metric, value)` — a long format, not a second
  independently-designed schema.
- **`summary.txt`** — a short human-readable rendering of the same numbers.

If the artifact has no recorded holdout split (the `--holdout-seed-fraction`
default), every row lands in `in_sample_unrecorded` and both the console and
`summary.txt` print an explicit warning that no number in the report is a
verified generalization number (D-13).

`auc`/`qwk` are `null` rather than a raw `NaN` whenever the population being
measured is degenerate (single-class) for that component (D-16/D-33).

## Example

```bash
hrc-evaluate \
  --model-dir /tmp/hrc-demo/model \
  --input examples/sample_input.csv \
  --output-dir /tmp/hrc-demo/eval
cat /tmp/hrc-demo/eval/summary.txt
```

## What makes it fail

- **Bad `--model-dir`** — `FileNotFoundError` from `model.load`, reported
  as a clean one-line error.
- **Schema-invalid `--input`** — `SchemaError`, same as `hrc-train`.
- **A known, non-enablement-only hazard row with a blank ground-truth
  value** (`BlankGroundTruthError`, D-26) — this is treated as a data
  defect and aborts the whole run, unlike a hard-fail row (which is simply
  excluded and counted, not treated as a defect).
