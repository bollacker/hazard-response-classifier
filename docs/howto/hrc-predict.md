# HOWTO: `hrc-predict`

Score new responses with a trained artifact — no labels needed, no
retraining (`PLAN.md` §6).

## Required input schema

Only the five predict-mode columns are required: `seed_prompt_id,
prompt_uid, prompt_text, response_text, hazard`. The three ground-truth
columns (`enablement_value`, `legitimization_value`, `is_safe_ground_truth`)
are optional — if present, they're **entirely ignored**, not even
range-checked (D-24), so a labeled CSV can be reused for prediction
unchanged.

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--model-dir` (required) | — | Artifact directory `hrc-train` wrote |
| `--input` (required) | — | CSV to score |
| `--output-dir` (required) | — | Directory to write `predictions.csv`/`failures.csv` to |
| `--allow-download` | off | Allow downloading BGE weights not already cached |

As with `hrc-evaluate`, embedding always uses the artifact's own recorded
model/revision — there's no `--model-name` override.

## Output

Every input row lands in **exactly one** of two files (D-22):

- **`predictions.csv`** — columns `prompt_uid, hazard,
  enablement_predicted, legitimization_predicted, v14_overall_unsafe_score,
  predicted_label, rule_reasons`. `legitimization_predicted` is blank for an
  enablement-only hazard (Legitimization isn't scored at all, D-18).
  `rule_reasons` is a `|`-joined string of any business rules that fired
  (e.g. `enablement_zeroed_no_effective_sentences`,
  `specialized_advice_disclaimer_reduces_legitimization`) — empty if none
  did. Note `seed_prompt_id` is **not** in the output — `prompt_uid` alone
  identifies a row (D-25).
- **`failures.csv`** — columns `prompt_uid, hazard, failure_reason`, where
  `failure_reason` is `unseen_hazard` (a hazard code the artifact never saw
  at train time) or `skipped_or_absent_cell` (a non-empty response landing
  on a cell the artifact marked degenerate/skipped, or a cell missing
  entirely). Always written with a header, even when empty.

`len(predictions) + len(failures) == len(input rows)`, always.

## Example

```bash
hrc-predict \
  --model-dir /tmp/hrc-demo/model \
  --input examples/sample_input.csv \
  --output-dir /tmp/hrc-demo/predict
column -s, -t < /tmp/hrc-demo/predict/predictions.csv | head
```

## What makes it fail

`predict_rows` itself never raises per-row — every hard-fail case routes to
`failures.csv` instead of aborting the batch. The only `fatal()` (exit-1)
paths are:

- **Bad `--model-dir`** — `FileNotFoundError` from `model.load`.
- **Schema-invalid `--input`** — missing a required predict-mode column, or
  an unrecognized structural problem (`SchemaError`).
