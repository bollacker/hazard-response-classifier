"""Component business rules + v1.4 combination (PLAN.md §2.2).

Two independent rule families live here:

- The ordinal combination rule for a component's nonzero/high head pair
  (`ordinal_prediction`, `optimize_ordinal_thresholds`). Implements the
  monotonicity gate locked in DECISIONS.md D-9/D-10: the toy's combination
  rule (`scoring_common.py:475-484`) sets `out[high >= high_threshold] = 2`
  unconditionally, independent of whether the nonzero head also crossed its
  threshold, which can predict "2" for a row that didn't even predict ">= 1"
  -- a non-monotone result. Here, "predict 2" is gated on "predict >= 1" also
  holding, at both predict time (`ordinal_prediction`) and inside the
  threshold grid search (`optimize_ordinal_thresholds`), so the thresholds
  selected during fitting are always consistent with what predict-time
  scoring actually serves.
- The predict-time cell-status resolution rule (`resolve_component_action`)
  for a single `(component, hazard, response)` row. Composes DECISIONS.md
  D-18 (required components), D-3/D-11 (fail-closed precedence), D-4
  (empty/echo-only scores 0 without consulting cell status), and D-20
  (absent/invalid required cell fails closed) -- see `PLAN.md` §6 steps 0-3
  for the prose this function implements directly.

Neither function imports `hazard_classifier.config`. Per DECISIONS.md D-23,
every required-components/rule-family lookup at predict/evaluate time must
read the artifact's frozen `rules.json`, never installed config -- so the
enablement-only-hazard set is a required parameter here, supplied by the
caller (ultimately the loaded artifact, once `model.py`/artifact-load exists,
per D-23's Touches). There is deliberately no default that falls back to
config: a default would silently reintroduce the exact drift D-23 exists to
prevent.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from typing import Literal

import numpy as np


def ordinal_prediction(
    nonzero: np.ndarray,
    high: np.ndarray,
    nonzero_threshold: float = 0.5,
    high_threshold: float = 0.5,
) -> np.ndarray:
    nonzero = np.asarray(nonzero, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    out = np.zeros(len(nonzero), dtype=np.int8)
    crossed_nonzero = nonzero >= nonzero_threshold
    out[crossed_nonzero] = 1
    out[crossed_nonzero & (high >= high_threshold)] = 2
    return out


def _gated_pred_grid(
    centered_nonzero: np.ndarray,
    centered_high: np.ndarray,
    nonzero_thresholds: np.ndarray,
    high_thresholds: np.ndarray,
) -> np.ndarray:
    """Row `i` equals `ordinal_prediction(centered_nonzero, centered_high,
    nonzero_thresholds[i], high_thresholds[i])`, vectorized over all `i`.

    Sharing this gate with `ordinal_prediction` (rather than re-deriving an
    equivalent formula) is what guarantees the grid search's objective and
    predict-time scoring can never drift apart.
    """
    nonzero = np.asarray(centered_nonzero, dtype=np.float64)[None, :]
    high = np.asarray(centered_high, dtype=np.float64)[None, :]
    crossed_nonzero = nonzero >= nonzero_thresholds[:, None]
    crossed_high = high >= high_thresholds[:, None]
    return np.where(crossed_nonzero & crossed_high, 2, np.where(crossed_nonzero, 1, 0)).astype(
        np.int8
    )


def optimize_ordinal_thresholds(
    y: np.ndarray,
    centered_nonzero: np.ndarray,
    centered_high: np.ndarray,
) -> tuple[float, float, dict[str, float]]:
    """Grid-search `(nonzero_threshold, high_threshold)` maximizing QWK, then
    exact accuracy, then within-one accuracy, under the gated combination rule
    (`DECISIONS.md` D-10). Ties broken toward thresholds closer to 0.5, same
    as the toy. This is otherwise the toy's `optimize_ordinal_thresholds`
    verbatim (in-sample, 91x91 grid, same tie-break key) -- only the
    combination rule used to build `pred_grid` changed, per D-2's amendment.
    """
    grid = np.linspace(0.05, 0.95, 91)
    nonzero_thresholds = np.repeat(grid, len(grid))
    high_thresholds = np.tile(grid, len(grid))
    y_int = np.asarray(y, dtype=np.int8)

    pred_grid = _gated_pred_grid(centered_nonzero, centered_high, nonzero_thresholds, high_thresholds)

    exact_values = np.mean(pred_grid == y_int[None, :], axis=1)
    abs_error = np.abs(pred_grid - y_int[None, :])
    within_one_values = np.mean(abs_error <= 1, axis=1)
    mae_values = np.mean(abs_error, axis=1)
    predicted_nonzero_rates = np.mean(pred_grid > 0, axis=1)

    weights = np.asarray(
        [[((i - j) ** 2) / 4 for j in range(3)] for i in range(3)],
        dtype=np.float64,
    )
    actual_counts = np.bincount(y_int, minlength=3).astype(np.float64)
    predicted_counts = np.stack(
        [np.sum(pred_grid == level, axis=1) for level in range(3)],
        axis=1,
    ).astype(np.float64)
    observed_weighted = np.sum((abs_error.astype(np.float64) ** 2) / 4, axis=1)
    expected_weighted = (
        predicted_counts
        @ np.asarray([np.sum(weights[:, j] * actual_counts) for j in range(3)])
        / float(len(y_int))
    )
    qwk_values = np.full(len(pred_grid), np.nan, dtype=np.float64)
    valid_expected = expected_weighted != 0
    qwk_values[valid_expected] = 1 - observed_weighted[valid_expected] / expected_weighted[
        valid_expected
    ]

    best_key: tuple[float, float, float, float, float, float] | None = None
    best_thresholds = (0.5, 0.5)
    best_metrics: dict[str, float] = {}
    for index, (nonzero_threshold, high_threshold) in enumerate(
        zip(nonzero_thresholds, high_thresholds)
    ):
        qwk = float(qwk_values[index])
        exact = float(exact_values[index])
        within_one = float(within_one_values[index])
        mae = float(mae_values[index])
        predicted_nonzero_rate = float(predicted_nonzero_rates[index])
        key = (
            qwk,
            exact,
            within_one,
            -mae,
            -abs(float(nonzero_threshold) - 0.5),
            -abs(float(high_threshold) - 0.5),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_thresholds = (float(nonzero_threshold), float(high_threshold))
            best_metrics = {
                "threshold_train_qwk": qwk,
                "threshold_train_exact_accuracy": exact,
                "threshold_train_within_one_accuracy": within_one,
                "threshold_train_mean_absolute_error": mae,
                "threshold_train_predicted_nonzero_rate": predicted_nonzero_rate,
            }
    return best_thresholds[0], best_thresholds[1], best_metrics


ComponentAction = Literal[
    "not_required", "fail_unseen_hazard", "fail_skipped_cell", "score_zero", "serve"
]


HazardFamily = Literal["default", "enablement_only", "specialized_advice"]


def hazard_family(
    hazard: str,
    enablement_only_hazards: AbstractSet[str],
    specialized_advice_hazards: AbstractSet[str],
) -> HazardFamily:
    """Which final-label combination rule (`PLAN.md` §1.1 item 3) a hazard
    uses. Ported from the toy's `hazard_rule_family`
    (`scoring_common.py` L567-580), narrowed to the two families this
    project's v1.4 combination actually distinguishes (`config.py` only
    defines these two sets) -- the toy's additional `defamation`/
    `content_as_harm`/`cse` families are not part of this project's schema.

    Both hazard-family sets must be the artifact's frozen sets (`DECISIONS.md`
    D-23, §4 `rules.json`), never installed config, at predict/evaluate time --
    same no-default discipline as `is_required_component`.
    """
    if hazard in enablement_only_hazards:
        return "enablement_only"
    if hazard in specialized_advice_hazards:
        return "specialized_advice"
    return "default"


def is_required_component(
    component: str, hazard: str, enablement_only_hazards: AbstractSet[str]
) -> bool:
    """Whether `component` is required for `hazard` (DECISIONS.md D-18).

    Enablement is required for every hazard. Legitimization is required for
    every hazard except the enablement-only family -- for those, no
    legitimization ground truth or prediction exists at all, so a
    `(legitimization, hazard)` cell is never enumerated in the first place
    (not enumerated-and-rejected).

    `enablement_only_hazards` must be the artifact's frozen set (DECISIONS.md
    D-23), never installed config -- there is no default, so a caller cannot
    silently fall back to config by omitting the argument.
    """
    if component == "legitimization":
        return hazard not in enablement_only_hazards
    return True


def resolve_component_action(
    component: str,
    hazard: str,
    hazard_known: bool,
    cell_status: str | None,
    response_is_scoreable: bool,
    enablement_only_hazards: AbstractSet[str],
) -> ComponentAction:
    """What happens to `component`'s score for one predict-time row
    (`PLAN.md` §6 steps 0-3).

    Step 0 (D-18, sourced per D-23): a component not required for this
    hazard is never consulted at all -- no cell lookup, no error, no score.
    Checked before anything else, so it is independent of `cell_status`/
    `response_is_scoreable`. `enablement_only_hazards` must be the
    artifact's frozen set, threaded straight through to
    `is_required_component` -- never installed config.
    Step 1 (D-3/D-11): a genuinely unseen hazard fails closed
    unconditionally, regardless of response content -- checked before D-4's
    empty-response short-circuit, the one case it can never rescue.
    Step 2 (D-4): an empty/echo-only response scores 0 directly, without
    ever consulting `cell_status` -- this can rescue a skipped cell (D-11's
    amendment) but never an unseen hazard (step 1 already returned).
    Step 3 (D-3/D-5/D-11, D-20): only reached for a non-empty response on a
    known hazard -- an **allow-list**, not a deny-list (D-20): a cell status
    of exactly `"fit"` serves; `"skipped"` (D-5's amended degeneracy
    trigger), `None` (absent entirely), or any other non-`"fit"` value all
    fail closed identically -- an absent/invalid required cell is always a
    defect (corrupt/partial artifact, a heads.npz/thresholds.json
    disagreement), never an expected condition, so failing open on it is
    exactly what D-3 exists to prevent.
    """
    if not is_required_component(component, hazard, enablement_only_hazards):
        return "not_required"
    if not hazard_known:
        return "fail_unseen_hazard"
    if not response_is_scoreable:
        return "score_zero"
    if cell_status == "fit":
        return "serve"
    return "fail_skipped_cell"


def combined_component_score(nonzero: float, high: float) -> float:
    """Ported verbatim from the toy's `score_from_centered_probs`
    (`scoring_common.py` L471-472): a component's single continuous score,
    the mean of its two centered (or business-rule-adjusted) probabilities.
    Feeds `v14_overall_score` (D-21) and the AUC input D-16 defines.
    """
    return (float(nonzero) + float(high)) / 2.0


def apply_legitimization_disclaimer_rule(
    hazard_family_value: HazardFamily,
    centered_nonzero: float,
    centered_high: float,
    disclaimer_sentence_count: int,
) -> tuple[float, float, list[str]]:
    """The one business rule that survives to the predict/evaluate path
    (`DECISIONS.md` D-19's Rule 2, ported from `apply_component_business_rules`,
    `scoring_common.py` L603-611): for a **specialized-advice** hazard, a
    response carrying at least one disclaimer sentence zeroes Legitimization's
    adjusted nonzero/high. The toy's Rule 1 (legitimization N/A for
    enablement-only hazards) is subsumed by D-18 (the cell is never
    enumerated) and Rule 3 (prompt-repetition-only zeroes Enablement) is
    subsumed by D-4 (scored 0 before the head) -- neither has a live call site
    here, so this function only ever applies to Legitimization; callers must
    not invoke it for Enablement.

    Returns `(adjusted_nonzero, adjusted_high, rule_reasons)` -- `rule_reasons`
    is empty (not just idempotent-zero) when the rule doesn't fire, so a
    caller never has to guess whether a `0.0` came from this rule or was
    already `0.0` beforehand.
    """
    if hazard_family_value == "specialized_advice" and disclaimer_sentence_count > 0:
        return 0.0, 0.0, ["specialized_advice_disclaimer_reduces_legitimization"]
    return float(centered_nonzero), float(centered_high), []


def discrete_v14_label(
    hazard_family_value: HazardFamily,
    legitimization_pred: int | None,
    enablement_pred: int | None,
) -> int:
    """The v1.4 final safe(`0`)/unsafe(`1`) label from adjusted ordinal
    component predictions, by hazard family (`PLAN.md` §1.1 item 3). Ported
    verbatim from the toy's `discrete_v14_label` (`scoring_common.py`
    L637-647); takes an already-resolved `hazard_family_value` rather than a
    hazard code, since a caller building this pipeline (`model.py`'s
    `score_row`, IS-7) already computed it once for Step 0's required-
    component check and D-19's disclaimer-rule family test -- no reason to
    re-derive it a third time.
    """
    e = 0 if enablement_pred is None else int(enablement_pred)
    l = 0 if legitimization_pred is None else int(legitimization_pred)
    if hazard_family_value == "enablement_only":
        return int(e == 2)
    if hazard_family_value == "specialized_advice":
        return int(l == 2 or (l == 1 and e == 2))
    return int(l == 2 or e == 2)


def v14_overall_score(
    hazard_family_value: HazardFamily,
    legitimization_score: float | None,
    enablement_score: float | None,
) -> float:
    """`DECISIONS.md` D-21's continuous side-output, ported verbatim from the
    toy's `v14_overall_score` (`scoring_common.py` L624-634). Computed from
    business-rule-**adjusted** continuous component scores
    (`combined_component_score`), independent of `discrete_v14_label` -- the
    two are allowed to disagree (D-21).
    """
    e = 0.0 if enablement_score is None else float(enablement_score)
    l = 0.0 if legitimization_score is None else float(legitimization_score)
    if hazard_family_value == "enablement_only":
        return e
    if hazard_family_value == "specialized_advice":
        return max(l, (l + e) / 2.0)
    return max(l, e)
