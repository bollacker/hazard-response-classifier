"""Deliverable 2 metric computation: per-component and final-label metrics.

Implements DECISIONS.md D-13 (holdout partitioning), D-15 (legitimization
excludes enablement-only-hazard rows), D-16 (AUC uses the retained high-head
probability only, not the nonzero head), and D-17 (safe=1/unsafe=0 positive-
class convention, labeled confusion shape, false-safe/false-unsafe rate
definition on the shared final-label-eligible denominator).

This module does not import `hazard_classifier.config`. Per DECISIONS.md D-23,
every required-components/rule-family lookup at predict/evaluate time must
read the artifact's frozen `rules.json`, never installed config -- so both the
enablement-only-hazard set (`legitimization_eligible_mask`) and the
specialized-advice-hazard set (`final_label_metrics`) are required parameters
here, supplied by the caller (ultimately the loaded artifact, once
`model.py`/artifact-load exists), mirroring `rules.py`'s
`is_required_component`/`resolve_component_action`. There is deliberately no
default that falls back to config for either.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet

import numpy as np
from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support, roc_auc_score


def partition_by_holdout(seed_prompt_ids, holdout_seed_prompt_ids):
    seed_prompt_ids = np.asarray(seed_prompt_ids)
    holdout = set(holdout_seed_prompt_ids)
    held_out_mask = np.array([sid in holdout for sid in seed_prompt_ids], dtype=bool)
    return held_out_mask, ~held_out_mask


def legitimization_eligible_mask(
    hazard, enablement_only_hazards: AbstractSet[str]
) -> np.ndarray:
    """Which rows are Legitimization-eligible (DECISIONS.md D-15, mechanized
    by D-18). `enablement_only_hazards` must be the artifact's frozen set
    (D-23), never installed config -- there is no default, so a caller cannot
    silently fall back to config by omitting the argument.
    """
    hazard = np.asarray(hazard)
    return np.array([h not in enablement_only_hazards for h in hazard], dtype=bool)


def _safe_auc(actual_binary, score) -> float | None:
    actual_binary = np.asarray(actual_binary, dtype=np.int8)
    if len(np.unique(actual_binary)) < 2:
        return None
    return float(roc_auc_score(actual_binary, score))


def _safe_qwk(y_true, y_pred) -> float | None:
    """DECISIONS.md D-33: `cohen_kappa_score` returns `NaN` (with an
    `UndefinedMetricWarning`) on the same degenerate-population condition
    `_safe_auc` already guards against -- reported as `None` here instead,
    so `metrics.json` never carries a bare `NaN` token.
    """
    value = cohen_kappa_score(
        np.asarray(y_true, dtype=np.int8), np.asarray(y_pred, dtype=np.int8), weights="quadratic"
    )
    return None if np.isnan(value) else float(value)


def component_metrics(y_true, y_pred, high_prob) -> dict:
    """Per-component metrics for whatever rows the caller passes in.

    `n` (DECISIONS.md D-17's DI-Q4 amendment) is simply `len(y_true)` -- this
    function carries no hazard-family knowledge, so it does not itself decide
    which rows are eligible. The D-17 semantics fall out of the caller's own
    pre-filtering: called with the full population for Enablement (required
    for every hazard, D-18), `n` equals the population's `n_rows`; called
    with a `legitimization_eligible_mask`-filtered subset for Legitimization
    (D-15, mechanized by D-18), `n` is `n_rows` minus the enablement-only-hazard
    row count -- without this function needing to know why.
    """
    y_true = np.asarray(y_true, dtype=np.int8)
    y_pred = np.asarray(y_pred, dtype=np.int8)
    high_prob = np.asarray(high_prob, dtype=np.float64)

    abs_error = np.abs(y_true.astype(np.int64) - y_pred.astype(np.int64))
    confusion_counts = {
        f"actual_{a}": {
            f"predicted_{p}": int(np.sum((y_true == a) & (y_pred == p))) for p in range(3)
        }
        for a in range(3)
    }
    return {
        "n": int(len(y_true)),
        "exact_accuracy": float(np.mean(y_true == y_pred)),
        "within_one_accuracy": float(np.mean(abs_error <= 1)),
        "binary_present_accuracy": float(np.mean((y_true > 0) == (y_pred > 0))),
        "auc": _safe_auc(y_true == 2, high_prob),
        "qwk": _safe_qwk(y_true, y_pred),
        "mae": float(np.mean(abs_error)),
        "confusion_counts": confusion_counts,
    }


def final_label_metrics(
    is_safe_true, predicted_safe, hazard, specialized_advice_hazards: AbstractSet[str]
) -> dict:
    """Final-label precision/recall/f1/rates (DECISIONS.md D-17), excluding
    specialized-advice hazards from the headline. `specialized_advice_hazards`
    must be the artifact's frozen set (D-23), never installed config -- there
    is no default, so a caller cannot silently fall back to config by
    omitting the argument.
    """
    is_safe_true = np.asarray(is_safe_true, dtype=bool)
    predicted_safe = np.asarray(predicted_safe, dtype=bool)
    hazard = np.asarray(hazard)

    headline_mask = np.array(
        [h not in specialized_advice_hazards for h in hazard], dtype=bool
    )
    actual = is_safe_true[headline_mask]
    predicted = predicted_safe[headline_mask]
    n = int(len(actual))

    predicted_safe_actual_safe = int(np.sum(predicted & actual))
    predicted_safe_actual_unsafe = int(np.sum(predicted & ~actual))
    predicted_unsafe_actual_safe = int(np.sum(~predicted & actual))
    predicted_unsafe_actual_unsafe = int(np.sum(~predicted & ~actual))
    confusion_counts = {
        "predicted_safe_actual_safe": predicted_safe_actual_safe,
        "predicted_safe_actual_unsafe": predicted_safe_actual_unsafe,
        "predicted_unsafe_actual_safe": predicted_unsafe_actual_safe,
        "predicted_unsafe_actual_unsafe": predicted_unsafe_actual_unsafe,
    }

    if n == 0:
        return {
            "n": 0,
            "precision": None,
            "recall": None,
            "f1": None,
            "false_safe_rate": None,
            "false_unsafe_rate": None,
            "confusion_counts": confusion_counts,
        }

    precision, recall, f1, _ = precision_recall_fscore_support(
        actual.astype(np.int8),
        predicted.astype(np.int8),
        labels=[1],
        average=None,
        zero_division=0,
    )

    return {
        "n": n,
        "precision": float(precision[0]),
        "recall": float(recall[0]),
        "f1": float(f1[0]),
        "false_safe_rate": predicted_safe_actual_unsafe / n,
        "false_unsafe_rate": predicted_unsafe_actual_safe / n,
        "confusion_counts": confusion_counts,
    }


_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "holdout_recorded",
    "excluded_row_count",
    "excluded_unseen_hazard_count",
    "excluded_skipped_cell_count",
)
_POPULATIONS: tuple[str, ...] = ("held_out", "in_sample_unrecorded")


def flatten_metrics_report(report: dict) -> list[dict]:
    """`metrics.csv`'s long format (`PLAN.md` §5, `DECISIONS.md` D-17): one
    row per `(population, section, metric, value)`, rather than a second,
    independently-designed wide schema. The three top-level fields (D-14's
    exclusion counts, D-13's `holdout_recorded`) use the sentinel population
    `"overall"`, section `"run"`, since they apply to the whole run rather
    than to `held_out`/`in_sample_unrecorded` specifically -- every row
    still carries a population so a consumer can never accidentally read a
    run-level count as belonging to one population, or an in-sample number
    as a generalization one. Nested values (`confusion_counts`, and
    `components.{enablement,legitimization}`) are flattened into a
    dot-separated `metric` path, e.g. `metric="confusion_counts.actual_0.
    predicted_1"` -- this is `PLAN.md` §5's explicit "best-effort" schema
    (correctable via an ordinary future fix-proposal, not a high-confidence
    spec), so the exact section/metric split is this function's own
    reasonable choice, not independently locked.
    """
    rows: list[dict] = []

    def flatten(population: str, section: str, obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                flatten(population, section, value, f"{path}.{key}" if path else key)
        else:
            rows.append({"population": population, "section": section, "metric": path, "value": obj})

    for field in _TOP_LEVEL_FIELDS:
        flatten("overall", "run", report[field], field)

    for population in _POPULATIONS:
        if population not in report:
            continue
        population_report = report[population]
        flatten(population, "population", population_report["n_rows"], "n_rows")
        for component in ("enablement", "legitimization"):
            flatten(population, f"components.{component}", population_report["components"][component])
        flatten(population, "final_label", population_report["final_label"])

    return rows


def _fmt(value: object) -> str:
    """`None`-safe formatting for `render_summary` -- several fields here
    (`auc`/`qwk` on a degenerate population, D-16/D-33; every
    `final_label_metrics` field when its eligible population is empty) are
    genuinely `None`, not just always-a-float.
    """
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_summary(report: dict) -> str:
    """`PLAN.md` §5's free-form human-readable `summary.txt`, derived from
    the same report object `metrics.json`/`metrics.csv` are (not
    independently specified).
    """
    lines: list[str] = [
        f"holdout_recorded: {report['holdout_recorded']}",
        f"excluded_row_count: {report['excluded_row_count']} "
        f"(unseen_hazard={report['excluded_unseen_hazard_count']}, "
        f"skipped_cell={report['excluded_skipped_cell_count']})",
    ]
    if not report["holdout_recorded"]:
        lines.append(
            "WARNING: this artifact has no recorded held-out split (DECISIONS.md D-13) "
            "-- no number below is a verified generalization number."
        )

    for population in _POPULATIONS:
        if population not in report:
            continue
        population_report = report[population]
        lines.append("")
        lines.append(f"=== {population} (n_rows={population_report['n_rows']}) ===")
        for component in ("enablement", "legitimization"):
            cm = population_report["components"][component]
            lines.append(
                f"{component}: n={_fmt(cm['n'])} exact={_fmt(cm['exact_accuracy'])} "
                f"within_one={_fmt(cm['within_one_accuracy'])} "
                f"binary_present={_fmt(cm['binary_present_accuracy'])} "
                f"auc={_fmt(cm['auc'])} qwk={_fmt(cm['qwk'])} mae={_fmt(cm['mae'])}"
            )
        fl = population_report["final_label"]
        lines.append(
            f"final_label: n={_fmt(fl['n'])} precision={_fmt(fl['precision'])} "
            f"recall={_fmt(fl['recall'])} f1={_fmt(fl['f1'])} "
            f"false_safe_rate={_fmt(fl['false_safe_rate'])} "
            f"false_unsafe_rate={_fmt(fl['false_unsafe_rate'])}"
        )

    return "\n".join(lines) + "\n"
