"""Derived views (`docs/ARCHITECTURE.md` §11).

The record is canonical; every output is a view derived from it, never the
record itself, and each view is a **named, versioned flattening contract**
rather than an implicit one -- one of the two counterarguments recorded
against the canonical-record proposal, answered here explicitly.

Two views are built in slice 1C:

- `result_view` -- the lossless `results.jsonl` record (§11 row 1).
- `prediction_rows` -- the per-`(response, hazard)` `predictions.csv`
  flattening (§11 row 2).

`metrics.json` and `failures.csv` are not built here: `metrics.json` needs
the per-outcome metrics and uncertainty estimates `SCIENCE.md`
§Estimability requires (blocked on PR 5's real three-class model and the
Standards team's approved criteria), and `failures.csv` needs the
batch-level runner that does not exist yet. Naming them as unbuilt is the
point -- §11 lists four views, and two of them have real prerequisites.

**Sensitive-data retention (§11's other recorded counterargument) is bounded
here, not at the record.** The record carries every text version;
`prediction_rows` deliberately carries none, matching what the baseline's
own `predictions.csv` exposed. `result_view` is the lossless artifact and
does include text, which is exactly why it is a separate view a consumer
opts into.
"""

from __future__ import annotations

from typing import Any

from .record import EvaluationRecord

RESULT_VIEW_VERSION = "1"
PREDICTION_ROWS_VERSION = "1"

PREDICTION_COLUMNS = (
    "request_id",
    "prompt_uid",
    "response_id",
    "hazard",
    "hazard_source",
    "legitimization_applies",
    "provisional_l",
    "provisional_e",
    "final_l",
    "final_e",
    "decided_by",
    "result",
    "failure_reason",
    "overall_result",
)


def _judgment_view(judgment) -> dict[str, Any] | None:
    if judgment is None:
        return None
    return {
        "label": judgment.label,
        # None when the implementation cannot produce a three-class
        # multinomial (ARCHITECTURE.md §4). Consumers must handle the
        # absence rather than assume a distribution is present.
        "distribution": list(judgment.distribution) if judgment.distribution is not None else None,
        "model_version": judgment.model_version,
    }


def _run_view(run: Any) -> dict[str, Any] | None:
    """The run context, flattened. This is what carries "enough provenance
    to reproduce the result" (`SCIENCE.md` §Evidence and outputs) into the
    output: the artifact id, the rule version, and the exact
    implementation **and version** selected for every stage.
    """
    if run is None:
        return None
    return {
        "artifact_id": run.artifact_id,
        "rule_version": run.rule_version,
        "hazard_scope": sorted(run.hazard_scope),
        "component_selections": {
            stage: {"implementation": selection.implementation, "version": selection.version}
            for stage, selection in run.component_selections.items()
        },
    }


def result_view(record: EvaluationRecord) -> dict[str, Any]:
    """The lossless `results.jsonl` view (§11). JSON-serializable: every
    tuple becomes a list, every mapping a plain dict, and the embedding
    stage's pooled vector is **omitted** -- it is a large float array with
    no audit value, and `ARCHITECTURE.md` §11 explicitly bounds payload
    size at the view layer rather than at the record.
    """
    return {
        "view_version": RESULT_VIEW_VERSION,
        "request_id": record.request_id,
        "prompt_uid": record.prompt_uid,
        "response_id": record.response_id,
        "supplied_hazard": record.supplied_hazard,
        "run": _run_view(record.run),
        "prompt_text": record.prompt_text,
        "response_text": record.response_text,
        "texts": {
            "original": record.texts.original,
            "decoded": record.texts.decoded,
            "working": record.texts.working,
            "history": [{"stage": step.stage, "text": step.text} for step in record.texts.history],
            "named": dict(record.texts.named),
        },
        "exhausted_at": record.exhausted_at,
        "observations": [
            {
                "stage": observation.stage,
                "implementation": observation.implementation,
                "version": observation.version,
                "maturity": observation.maturity,
                "outcome": observation.outcome,
                "facts": {
                    key: value
                    for key, value in observation.facts.items()
                    if key != "pooled_vector"
                },
                "text_out": observation.text_out,
                "error": (
                    None
                    if observation.error is None
                    else {
                        "stage": observation.error.stage,
                        "message": observation.error.message,
                        "hazard": observation.error.hazard,
                    }
                ),
            }
            for observation in record.observations
        ],
        "detected_hazards": list(record.detected_hazards),
        "evaluated_hazards": list(record.evaluated_hazards),
        "flags": {
            "empty_payload": record.flags.empty_payload,
            "decoding_failed": record.flags.decoding_failed,
            "prompt_repetition": record.flags.prompt_repetition,
            "narrative": record.flags.narrative,
            "narrative_subtypes": dict(record.flags.narrative_subtypes),
            "refusal": record.flags.refusal,
            "sa_disclaimer": record.flags.sa_disclaimer,
        },
        "per_hazard": {
            hazard: {
                "hazard": judgment.hazard,
                "source": judgment.source,
                "legitimization_applies": judgment.legitimization_applies,
                "provisional_l": _judgment_view(judgment.provisional_l),
                "provisional_e": _judgment_view(judgment.provisional_e),
                "final_l": judgment.final_l,
                "final_e": judgment.final_e,
                "decided_by": judgment.decided_by,
                "result": judgment.result,
                "failure_reason": judgment.failure_reason,
            }
            for hazard, judgment in record.per_hazard.items()
        },
        "overall_result": record.overall_result,
        "overall_failure_reason": record.overall_failure_reason,
    }


def prediction_rows(record: EvaluationRecord) -> list[dict[str, Any]]:
    """The `predictions.csv` view (§11): one row per `(response, hazard)`,
    with `PREDICTION_COLUMNS`'s exact keys and order. Carries no text.
    """
    rows: list[dict[str, Any]] = []
    for hazard in record.evaluated_hazards:
        judgment = record.per_hazard.get(hazard)
        if judgment is None:
            continue
        rows.append(
            {
                "request_id": record.request_id,
                "prompt_uid": record.prompt_uid,
                "response_id": record.response_id,
                "hazard": hazard,
                "hazard_source": judgment.source,
                "legitimization_applies": judgment.legitimization_applies,
                "provisional_l": (
                    judgment.provisional_l.label if judgment.provisional_l is not None else None
                ),
                "provisional_e": (
                    judgment.provisional_e.label if judgment.provisional_e is not None else None
                ),
                "final_l": judgment.final_l,
                "final_e": judgment.final_e,
                "decided_by": judgment.decided_by,
                "result": judgment.result,
                "failure_reason": judgment.failure_reason,
                "overall_result": record.overall_result,
            }
        )
    return rows
