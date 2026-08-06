# HOWTO: `hrc-run`

Run the **Release 1.1** evaluator over an unlabeled CSV — the ten-stage
pipeline in [`../ARCHITECTURE.md`](../ARCHITECTURE.md), not the baseline
scorer. No labels, no retraining.

> **Read [`../../README.md` §Release 1.1 evaluator status](../../README.md#release-11-evaluator-status)
> before using any output.** Release 1.1 is a **pre-staging prototype** — a
> posture decided on the evidence and not a default (`DECISIONS.md` D-81,
> 2026-08-05, discharging D-58's exit item): three of its ten stages are
> visible placeholders,
> three more ship `partial`, and no component has an approved success
> criterion, so every one of them is reported as *not evaluated* under
> `SCIENCE.md` §Evidence and outputs. **That includes the L and E models,
> which now emit a real three-class distribution and are still not
> evaluated** — the structure they use was selected on a null result (D-68),
> and a distribution summing to 1 is arithmetic, not evidence. The results
> this command writes support no quality claim in either direction.

`hrc-run` is a **fourth** CLI, not a change to the three baseline ones
(`DECISIONS.md` D-48). `hrc-predict` is the baseline's unlabeled scorer and
means something different; `hrc-evaluate` scores *labelled* rows against
ground truth.

## Required input schema

Six columns, all required
(`evaluator/input_schema.py::REQUIRED_COLUMNS`):

`request_id, prompt_uid, response_id, prompt_text, response_text,
supplied_hazard`

This is **not** the baseline's schema — it carries `request_id` and
`response_id`, which the baseline's does not, and it names the hazard column
`supplied_hazard` to match the carried record. Extra columns are ignored.

Validation here is **structural only**: a missing column, a blank
`request_id`/`prompt_uid`/`response_id`, or a duplicate `response_id`. A
blank `response_id` is rejected rather than synthesized — identity is the
input's contract, and a synthesized id silently breaks your join back to your
own data. A blank `response_text` is legitimate input: detecting exactly that
is stage 1's job.

Whether the hazard is *valid* is a separate check, made against the run's
resolved scope — see **What makes it fail**.

## The run profile

A JSON file, because it is provenance you should be able to diff:

```json
{
  "artifact_id": "/path/to/artifact",
  "hazard_scope": ["hte", "prv"],
  "component_selection": {"hazard_detection": "placeholder"},
  "text_view": "working"
}
```

| Field | Required | Meaning |
|---|---|---|
| `artifact_id` | yes | Artifact directory to score against — **either format**. A Release 1.1 evaluator artifact (`scripts/build_release_artifact.py`, `ARCHITECTURE.md` §10.1) scores with the real three-class model; a baseline artifact scores with PR 1's wrapped two-head model, which reports `distribution: null`. The formats are told apart by the 1.1 manifest's `format` field |
| `hazard_scope` | no | The run's active hazard set. Omit it and it **defaults to the artifact's own frozen supported set** (D-57), which is what makes the default unrejectable. A narrower set is allowed; a wider one is a run rejection |
| `component_selection` | no | `stage -> implementation_id` overrides; every stage not named keeps its default. Selection is resolved through the registry, never by importing a component (`ARCHITECTURE.md` §6). **Stage 9 is the exception**: its implementation follows the artifact, because the other scorer has no model in that artifact to score with |
| `text_view` | no | Which text view stage 8 embeds, default `working` (D-74, D-55). `disclaimer_stripped` is the only other view any 1.1 component publishes |

The resolved hazard scope, the artifact id, the rule version, and every
stage's selected implementation and version are recorded in **every** output
record — that is the provenance `SCIENCE.md` §Evidence and outputs requires.

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `--profile` (required) | — | The run profile JSON above |
| `--input` (required) | — | 1.1 input CSV |
| `--output-dir` | — | Directory to write the three views to. **Required unless `--check-input` is given** |
| `--check-input` | off | Pre-flight only: report every row that would reject the run, then exit without scoring anything. Exits 1 if any would |
| `--model-dir` | — | Overrides the profile's `artifact_id`, so one checked-in profile can be reused across machines |
| `--allow-download` | off | Allow downloading BGE weights not already cached |

## Checking an input before you run it

`--check-input` answers "would this be rejected?" without scoring anything
(`DECISIONS.md` D-75). It runs exactly the run's own rejection conditions —
the input's structural contract, the profile's hazard scope against the
artifact, and every row's supplied hazard — and stops there:

```bash
hrc-run --profile profile.json --input rows.csv --check-input
```

```
hrc-run: 3 of 10000 row(s) would reject the run (hazard_scope=['hte', 'prv']):
  row 37 (response_id='resp-37'): supplied_hazard='typo_hazard' is not in hazard_scope=['hte', 'prv']
  row 4021 (response_id='resp-4021'): supplied_hazard='typo_hazard' is not in hazard_scope=['hte', 'prv']
  row 9999 (response_id='resp-9999'): supplied_hazard='typo_hazard' is not in hazard_scope=['hte', 'prv']
```

Exit 0 and a one-line all-clear when nothing would reject; exit 1 and the
list above when something would. It costs about **two seconds on 10,000
rows** — the artifact is loaded and the components are built, but the
encoder's weights load lazily and nothing is embedded.

**A clean check is a genuine prediction, not an approximation.** The only
thing between it and a scored batch is the pipeline itself, whose failures
are per-row and never reject a run. The check and the run read the same rule
rather than two copies of it, so they cannot disagree — but the run still
performs its own validation, because the file can change between the two
calls.

Available in process as `entrypoint.check_input(profile, input_path)`,
returning a `CheckReport` with `.ok`, `.rows`, `.hazard_scope`, and
`.problems`.

## Output

Three files, **always all three** on a completed run
(`ARCHITECTURE.md` §11 — each is a separately versioned view of the same
canonical record):

- **`results.jsonl`** — one record per input row, in input order. The only
  lossless output: every text view, every stage observation, every flag,
  every per-hazard judgment, and the run's provenance. Large by design; the
  pooled embedding vector is the one thing omitted.
- **`predictions.csv`** — one row per `(response, hazard)`, carrying no text.
- **`failures.csv`** — one row per **failed** hazard, carrying no text.
  Written with a header even when empty, so a downstream step can read it
  unconditionally.

`failures.csv` and `results.jsonl` are **not** exclusive: a row that failed
appears in both. Run rejections appear in neither — see below.

Same input, same profile, same artifact ⇒ byte-identical outputs.

## Example

```bash
printf '{"artifact_id": "/tmp/hrc-demo/model"}\n' > /tmp/hrc-demo/profile.json
hrc-run \
  --profile /tmp/hrc-demo/profile.json \
  --input /tmp/hrc-demo/rows.csv \
  --output-dir /tmp/hrc-demo/run
column -s, -t < /tmp/hrc-demo/run/predictions.csv | head
```

The same run is available in process, and the CLI is a thin wrapper over it,
so the two produce identical records for identical input:

```python
from hazard_classifier.evaluator import entrypoint
from hazard_classifier.evaluator.profile import RunProfile

records = entrypoint.run(RunProfile(artifact_id="/tmp/hrc-demo/model"),
                         "/tmp/hrc-demo/rows.csv", "/tmp/hrc-demo/run")
```

## What makes it fail

Two different things, and the difference matters
(`ARCHITECTURE.md` §2):

- **A run rejection** is about the run's configuration or its input
  contract. It aborts **before any row is scored** and writes **no output
  file at all** — not even a partial one. Three causes: a supplied hazard
  that is missing, unrecognized, or outside the resolved scope *on any row*;
  a `hazard_scope` wider than the artifact supports; a selected
  implementation that is not registered. The message names **every**
  offending row — its position, its `response_id`, and its reason — plus the
  resolved scope they were checked against (D-75). It lists the first ten
  and counts the rest; `--check-input` lists them all.

  **This is all-or-nothing on purpose**, and it is the one behavior most
  likely to surprise you on a large file: one bad hazard code in row 40,000
  means no row is scored. What it does *not* cost is time — the check runs
  before any scoring, so a 10,000-row file is rejected in about two seconds
  with nothing embedded and nothing thrown away. Use `--check-input` to see
  the whole list before committing to a run.

- **A per-row failure** is about one row's content. It never aborts the
  batch: the row gets a `failures.csv` entry, its record still lands in
  `results.jsonl`, and the run continues. Every input row always produces
  exactly one record.

Malformed input (a missing column, a blank identity, a duplicate
`response_id`) and a profile with no `artifact_id` exit 1 with a plain
message, matching the other CLIs' `fatal()` style.

## Cost

One embedding call per record, shared across every hazard evaluated for it
(`ARCHITECTURE.md` §8) — so an N-row batch makes up to N encoder calls. Rows
whose working text is exhausted (empty or prompt-only responses) never reach
the encoder at all.

On real data (177 rows, mean response ~2.5k characters, CPU-only), that is
roughly **4.8 rows/second** in steady state, plus a one-off ~4.5 s on the
first row while the encoder's weights load. Reproduce with
`python scripts/probe_runner_throughput.py`. The evaluator's contract is
**single-threaded per process** (D-61); parallelism, if you need it, is at
the process level.
