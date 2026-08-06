"""Derived views (`docs/ARCHITECTURE.md` §11).

The record is canonical; every output is a view derived from it, never the
record itself, and each view is a **named, versioned flattening contract**
rather than an implicit one -- one of the two counterarguments recorded
against the canonical-record proposal, answered here explicitly.

Three of §11's four views are built here:

- `result_view` -- the lossless `results.jsonl` record (§11 row 1).
- `prediction_rows` -- the per-`(response, hazard)` `predictions.csv`
  flattening (§11 row 2).
- `failure_rows` -- the `failures.csv` flattening (§11 row 4), added by PR 7
  slice C alongside the batch runner that produces the records it reads
  (`docs/planning/PR7_EXECUTION_PLAN.md` §6).

`metrics.json` is still not built: it needs the per-outcome metrics and
uncertainty estimates `SCIENCE.md` §Estimability requires, which are blocked
on PR 5's real three-class model *and* on the Standards team's approved
criteria -- and only the first of those clears with PR 5, so whether the view
ships at all is PR 6's call. Naming it as unbuilt is the point.

**Run rejections are not in `failures.csv`** (§11 row 4, §2). A rejection
aborts the run before any row is scored, so it produces no record for a view
to derive from and no output files at all. `failures.csv` carries only
*failed rows* -- a per-hazard failure decided by phase D, or a row the
pipeline could not complete. Keeping the two apart is the distinction PR 7's
plan calls the subtlest thing in the PR: rejections are about the run's
configuration and input contract, failures are about a row's content.

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

# Bumped 1 -> 2 on 2026-08-05 by `docs/planning/DECISIONS.md` D-76: each
# observation now renders `errors` (a list) where it rendered `error` (an
# object or null). That is a breaking change to this view's shape, and §11
# versions each view separately precisely so a consumer can tell.
# `PREDICTION_ROWS_VERSION` and `FAILURES_VERSION` are deliberately **not**
# bumped -- neither view's columns changed, and moving them in sympathy
# would make a future change to one look like a change to all three.
RESULT_VIEW_VERSION = "2"
PREDICTION_ROWS_VERSION = "1"
# §11: "every view is versioned separately". This one starts at 1
# independently of the other two rather than inheriting their number --
# `failures.csv` is a new contract as of PR 7, and a shared version would
# make a future change to one view look like a change to all three.
FAILURES_VERSION = "1"

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

FAILURE_COLUMNS = (
    "request_id",
    "prompt_uid",
    "response_id",
    "hazard",
    "stage",
    "failure_reason",
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
                # Every error the stage produced, in order (D-76). A list
                # rather than an optional object: a stage can fail once per
                # `(target, hazard)`, and the earlier single-error field
                # discarded all but the first.
                "errors": [
                    {"stage": error.stage, "message": error.message, "hazard": error.hazard}
                    for error in observation.errors
                ],
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


def _first_component_error(record: EvaluationRecord, hazard: str):
    """The earliest `ComponentError` in execution order scoped to `hazard`,
    or `None`. Earliest rather than latest: the first stage that could not
    do its job for this hazard is the cause, and anything after it is a
    consequence.

    **Searches every error on every observation** (`ARCHITECTURE.md` §4,
    `docs/planning/DECISIONS.md` D-76). Until that amendment an observation
    carried a single optional error, so a stage that failed more than once --
    stage 9 fails once per `(target, hazard)` -- kept only the first, and in a
    multi-hazard record every failing hazard's error but the first was lost.
    This function then found nothing for those hazards and `failure_rows`
    fell back to `stage="final_integration"`, its honest answer for "no
    component reported a problem for this hazard", which named the wrong
    stage. Two consecutive sweeps recorded that gap before it was closed.

    It was never a wrong *result*, only a lost cause: the authoritative text
    in the row is `HazardJudgment.failure_reason`, which phase D writes per
    component, and the row itself is emitted from
    `judgment.result == "failure"`, never from an observation.
    """
    for observation in record.observations:
        for error in observation.errors:
            if error.hazard == hazard:
                return error
    return None


def failure_rows(record: EvaluationRecord) -> list[dict[str, Any]]:
    """The `failures.csv` view (§11 row 4): one row per **failed** hazard,
    with `FAILURE_COLUMNS`'s exact keys and order. Carries no text, matching
    `prediction_rows`' sensitive-data bound.

    Rows are emitted in `record.evaluated_hazards` order -- never dict
    iteration order -- so the same record always renders the same bytes.

    A record with no failures returns `[]`. **A record that failed still
    appears in `results.jsonl` as well**: the record is canonical and
    lossless, this is the narrow view, and the two are deliberately not
    exclusive (`PR7_EXECUTION_PLAN.md` §6).

    Two shapes of failure are covered:

    - **Per-hazard**, the normal case: a `HazardJudgment` whose `result` is
      `"failure"`, which is phase D's verdict (`SCIENCE.md` §Per-hazard
      finalization). `stage` names the component whose `ComponentError`
      caused it when there is one, and `final_integration` otherwise --
      phase D itself decided, with no upstream component having reported a
      problem.
    - **Record-level**, when the record carries no per-hazard verdict at all
      but is nonetheless a failure. That is a record final integration never
      reached: in 1.1 the only route there is a component raising at run
      time, which `ARCHITECTURE.md` §5 says no component does
      (`ComponentError` is a record field, not an exception), so this is a
      backstop against a genuine bug rather than an expected path. `hazard`
      falls back to the supplied hazard, since that is the one hazard such a
      record is always known to have been evaluated against, and `stage` is
      `None` -- the partial record is lost when an exception unwinds
      `run_pipeline`, so the stage genuinely is not knowable here.
    """
    rows: list[dict[str, Any]] = []
    for hazard in record.evaluated_hazards:
        judgment = record.per_hazard.get(hazard)
        if judgment is None or judgment.result != "failure":
            continue
        error = _first_component_error(record, hazard)
        rows.append(
            {
                "request_id": record.request_id,
                "prompt_uid": record.prompt_uid,
                "response_id": record.response_id,
                "hazard": hazard,
                "stage": error.stage if error is not None else "final_integration",
                "failure_reason": judgment.failure_reason
                or (error.message if error is not None else None),
            }
        )

    if not rows and record.overall_result == "failure":
        rows.append(
            {
                "request_id": record.request_id,
                "prompt_uid": record.prompt_uid,
                "response_id": record.response_id,
                "hazard": record.supplied_hazard,
                "stage": None,
                "failure_reason": record.overall_failure_reason,
            }
        )

    return rows
