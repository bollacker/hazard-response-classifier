# Software architecture

## Module map

```
schema.py         Input CSV validation (mode-scoped required columns, hazard
                   normalization, label range checks). No knowledge of
                   hazard families — that requires a loaded artifact.
pipeline.py       Versioned component handoffs, datastore identity, and the
                   ordered upstream response-preparation workflow. Incomplete
                   components are explicit pass-through placeholders.
preprocess/
  decode.py        Pure decoding helper used by pipeline.py.
  segment.py       Pure sentence/bullet/code segmentation helper.
  flags.py         Pure prompt-repetition / disclaimer flag helpers.
embed.py           BGE sentence embedding (CPU-only) + mean pooling.
                   build_component_features() is the ONE shared raw-text→
                   features pipeline every entry point uses (see below).
heads.py           BinaryHead: standardize + logistic regression + centering.
                   No notion of hazard or component identity — fits/serves
                   one already-filtered, already-weighted binary head.
rules.py           Two independent rule families:
                   - ordinal_prediction / optimize_ordinal_thresholds
                     (monotonicity-gated combination of the two heads)
                   - resolve_component_action (predict-time fail-closed
                     resolution: not_required / fail_unseen_hazard /
                     fail_skipped_cell / score_zero / serve)
                   Plus hazard_family, discrete_v14_label, v14_overall_score,
                   apply_legitimization_disclaimer_rule.
metrics.py         component_metrics, final_label_metrics, holdout
                   partitioning, metrics.csv/summary.txt rendering.
model.py           Orchestration: fit, save/load (artifact I/O), score_row
                   (per-row predict/evaluate pipeline), evaluate_rows,
                   predict_rows, HazardResponseClassifier.score (the
                   in-process batch API).
cli/
  _common.py       Shared argparse pieces (--allow-download), fatal(),
                   the skipped-component load-time warning.
  train.py         hrc-train
  evaluate.py      hrc-evaluate
  predict.py       hrc-predict
config.py          Hazard-family sets (installed defaults only — never
                   consulted at predict/evaluate time; see below), the
                   default embedding model name, the head-fit random seed.
```

## One shared feature-building pipeline

Every entry point that needs real embeddings — `hrc-train`, `hrc-evaluate`,
`hrc-predict`, and the in-process `HazardResponseClassifier.score` API — goes
through the same function, `embed.build_component_features`. There is no
per-CLI copy of the preprocess→embed→pool pipeline.

```mermaid
flowchart TD
    subgraph Shared pipeline
    A[prompt ID, response ID, request ID] --> B[pipeline.prepare_response]
    A1[prompt_text, response_text, intended hazard] --> B
    B --> B1[ordered, versioned component results]
    B --> C[embed.embed_sentences - BGE, batched]
    C --> D[pool per component: enablement / legitimization]
    end
    D --> E1[hrc-train: model.fit]
    D --> E2[hrc-evaluate: model.evaluate_rows]
    D --> E3[hrc-predict: model.predict_rows]
    D --> E4["HazardResponseClassifier.score (in-process API)"]

    E1 --> F[Artifact: heads.npz / thresholds.json / rules.json / manifest.json]
    F --> E2
    F --> E3
    F --> E4
```

`pipeline.prepare_response` is the single upstream component workflow used by
the shared feature builder. Each component result records the component and
Assessment Standard versions, implementation status, input text, output text,
judgments, and the supplied datastore identity. The prepared response also
retains the supplied intended hazard as context for the future
hazard-detection component. A `placeholder` is enforced as a no-op: it must pass text
through unchanged and cannot emit judgments. The current hazard-detection,
narrative-analysis, and refusal-analysis entries are placeholders; their
presence does not change a score.

## Identity and provenance

The production identity is the combination of three opaque datastore IDs:
`prompt_id`, `response_id`, and `request_id`. The same prompt and response
text may appear in more than one request, so text and row order are not
identities. `pipeline.EvaluationIdentity` carries all three IDs unchanged on
the prepared response, every prepared segment, and every component result.
Text-only helpers such as `preprocess.decode.best_readable_view` do not know
about IDs; `pipeline.prepare_response` owns the identity envelope around them.

The in-process `HazardResponseClassifier.score` API requires these three IDs
on every `PredictRow` and returns them on every `RowResult`, including failed
rows. Its existing `prompt_uid` field remains as a legacy caller row key for
compatibility; it is not the datastore identity. The CSV CLIs still accept
that legacy schema and do not yet supply the three datastore IDs. They are a
temporary adapter, not the production datastore contract.

`model.score_row` is the shared per-row scoring function underneath
`evaluate_rows`/`predict_rows`/`score` — all three differ only in what they
do with a hard-fail row (`hrc-evaluate` excludes it and tallies a count;
`hrc-predict` and `score` route it to a separate failures/result entry and
continue).

## Artifact format

`hrc-train`'s output directory is the frozen contract between training and
everything downstream:

| File | Contents |
|---|---|
| `heads.npz` | Every fitted `BinaryHead`'s `mean`/`scale`/`coef`/`intercept`/`constant_probability`/`center_mean`/`status` arrays, keyed deterministically as `{component}__{hazard}__{nonzero,high}__{field}` |
| `thresholds.json` | Per-cell `status` (`"fit"`/`"skipped"`), `nonzero_threshold`, `high_threshold`, and the threshold search's own training-time metrics |
| `rules.json` | `trained_hazards`, `hazard_family` per hazard, and the artifact's own frozen `enablement_only_hazards`/`specialized_advice_hazards` sets |
| `manifest.json` | `holdout_seed_prompt_ids`, `skipped_components`, `embedding_model_name`/`revision`, the Assessment Standard/pipeline/component versions and statuses, plus optional provenance fields `hrc-train` fills in (`code_version`, `hyperparameters`, `training_timestamp`, `training_file_hash`, `training_row_count`, `training_hazard_counts`) |

Two deliberate architectural choices worth knowing about:

- **Hazard-family sets are read from the artifact, never installed
  `config.py` defaults, at predict/evaluate time (D-23).** `rules.json`
  freezes the exact sets the artifact was trained with. This is why
  `rules.py`/`metrics.py` take `enablement_only_hazards`/
  `specialized_advice_hazards` as required parameters everywhere, with no
  default that could silently fall back to whatever `config.py` says today —
  an artifact trained months ago must always score consistently with
  itself, even if `config.py`'s defaults change later.
- **No `joblib`, no pickle (D-6, D-37)** — the artifact is `.npz` + JSON
  only, and training always runs on CPU. Both were explicit choices to keep
  the artifact format simple, portable, and free of a pickle-based security
  surface.

## CLI layer

Each of the three CLIs is a thin wrapper: argparse → `schema.load_csv` →
(`model.load` for evaluate/predict) → `embed.build_component_features` →
one `model.py` orchestration call → file output. None of them contain
business logic of their own — see
[`docs/howto/`](howto/) for each command's actual flags and outputs.
