"""`HazardResponseClassifier.fit` (`PLAN.md` §2.3, §3 step 4).

Ported from the toy's per-target-hazard weighted head fit
(`run_bge_hazard_weighted_heads.py`'s CV-fold loop, L200-306) with the
now-dropped grouped-CV apparatus (`DECISIONS.md` D-12) removed: this fits
each `(component, hazard)` cell **once**, on the whole (non-holdout) training
population, instead of per-fold.

**Layering contract, not yet pinned by any locked decision (an internal
interface choice, not an externally-visible behavior):** this module does
not itself preprocess text or compute sentence embeddings (`embed.py`, not
yet built) -- `fit` takes already-pooled per-component feature matrices and
an explicit "has effective sentences" boolean mask per component, rather
than raw text:

- `component_features["enablement" | "legitimization"]` -- an `(n_rows,
  n_dims)` array, row-aligned with `df`, already pooled per response
  (mean-pooled sentence embeddings, with the Enablement-only
  prompt-repetition sentence drop already applied upstream, §1.1 item 3).
- `component_effective["enablement" | "legitimization"]` -- an `(n_rows,)`
  boolean array, `True` unless that response has zero effective sentences
  for that component (D-4: a genuinely empty response, or -- Enablement
  only -- a response that is entirely prompt-repetition with no authored
  continuation). This is an explicit signal rather than an implicit
  "all-NaN feature row" convention, so a real bug elsewhere producing NaN
  features is never silently misread as an intentional D-4 exclusion.

Whichever future slice builds `embed.py`/pooling is responsible for
producing these two inputs correctly; this module only consumes them.
"""

from __future__ import annotations

import json
import math
import warnings
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from hazard_classifier.config import DEFAULT_EMBEDDING_MODEL_NAME, DEFAULT_SEED
from hazard_classifier.heads import BinaryHead, fit_binary_head
from hazard_classifier.metrics import (
    component_metrics,
    final_label_metrics,
    legitimization_eligible_mask,
    partition_by_holdout,
)
from hazard_classifier.rules import (
    ComponentAction,
    apply_legitimization_disclaimer_rule,
    combined_component_score,
    discrete_v14_label,
    hazard_family,
    is_required_component,
    optimize_ordinal_thresholds,
    ordinal_prediction,
    resolve_component_action,
    v14_overall_score,
)
from hazard_classifier.schema import parse_is_safe_ground_truth

Component = Literal["enablement", "legitimization"]
CellStatus = Literal["fit", "skipped"]


class WhollySkippedEnablementError(RuntimeError):
    """`DECISIONS.md` D-28: a wholly-skipped Enablement component leaves no
    deployable artifact (Enablement is required for every hazard, D-18) --
    `fit` hard-fails rather than returning a `HazardResponseClassifier` no
    caller could usefully serve.
    """

_COMPONENTS: tuple[Component, ...] = ("enablement", "legitimization")
_GROUND_TRUTH_COLUMN: dict[Component, str] = {
    "enablement": "enablement_value",
    "legitimization": "legitimization_value",
}
_OWN_HAZARD_MIN_ROWS = 5


@dataclass(frozen=True)
class Cell:
    """One fitted `(component, hazard)` cell (`PLAN.md` §4 `thresholds.json`
    row + `heads.npz` entry). `status` is `"skipped"` whenever **either**
    head is (D-5) -- both heads still hold a real (if degenerate-constant)
    value, since `PLAN.md` §3 step 4 / `DECISIONS.md` D-5's DR-6 note says
    the threshold search still runs on a skipped cell (wasted, not
    incorrect, work) rather than being special-cased away.
    """

    nonzero_head: BinaryHead
    high_head: BinaryHead
    nonzero_threshold: float
    high_threshold: float
    status: CellStatus
    threshold_metrics: dict[str, float]


@dataclass(frozen=True)
class PredictRow:
    """One raw input row for `HazardResponseClassifier.score` (`PLAN.md` §6,
    §11 item 5) -- unlike `score_row`, which takes already-pooled features,
    this is the production-facing shape: raw prompt/response text plus the
    opaque prompt/response/request datastore identity.
    """

    prompt_id: str
    response_id: str
    request_id: str
    hazard: str
    prompt_text: str
    response_text: str


@dataclass(frozen=True)
class RowResult:
    """One row's result from `score` (`DECISIONS.md` D-31): never raises on
    a hard-fail row. The prompt/response/request identity is returned
    unchanged. Exactly one of `scored`/`failure_reason` is set --
    `scored` for a successful row, `failure_reason` (`"unseen_hazard"` /
    `"skipped_or_absent_cell"`, D-25's vocabulary) for a hard-fail one.
    """

    prompt_id: str
    response_id: str
    request_id: str
    hazard: str
    scored: ScoredRow | None
    failure_reason: str | None


@dataclass
class HazardResponseClassifier:
    """The in-memory result of `fit` (`PLAN.md` §2.3). Serialization to the
    §4 artifact format (`heads.npz`/`thresholds.json`/`rules.json`/
    `manifest.json`) is a separate slice (IS-5), not built here.
    """

    cells: dict[tuple[Component, str], Cell]
    holdout_seed_prompt_ids: list[str]
    skipped_components: list[Component]
    trained_hazards: list[str]
    enablement_only_hazards: frozenset[str]
    specialized_advice_hazards: frozenset[str]
    embedding_model_name: str
    embedding_model_revision: str | None

    def score(self, rows: list[PredictRow], *, allow_download: bool = False) -> list[RowResult]:
        """Score raw `rows` end-to-end: `embed.build_component_features`
        (`DECISIONS.md` D-35 -- preprocess, `embed.py`'s
        `embed_sentences` against this artifact's own frozen
        `embedding_model_name`/`embedding_model_revision`, D-23, then pool)
        → `score_row` (`PLAN.md` §6, §11 item 5). The production Python API
        for embedding in a service -- "designed for repeated calls with the
        BGE model loaded once" (`PLAN.md` §6): `embed.py`'s `_load_model` is
        cached (`functools.lru_cache`), so calling `score` repeatedly on the
        same classifier reuses one loaded model rather than reloading per
        call.

        **Never raises on a hard-fail row (`DECISIONS.md` D-31):** returns
        exactly one `RowResult` per input row, in order. **Concurrency is
        unverified, not guaranteed** -- D-31 settles the error contract only;
        calling `score` from multiple threads simultaneously has not been
        tested and should not be assumed safe.

        Heavy imports (`embed.py`, and therefore `sentence-transformers`/
        `torch`) are deferred to inside this method, so importing
        `hazard_classifier.model` itself never requires them -- only
        actually calling `score` does.
        """
        from hazard_classifier import embed as embed_module
        from hazard_classifier.pipeline import EvaluationIdentity

        identities = [
            EvaluationIdentity(
                prompt_id=row.prompt_id,
                response_id=row.response_id,
                request_id=row.request_id,
            )
            for row in rows
        ]

        component_features, component_effective, disclaimer_sentence_count = (
            embed_module.build_component_features(
                [row.prompt_text for row in rows],
                [row.response_text for row in rows],
                [row.hazard for row in rows],
                identities=identities,
                model_name=self.embedding_model_name,
                revision=self.embedding_model_revision,
                allow_download=allow_download,
            )
        )

        results: list[RowResult] = []
        for i, row in enumerate(rows):
            try:
                scored = score_row(
                    self,
                    row.hazard,
                    enablement_features=component_features["enablement"][i],
                    legitimization_features=component_features["legitimization"][i],
                    enablement_effective=bool(component_effective["enablement"][i]),
                    legitimization_effective=bool(component_effective["legitimization"][i]),
                    disclaimer_sentence_count=int(disclaimer_sentence_count[i]),
                )
            except HardFailError as exc:
                results.append(
                    RowResult(
                        prompt_id=row.prompt_id,
                        response_id=row.response_id,
                        request_id=row.request_id,
                        hazard=row.hazard,
                        scored=None,
                        failure_reason=_FAILURE_REASON[exc.action],
                    )
                )
                continue

            results.append(
                RowResult(
                    prompt_id=row.prompt_id,
                    response_id=row.response_id,
                    request_id=row.request_id,
                    hazard=row.hazard,
                    scored=scored,
                    failure_reason=None,
                )
            )

        return results


def choose_holdout_seed_prompts(
    seed_prompt_ids: pd.Series,
    fraction: float,
    seed: int = DEFAULT_SEED,
) -> set[str]:
    """Reserve a `fraction` of the distinct `seed_prompt_id` values for
    `hrc-evaluate`'s held-out generalization measurement (`DECISIONS.md`
    D-1). Deterministic for a given `(seed_prompt_ids, fraction, seed)`
    (`PLAN.md` §8.1).

    `fraction <= 0` (the documented D-1 default) always returns an empty
    set, never a degenerate 1-item selection from a `ceil` rounding up.

    **Simplification from the toy's `choose_holdout_seed_prompts`
    (`scoring_common.py` L1077-1143), not a locked-decision deviation:** the
    toy additionally targets a minimum *response* count (its now-dropped
    grouped-CV apparatus, `DECISIONS.md` D-12) and accepts an explicit
    override list, neither of which the production CLI exposes (`PLAN.md`
    §3's `--holdout-seed-fraction` has no such companion flag). This
    selects uniformly at the seed-prompt level only.
    """
    unique_ids = sorted({str(value) for value in seed_prompt_ids})
    if not unique_ids or fraction <= 0:
        return set()
    target_count = max(1, math.ceil(len(unique_ids) * fraction))
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(np.asarray(unique_ids, dtype=object))
    return set(shuffled[:target_count])


def _own_hazard_or_pooled_mask(
    hazard_fit: np.ndarray, y_fit: np.ndarray, target_hazard: str
) -> np.ndarray:
    """`DECISIONS.md` D-2's `n_own >= 5` cliff, ported from the toy's
    `optimize_thresholds_for_hazard` (`run_bge_hazard_weighted_heads.py`
    L113-131): search over this hazard's own rows if there are at least
    `_OWN_HAZARD_MIN_ROWS` of them and they span at least two distinct
    ordinal labels, else fall back to the full (pooled, all-hazards) row
    population passed in.
    """
    own_mask = hazard_fit == target_hazard
    if int(np.sum(own_mask)) >= _OWN_HAZARD_MIN_ROWS and len(set(int(v) for v in y_fit[own_mask])) >= 2:
        return own_mask
    return np.ones(len(y_fit), dtype=bool)


def fit(
    df: pd.DataFrame,
    component_features: dict[Component, np.ndarray],
    component_effective: dict[Component, np.ndarray],
    enablement_only_hazards: AbstractSet[str],
    *,
    other_hazard_weight: float = 0.25,
    holdout_seed_fraction: float = 0.0,
    seed: int = DEFAULT_SEED,
    specialized_advice_hazards: AbstractSet[str] = frozenset(),
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL_NAME,
    embedding_model_revision: str | None = None,
) -> HazardResponseClassifier:
    """Fit every required `(component, hazard)` cell once on `df` (`PLAN.md`
    §3 step 4). `df` must already be schema-validated, train-mode, with
    `hazard` normalized (`schema.py`, D-27).

    Row-set construction per component (`DECISIONS.md` D-1/D-4/D-7/D-18),
    identical across every hazard within that component so `mean`/`scale`
    come out D-7-identical: `~holdout_mask & component_effective[component] &
    is_required_component(component, hazard, ...)` -- the last term is what
    makes Legitimization's row set exclude enablement-only-hazard rows
    entirely (D-18), since `is_required_component` returns `False` for them
    and no other component is ever narrowed by it (Enablement is required
    for every hazard).

    `embedding_model_name`/`embedding_model_revision` play no role in fitting
    either (the caller already supplied embeddings via `component_features`)
    -- they are recorded on the returned object purely so `score` (IS-11)
    loads the *same* BGE model/revision the caller actually embedded with,
    per `DECISIONS.md` D-23's "predict-time embeddings must match training,
    never overridden" principle, rather than a hardcoded default that could
    silently diverge from what this artifact was really fit against.

    `specialized_advice_hazards` plays no role in cell enumeration or fitting
    (D-18 only names the enablement-only set) -- it is accepted here purely
    so it rides along on the returned `HazardResponseClassifier` for `save`
    to freeze into `rules.json` (D-23) and for `score_row` (IS-7) to read
    back after `load`, without a caller needing to track it separately from
    the artifact itself.
    """
    hazard_values = df["hazard"].to_numpy(dtype=object)
    trained_hazards = sorted(set(str(value) for value in hazard_values))

    holdout_ids = choose_holdout_seed_prompts(df["seed_prompt_id"], holdout_seed_fraction, seed=seed)
    holdout_mask = df["seed_prompt_id"].astype(str).isin(holdout_ids).to_numpy()

    cells: dict[tuple[Component, str], Cell] = {}
    skipped_components: list[Component] = []

    for component in _COMPONENTS:
        required_hazards = [
            hazard
            for hazard in trained_hazards
            if is_required_component(component, hazard, enablement_only_hazards)
        ]
        if not required_hazards:
            continue

        row_required_mask = np.asarray(
            [is_required_component(component, str(h), enablement_only_hazards) for h in hazard_values],
            dtype=bool,
        )
        fit_row_mask = row_required_mask & component_effective[component] & ~holdout_mask

        x_fit = np.asarray(component_features[component])[fit_row_mask]
        hazard_fit = hazard_values[fit_row_mask]
        y_fit_raw = df[_GROUND_TRUTH_COLUMN[component]].to_numpy(dtype=object)[fit_row_mask]
        y_fit = np.array([int(value) for value in y_fit_raw], dtype=np.int8)

        component_cells_skipped: list[bool] = []
        for target_hazard in required_hazards:
            sample_weight = np.where(hazard_fit == target_hazard, 1.0, float(other_hazard_weight))

            nonzero_head = fit_binary_head(x_fit, (y_fit > 0).astype(np.int8), sample_weight, seed=seed)
            high_head = fit_binary_head(x_fit, (y_fit == 2).astype(np.int8), sample_weight, seed=seed)
            status: CellStatus = (
                "skipped" if nonzero_head.status == "skipped" or high_head.status == "skipped" else "fit"
            )
            component_cells_skipped.append(status == "skipped")

            nz_centered = nonzero_head.predict_proba_centered(x_fit)
            hi_centered = high_head.predict_proba_centered(x_fit)
            subset_mask = _own_hazard_or_pooled_mask(hazard_fit, y_fit, target_hazard)

            nonzero_threshold, high_threshold, threshold_metrics = optimize_ordinal_thresholds(
                y=y_fit[subset_mask],
                centered_nonzero=nz_centered[subset_mask],
                centered_high=hi_centered[subset_mask],
            )

            cells[(component, target_hazard)] = Cell(
                nonzero_head=nonzero_head,
                high_head=high_head,
                nonzero_threshold=nonzero_threshold,
                high_threshold=high_threshold,
                status=status,
                threshold_metrics=threshold_metrics,
            )

        if component_cells_skipped and all(component_cells_skipped):
            skipped_components.append(component)
            if component == "enablement":
                # DECISIONS.md D-28: Enablement is required for every hazard
                # (D-18), so a wholly-skipped Enablement leaves no workload
                # the artifact could serve at all. Hard-fail before even
                # attempting Legitimization's loop -- there is no
                # deployable classifier to return.
                raise WhollySkippedEnablementError(
                    "Enablement's nonzero/high label is single-class across every "
                    "training row surviving the D-1/D-4 exclusions (DECISIONS.md "
                    "D-5) -- every hazard's Enablement cell would be status="
                    "'skipped', and Enablement is required for every hazard "
                    "(D-18), so this training run produces no usable artifact."
                )
            if component == "legitimization":
                # D-28: Legitimization is not required for enablement-only
                # hazards (D-18), so a wholly-skipped Legitimization still
                # leaves a usable artifact for that narrower workload --
                # warn prominently, but write it (no raise).
                warnings.warn(
                    "Legitimization's nonzero/high label is single-class across "
                    "every training row surviving the D-1/D-4/D-18 exclusions "
                    "(DECISIONS.md D-5) -- every hazard's Legitimization cell is "
                    "status='skipped'. This artifact is only usable for "
                    "enablement-only-hazard workloads (D-18); loading it will "
                    "warn again at hrc-predict/hrc-evaluate time.",
                    UserWarning,
                    stacklevel=2,
                )

    return HazardResponseClassifier(
        cells=cells,
        holdout_seed_prompt_ids=sorted(str(value) for value in holdout_ids),
        skipped_components=skipped_components,
        trained_hazards=trained_hazards,
        enablement_only_hazards=frozenset(enablement_only_hazards),
        specialized_advice_hazards=frozenset(specialized_advice_hazards),
        embedding_model_name=embedding_model_name,
        embedding_model_revision=embedding_model_revision,
    )


# --- Artifact save/load (`PLAN.md` §4, `VERIFICATION.md` IS-5) ---------------

_HEAD_TYPES: tuple[str, ...] = ("nonzero", "high")
_MANIFEST_FILENAME = "manifest.json"
_THRESHOLDS_FILENAME = "thresholds.json"
_RULES_FILENAME = "rules.json"
_HEADS_FILENAME = "heads.npz"


def _head_array_key(component: str, hazard: str, head_type: str, field: str) -> str:
    """Deterministic `heads.npz` key, built (and later rebuilt) from
    `thresholds.json`'s cell list -- never parsed back out of the key string
    itself, so a hazard code containing an underscore can never be
    ambiguous.
    """
    return f"{component}__{hazard}__{head_type}__{field}"


def save(
    classifier: HazardResponseClassifier,
    output_dir: str | Path,
    *,
    code_version: str | None = None,
    hyperparameters: dict | None = None,
    training_timestamp: str | None = None,
    training_file_hash: str | None = None,
    training_row_count: int | None = None,
    training_hazard_counts: dict[str, int] | None = None,
) -> None:
    """Write `classifier` to the §4 artifact directory format.

    `classifier.specialized_advice_hazards` (set by `fit`, round-tripped by
    `load`) is frozen into `rules.json` alongside `enablement_only_hazards`
    -- D-23 requires `hrc-predict`/`hrc-evaluate` read *both* hazard-family
    sets from the artifact, never installed config.

    `classifier.embedding_model_name`/`embedding_model_revision` (set by
    `fit`, IS-11) are also written to `manifest.json` -- `score`'s "loaded
    once" BGE model must come from the artifact that was actually trained
    with it (D-23), never a hardcoded default a caller could forget to
    override.

    The installed upstream component contract is also written to
    `manifest.json`. This records the Assessment Standard, pipeline, component
    versions, and implementation statuses used by preprocessing without
    changing the classifier's scoring behavior.

    **`manifest.json`'s remaining §3 step 5 fields (`DECISIONS.md` D-35):**
    `code_version`/`hyperparameters`/`training_timestamp`/
    `training_file_hash`/`training_row_count`/`training_hazard_counts` are
    all optional and omitted from the manifest entirely when not supplied
    (`None`, the default) -- this function only receives an already-fitted
    `HazardResponseClassifier`, so it cannot compute any of these itself;
    `cli/train.py` is the only caller expected to supply them. Every
    existing caller that doesn't (every test in this project besides the
    CLI's own) still omits those optional fields. The required `pipeline`
    field described above is written for every newly saved artifact.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    head_arrays: dict[str, np.ndarray] = {}
    thresholds: dict[str, dict[str, dict]] = {component: {} for component in _COMPONENTS}
    for (component, hazard), cell in classifier.cells.items():
        for head_type, head in (("nonzero", cell.nonzero_head), ("high", cell.high_head)):
            for field, array in head.to_arrays().items():
                head_arrays[_head_array_key(component, hazard, head_type, field)] = array
        thresholds[component][hazard] = {
            "status": cell.status,
            "nonzero_threshold": cell.nonzero_threshold,
            "high_threshold": cell.high_threshold,
            "threshold_metrics": cell.threshold_metrics,
        }

    np.savez(output_dir / _HEADS_FILENAME, **head_arrays)

    with (output_dir / _THRESHOLDS_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(thresholds, handle, indent=2, sort_keys=True)

    hazard_family_map = {
        hazard: hazard_family(hazard, classifier.enablement_only_hazards, classifier.specialized_advice_hazards)
        for hazard in classifier.trained_hazards
    }
    trained = set(classifier.trained_hazards)
    rules = {
        "trained_hazards": classifier.trained_hazards,
        "hazard_family": hazard_family_map,
        "enablement_only_hazards": sorted(trained & set(classifier.enablement_only_hazards)),
        "specialized_advice_hazards": sorted(trained & set(classifier.specialized_advice_hazards)),
    }
    with (output_dir / _RULES_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(rules, handle, indent=2, sort_keys=True)

    from hazard_classifier.pipeline import pipeline_manifest

    manifest = {
        "holdout_seed_prompt_ids": classifier.holdout_seed_prompt_ids,
        "skipped_components": classifier.skipped_components,
        "embedding_model_name": classifier.embedding_model_name,
        "embedding_model_revision": classifier.embedding_model_revision,
        "pipeline": pipeline_manifest(),
    }
    optional_manifest_fields = {
        "code_version": code_version,
        "hyperparameters": hyperparameters,
        "training_timestamp": training_timestamp,
        "training_file_hash": training_file_hash,
        "training_row_count": training_row_count,
        "training_hazard_counts": training_hazard_counts,
    }
    manifest.update({key: value for key, value in optional_manifest_fields.items() if value is not None})
    with (output_dir / _MANIFEST_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)


def load(model_dir: str | Path) -> HazardResponseClassifier:
    """Load a `HazardResponseClassifier` from an artifact directory `save`
    wrote. `thresholds.json`'s cell list is the authoritative index of which
    `(component, hazard)` cells exist -- `heads.npz` keys are rebuilt from it
    via `_head_array_key`, never parsed.
    """
    model_dir = Path(model_dir)

    with (model_dir / _THRESHOLDS_FILENAME).open(encoding="utf-8") as handle:
        thresholds = json.load(handle)
    with (model_dir / _RULES_FILENAME).open(encoding="utf-8") as handle:
        rules = json.load(handle)
    with (model_dir / _MANIFEST_FILENAME).open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    head_arrays = dict(np.load(model_dir / _HEADS_FILENAME))

    cells: dict[tuple[Component, str], Cell] = {}
    for component, by_hazard in thresholds.items():
        for hazard, cell_json in by_hazard.items():
            heads: dict[str, BinaryHead] = {}
            for head_type in _HEAD_TYPES:
                fields = {
                    "mean",
                    "scale",
                    "coef",
                    "intercept",
                    "constant_probability",
                    "center_mean",
                    "status",
                }
                arrays = {
                    field: head_arrays[_head_array_key(component, hazard, head_type, field)]
                    for field in fields
                }
                heads[head_type] = BinaryHead.from_arrays(arrays)
            cells[(component, hazard)] = Cell(
                nonzero_head=heads["nonzero"],
                high_head=heads["high"],
                nonzero_threshold=float(cell_json["nonzero_threshold"]),
                high_threshold=float(cell_json["high_threshold"]),
                status=cell_json["status"],
                threshold_metrics=dict(cell_json["threshold_metrics"]),
            )

    return HazardResponseClassifier(
        cells=cells,
        holdout_seed_prompt_ids=list(manifest["holdout_seed_prompt_ids"]),
        skipped_components=list(manifest["skipped_components"]),
        trained_hazards=list(rules["trained_hazards"]),
        enablement_only_hazards=frozenset(rules["enablement_only_hazards"]),
        specialized_advice_hazards=frozenset(rules["specialized_advice_hazards"]),
        embedding_model_name=str(manifest["embedding_model_name"]),
        embedding_model_revision=manifest["embedding_model_revision"],
    )


# --- Predict/evaluate scoring pipeline (`PLAN.md` §5/§6, `VERIFICATION.md` IS-7) ---


class HardFailError(Exception):
    """A row `resolve_component_action` says must fail closed (D-3/D-11/D-20)
    for at least one required component -- a genuinely unseen hazard, or a
    non-empty response landing on a `"skipped"`/absent/invalid required
    cell. `score_row` raises this rather than deciding what happens next:
    `hrc-predict` (D-22, IS-10) routes the row to `failures.csv` and
    continues the batch; `hrc-evaluate` (D-14, IS-8) excludes the row from
    every metric and continues. Both share this exact predicate; only the
    consequence differs, and that consequence is each CLI's own job, not
    `score_row`'s.
    """

    def __init__(self, component: Component, action: ComponentAction):
        self.component = component
        self.action = action
        super().__init__(f"{component}: {action}")


@dataclass(frozen=True)
class ScoredRow:
    """One row's predict/evaluate output (`PLAN.md` §6's per-row output
    columns, minus the identifying columns `score_row` itself doesn't know
    about -- `prompt_uid`/`hazard` are the caller's to attach).

    `*_adjusted_high` (`None` for a `not_required` component, the D-4/D-16
    `0.0` sentinel for `score_zero`, else the business-rule-adjusted high-head
    probability) isn't part of `PLAN.md` §6's predict-output columns -- it
    exists so `hrc-evaluate` (IS-8) can feed `metrics.py`'s `component_metrics`
    the exact value D-16 defines "AUC" over, without recomputing it from a
    reloaded artifact a second time.
    """

    enablement_predicted: int | None
    legitimization_predicted: int | None
    v14_overall_unsafe_score: float
    predicted_label: Literal["safe", "unsafe"]
    rule_reasons: list[str]
    enablement_adjusted_high: float | None
    legitimization_adjusted_high: float | None


def score_row(
    classifier: HazardResponseClassifier,
    hazard: str,
    enablement_features: np.ndarray | None,
    legitimization_features: np.ndarray | None,
    enablement_effective: bool,
    legitimization_effective: bool,
    disclaimer_sentence_count: int,
) -> ScoredRow:
    """Score one response for `hazard` against a fitted/loaded `classifier`
    (`PLAN.md` §5/§6's shared pipeline): per required component, resolve
    the cell action (D-3/D-4/D-5/D-11/D-18/D-20, reusing
    `resolve_component_action` exactly as built, not re-derived) → serve via
    the frozen heads or apply D-4's zero sentinel → D-19's surviving
    disclaimer rule (Legitimization + specialized-advice only) → D-10's
    monotonicity-gated threshold → D-21's continuous v14 side-output +
    the discrete v1.4 label.

    Raises `HardFailError` for a `fail_unseen_hazard`/`fail_skipped_cell`
    row -- the caller decides the consequence (D-14/D-22), not this
    function. `enablement_features`/`legitimization_features` may be `None`
    when not needed (a `not_required` or `score_zero` component never reads
    them); `enablement_effective`/`legitimization_effective` mirror `fit`'s
    `component_effective` convention (D-4: `False` means zero effective
    sentences for that component).
    """
    hazard_known = hazard in classifier.trained_hazards
    family = hazard_family(hazard, classifier.enablement_only_hazards, classifier.specialized_advice_hazards)

    component_preds: dict[Component, int | None] = {}
    component_scores: dict[Component, float | None] = {}
    component_adjusted_high: dict[Component, float | None] = {}
    rule_reasons: list[str] = []

    for component, features, effective in (
        ("enablement", enablement_features, enablement_effective),
        ("legitimization", legitimization_features, legitimization_effective),
    ):
        cell = classifier.cells.get((component, hazard))
        cell_status = cell.status if cell is not None else None
        action = resolve_component_action(
            component, hazard, hazard_known, cell_status, effective, classifier.enablement_only_hazards
        )

        if action in ("fail_unseen_hazard", "fail_skipped_cell"):
            raise HardFailError(component, action)
        if action == "not_required":
            component_preds[component] = None
            component_scores[component] = None
            component_adjusted_high[component] = None
            continue
        if action == "score_zero":
            # D-4/D-16/D-21: the 0.0 sentinel. A zeroed component predicts 0
            # regardless of the cell's actual threshold (the grid search's
            # 0.05 floor, D-19's note) -- no need to consult `cell` at all.
            component_preds[component] = 0
            component_scores[component] = 0.0
            component_adjusted_high[component] = 0.0
            # D-32: this is the one short-circuit whose consequence isn't
            # already self-explanatory from the output columns (unlike D-18's
            # `not_required`, which leaves the predicted column `None`) -- a
            # plain 0 here is otherwise indistinguishable from a genuine
            # model prediction of 0.
            rule_reasons.append(f"{component}_zeroed_no_effective_sentences")
            continue

        # action == "serve"
        assert cell is not None  # guaranteed by resolve_component_action's own contract
        nz = float(cell.nonzero_head.predict_proba_centered(np.asarray([features]))[0])
        hi = float(cell.high_head.predict_proba_centered(np.asarray([features]))[0])
        if component == "legitimization":
            nz, hi, reasons = apply_legitimization_disclaimer_rule(family, nz, hi, disclaimer_sentence_count)
            rule_reasons.extend(reasons)

        pred = int(
            ordinal_prediction(
                np.asarray([nz]), np.asarray([hi]), cell.nonzero_threshold, cell.high_threshold
            )[0]
        )
        component_preds[component] = pred
        component_scores[component] = combined_component_score(nz, hi)
        component_adjusted_high[component] = hi

    label = discrete_v14_label(family, component_preds["legitimization"], component_preds["enablement"])
    v14_score = v14_overall_score(family, component_scores["legitimization"], component_scores["enablement"])

    return ScoredRow(
        enablement_predicted=component_preds["enablement"],
        legitimization_predicted=component_preds["legitimization"],
        v14_overall_unsafe_score=v14_score,
        predicted_label="unsafe" if label == 1 else "safe",
        rule_reasons=rule_reasons,
        enablement_adjusted_high=component_adjusted_high["enablement"],
        legitimization_adjusted_high=component_adjusted_high["legitimization"],
    )


# --- `hrc-evaluate` metric assembly (`PLAN.md` §5, `VERIFICATION.md` IS-8) ---


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


class BlankGroundTruthError(Exception):
    """`DECISIONS.md` D-26: among rows surviving D-14's hard-fail exclusion
    (`score_row`'s `HardFailError`), a known, non-enablement-only hazard row
    with a blank ground-truth column is a data defect. The user's original
    choice was **error over exclude** for this case -- `evaluate_rows` raises
    and aborts the whole run rather than silently dropping just that row,
    unlike `HardFailError`'s per-row exclusion.
    """


@dataclass(frozen=True)
class _EvalRow:
    seed_prompt_id: str
    hazard: str
    enablement_true: int
    enablement_pred: int
    enablement_adjusted_high: float
    legitimization_true: int | None
    legitimization_pred: int | None
    legitimization_adjusted_high: float | None
    is_safe_true: bool
    predicted_safe: bool


_EMPTY_COMPONENT_METRICS = {
    "n": 0,
    "exact_accuracy": None,
    "within_one_accuracy": None,
    "binary_present_accuracy": None,
    "auc": None,
    "qwk": None,
    "mae": None,
    "confusion_counts": None,
}


def evaluate_rows(
    df: pd.DataFrame,
    component_features: dict[Component, np.ndarray],
    component_effective: dict[Component, np.ndarray],
    disclaimer_sentence_count: np.ndarray,
    classifier: HazardResponseClassifier,
) -> dict:
    """Score every row of `df` (an evaluate-mode, schema-validated DataFrame
    with ground-truth columns present) against `classifier` and assemble the
    `PLAN.md` §5 `metrics.json`-shaped report.

    Reuses `score_row` (IS-7) as the single source of truth for what counts
    as an unscoreable row (`DECISIONS.md` D-3/D-4/D-5/D-11/D-18/D-20) --
    where `hrc-predict` would route a `HardFailError` row to `failures.csv`
    (D-22), this function **excludes** it from every metric and continues
    (D-14), recording which of the two `ComponentAction` reasons fired.

    Blank-ground-truth validation (D-26) only runs on rows that survived
    D-14's exclusion above -- an excluded row's labels are never examined, so
    a blank label on an unseen-hazard row can never turn into a whole-run
    abort (the exact ordering `DECISIONS.md` D-26's 2026-07-25 amendment
    requires).
    """
    hazards = df["hazard"].to_numpy(dtype=object)
    seed_ids = df["seed_prompt_id"].astype(str).to_numpy()
    enablement_values = df["enablement_value"].to_numpy(dtype=object)
    legitimization_values = df["legitimization_value"].to_numpy(dtype=object)
    is_safe_values = df["is_safe_ground_truth"].to_numpy(dtype=object)

    excluded_unseen_hazard_count = 0
    excluded_skipped_cell_count = 0
    rows: list[_EvalRow] = []

    for i in range(len(df)):
        hazard = str(hazards[i])
        try:
            result = score_row(
                classifier,
                hazard,
                enablement_features=component_features["enablement"][i],
                legitimization_features=component_features["legitimization"][i],
                enablement_effective=bool(component_effective["enablement"][i]),
                legitimization_effective=bool(component_effective["legitimization"][i]),
                disclaimer_sentence_count=int(disclaimer_sentence_count[i]),
            )
        except HardFailError as exc:
            if exc.action == "fail_unseen_hazard":
                excluded_unseen_hazard_count += 1
            else:
                excluded_skipped_cell_count += 1
            continue

        family = hazard_family(hazard, classifier.enablement_only_hazards, classifier.specialized_advice_hazards)
        enablement_value_raw = enablement_values[i]
        legitimization_value_raw = legitimization_values[i]
        is_safe_raw = is_safe_values[i]

        if _is_blank(enablement_value_raw) or _is_blank(is_safe_raw):
            raise BlankGroundTruthError(
                f"row {i} (hazard={hazard!r}): enablement_value/is_safe_ground_truth "
                "must not be blank on a row this run measures (DECISIONS.md D-26)"
            )
        if family != "enablement_only" and _is_blank(legitimization_value_raw):
            raise BlankGroundTruthError(
                f"row {i} (hazard={hazard!r}): legitimization_value must not be blank "
                "for a non-enablement-only hazard (DECISIONS.md D-26)"
            )

        rows.append(
            _EvalRow(
                seed_prompt_id=str(seed_ids[i]),
                hazard=hazard,
                enablement_true=int(enablement_value_raw),
                enablement_pred=result.enablement_predicted,
                enablement_adjusted_high=result.enablement_adjusted_high,
                legitimization_true=(
                    None if _is_blank(legitimization_value_raw) else int(legitimization_value_raw)
                ),
                legitimization_pred=result.legitimization_predicted,
                legitimization_adjusted_high=result.legitimization_adjusted_high,
                is_safe_true=parse_is_safe_ground_truth(is_safe_raw),
                predicted_safe=result.predicted_label == "safe",
            )
        )

    holdout_recorded = bool(classifier.holdout_seed_prompt_ids)
    if not holdout_recorded:
        warnings.warn(
            "This artifact has no recorded held-out split (DECISIONS.md D-13) -- "
            "every row falls into 'in_sample_unrecorded'; no reported number here "
            "is a verified generalization number.",
            UserWarning,
            stacklevel=2,
        )

    held_out_mask, in_sample_mask = (
        partition_by_holdout([row.seed_prompt_id for row in rows], classifier.holdout_seed_prompt_ids)
        if rows
        else (np.array([], dtype=bool), np.array([], dtype=bool))
    )

    report: dict = {
        "holdout_recorded": holdout_recorded,
        "excluded_row_count": excluded_unseen_hazard_count + excluded_skipped_cell_count,
        "excluded_unseen_hazard_count": excluded_unseen_hazard_count,
        "excluded_skipped_cell_count": excluded_skipped_cell_count,
    }
    for population_name, mask in (("held_out", held_out_mask), ("in_sample_unrecorded", in_sample_mask)):
        population_rows = [row for row, keep in zip(rows, mask) if keep]
        # D-13: "both populations are reported separately whenever both are
        # non-empty" -- an empty population has nothing to report and is
        # omitted rather than emitted with a hollow, all-null metrics object.
        if population_rows:
            report[population_name] = _population_report(population_rows, classifier)

    return report


def _population_report(rows: list[_EvalRow], classifier: HazardResponseClassifier) -> dict:
    hazards = [row.hazard for row in rows]

    enablement_metrics = component_metrics(
        y_true=[row.enablement_true for row in rows],
        y_pred=[row.enablement_pred for row in rows],
        high_prob=[row.enablement_adjusted_high for row in rows],
    )

    eligible_mask = legitimization_eligible_mask(hazards, classifier.enablement_only_hazards)
    legit_rows = [row for row, eligible in zip(rows, eligible_mask) if eligible]
    legitimization_metrics = (
        component_metrics(
            y_true=[row.legitimization_true for row in legit_rows],
            y_pred=[row.legitimization_pred for row in legit_rows],
            high_prob=[row.legitimization_adjusted_high for row in legit_rows],
        )
        if legit_rows
        else dict(_EMPTY_COMPONENT_METRICS)
    )

    final_label = final_label_metrics(
        is_safe_true=[row.is_safe_true for row in rows],
        predicted_safe=[row.predicted_safe for row in rows],
        hazard=hazards,
        specialized_advice_hazards=classifier.specialized_advice_hazards,
    )

    return {
        "n_rows": len(rows),
        "components": {"enablement": enablement_metrics, "legitimization": legitimization_metrics},
        "final_label": final_label,
    }


# --- `hrc-predict` batch scoring (`PLAN.md` §6, `VERIFICATION.md` IS-10) ----

PREDICTIONS_COLUMNS: tuple[str, ...] = (
    "prompt_uid",
    "hazard",
    "enablement_predicted",
    "legitimization_predicted",
    "v14_overall_unsafe_score",
    "predicted_label",
    "rule_reasons",
)
FAILURES_COLUMNS: tuple[str, ...] = ("prompt_uid", "hazard", "failure_reason")

_FAILURE_REASON: dict[ComponentAction, str] = {
    "fail_unseen_hazard": "unseen_hazard",
    "fail_skipped_cell": "skipped_or_absent_cell",
}


def predict_rows(
    df: pd.DataFrame,
    component_features: dict[Component, np.ndarray],
    component_effective: dict[Component, np.ndarray],
    disclaimer_sentence_count: np.ndarray,
    classifier: HazardResponseClassifier,
) -> tuple[list[dict], list[dict]]:
    """Score every row of `df` (a predict-mode DataFrame -- ground-truth
    columns optional/ignored, D-24) against `classifier` and split the
    result into `(predictions, failures)` row-dict lists, each shaped
    exactly like `PREDICTIONS_COLUMNS`/`FAILURES_COLUMNS` (`PLAN.md` §6,
    `DECISIONS.md` D-25).

    Every input row lands in **exactly one** of the two outputs (D-22): a
    `score_row` `HardFailError` routes to `failures`, tagged with the
    `failure_reason` D-25 names (`unseen_hazard` / `skipped_or_absent_cell`
    -- the same two-way distinction `evaluate_rows` counts, D-14); anything
    else lands in `predictions`. `seed_prompt_id` is never echoed into
    either output -- `prompt_uid` alone identifies a row in both
    (`DECISIONS.md` D-25's 2026-07-25 amendment, Finding C: `seed_prompt_id`
    is an inert predict-path passenger, D-24).

    Returns plain dict lists rather than a DataFrame directly so an empty
    batch still round-trips through `to_predictions_frame`/
    `to_failures_frame` with the correct header -- `pd.DataFrame([])` alone
    would lose the column names entirely.
    """
    prompt_uids = df["prompt_uid"].astype(str).to_numpy()
    hazards = df["hazard"].to_numpy(dtype=object)

    predictions: list[dict] = []
    failures: list[dict] = []

    for i in range(len(df)):
        hazard = str(hazards[i])
        try:
            result = score_row(
                classifier,
                hazard,
                enablement_features=component_features["enablement"][i],
                legitimization_features=component_features["legitimization"][i],
                enablement_effective=bool(component_effective["enablement"][i]),
                legitimization_effective=bool(component_effective["legitimization"][i]),
                disclaimer_sentence_count=int(disclaimer_sentence_count[i]),
            )
        except HardFailError as exc:
            failures.append(
                {
                    "prompt_uid": prompt_uids[i],
                    "hazard": hazard,
                    "failure_reason": _FAILURE_REASON[exc.action],
                }
            )
            continue

        predictions.append(
            {
                "prompt_uid": prompt_uids[i],
                "hazard": hazard,
                "enablement_predicted": result.enablement_predicted,
                "legitimization_predicted": result.legitimization_predicted,
                "v14_overall_unsafe_score": result.v14_overall_unsafe_score,
                "predicted_label": result.predicted_label,
                "rule_reasons": "|".join(result.rule_reasons),
            }
        )

    return predictions, failures


def to_predictions_frame(rows: list[dict]) -> pd.DataFrame:
    """`rows` (from `predict_rows`) as a DataFrame with `PREDICTIONS_COLUMNS`
    as its header -- explicit even for an empty list, since `pd.DataFrame([])`
    alone has no columns at all for `to_csv` to write a header from.
    """
    return pd.DataFrame(rows, columns=list(PREDICTIONS_COLUMNS))


def to_failures_frame(rows: list[dict]) -> pd.DataFrame:
    """`rows` (from `predict_rows`) as a DataFrame with `FAILURES_COLUMNS` as
    its header, always present (`DECISIONS.md` D-25: `failures.csv` is
    "always written, with a header even when empty").
    """
    return pd.DataFrame(rows, columns=list(FAILURES_COLUMNS))
