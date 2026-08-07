# HOWTO: `hrc-train`

Train a `HazardResponseClassifier` artifact from a labeled CSV
(`PLAN.md` §3).

## Required input schema

All eight columns from `schema.py`'s train-mode requirements must be
present:

`seed_prompt_id, prompt_uid, prompt_text, response_text, hazard,
enablement_value, legitimization_value, is_safe_ground_truth`

- `enablement_value`/`legitimization_value` must be blank or exactly `0`,
  `1`, or `2`.
- `is_safe_ground_truth` must be blank or exactly `safe`/`unsafe` (D-30) —
  not range-checked at load time, only by callers that parse it.
- A blank `legitimization_value` is only tolerated for enablement-only
  hazards (`prv`, `sxc_prn` by default) — otherwise it's a data defect
  `hrc-train`/`hrc-evaluate` will reject at fit/evaluate time.

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--input` (required) | — | Labeled training CSV |
| `--output-dir` (required) | — | Directory to write the artifact to (created if missing) |
| `--other-hazard-weight` | `0.25` | Sample weight for non-target-hazard rows in each cell's fit |
| `--model-name` | `BAAI/bge-base-en-v1.5` | BGE model id to embed responses with |
| `--holdout-seed-fraction` | `0.0` | Fraction of `seed_prompt_id` groups to reserve for `hrc-evaluate`'s held-out measurement (D-1) — `0` means no holdout, every row trains |
| `--allow-download` | off | Allow downloading BGE weights not already cached |

## Output

The artifact directory: `heads.npz`, `thresholds.json`, `rules.json`,
`manifest.json`. See
[`PLAN.md` §4](../planning/PLAN.md#4-model-artifact-format) for what each file
holds.

*(Corrected 2026-08-07: this pointed at `ARCHITECTURE.md#artifact-format`, an
anchor that does not exist — and the section it was reaching for,
`ARCHITECTURE.md` §10, specifies the **Release 1.1** artifact, which has a
`model/` directory and no `heads.npz`. `hrc-train` writes the **baseline**
artifact, and `PLAN.md` §4 is its specification. A reader who followed the old
link found a description of a different format.)*

## Example

```bash
hrc-train \
  --input examples/sample_input.csv \
  --output-dir /tmp/hrc-demo/model \
  --holdout-seed-fraction 0.2
```

Console output reports rows/hazards loaded, hazards trained, how many
`seed_prompt_id` groups were reserved for holdout (if any), and warns if any
component came out wholly skipped (D-28).

## What makes it fail

- **Schema-invalid `--input`** (missing/misnamed column, an out-of-range
  ordinal value) — a clean one-line error via `SchemaError`, exit code 1.
- **A wholly-skipped Enablement component** — `WhollySkippedEnablementError`:
  every training row's Enablement label was single-class after exclusions,
  so no usable artifact could be produced at all (Enablement is required for
  every hazard). A wholly-skipped **Legitimization** does *not* fail the
  run — it warns and writes an artifact usable only for enablement-only
  hazards.
- **Model not cached and no `--allow-download`** — `sentence-transformers`
  raises; pass `--allow-download` once (see
  [`../INSTALL.md`](../INSTALL.md)).
