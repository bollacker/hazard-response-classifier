"""Fit Release 1.1's L and E models against the frozen interim split
(`docs/planning/PR5_EXECUTION_PLAN.md` §5).

One entry point, `fit_release_models`, and the provenance record it
produces. Everything scientific about *which rows* and *which text* is
settled and is applied here rather than left to a caller:

- **Working text, not raw `response_text`** ([D-72](../../../docs/planning/DECISIONS.md#d-72),
  `SCIENCE.md` §Legitimization/Enablement Training) -- `features.py` runs the
  real stages 1-8.
- **The fit half only** ([D-73](../../../docs/planning/DECISIONS.md#d-73)), so
  the dev slice stays held out and slice D's numbers describe the artifact
  that ships rather than a differently-fitted sibling.
- **Legitimization excludes `prv` and `sxc_prn`**
  (`PREREGISTRATION_LE_STRUCTURE.md` §1; `SCIENCE.md` phase A makes final L
  `N/A` there), via `interim_data.legitimization_rows`.

**The split vocabularies differ and the code's wins.**
`interim_data.load_interim(split="train")` is the half the pre-registration
calls the *fit* split; `"eval"` is what it calls the *dev* slice. Mixing them
silently fits on the held-out rows -- the one mistake D-73 exists to prevent
-- so `FitProvenance` records both names for the half actually used.

**Nothing here is a benchmark.** Every number these models produce is a
dev-class number on out-of-version labels ([D-63](../../../docs/planning/DECISIONS.md#d-63),
[D-66](../../../docs/planning/DECISIONS.md#d-66)), and both models are
reported **not evaluated** (`SCIENCE.md` §Legitimization Scoring,
§Enablement Scoring) whatever the figures show.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from typing import Mapping

import numpy as np
import pandas as pd

from ...config import DEFAULT_SEED
from ...interim_data import INTERIM_SOURCE, INTERIM_SPLIT, legitimization_rows, load_interim
from ..no_fixed_rules import assert_no_fixed_rule_import
from .features import PipelineFeatures, build_pipeline_features
from .multinomial import ESTIMATOR_PARAMS, TargetModel, fit_target_model

__all__ = ["FitProvenance", "LEModels", "fit_release_models", "fit_models_from_features"]

# The pre-registration's names for the two halves of `interim_split_v1.json`,
# against the loader's own vocabulary. Recorded rather than translated
# silently, because the two words for the same rows are exactly what a
# fit-on-the-held-out-slice mistake would hide behind.
_SPLIT_ROLE = {"train": "fit", "eval": "dev"}

_LABEL_COLUMN = {
    "legitimization": "legitimization_value",
    "enablement": "enablement_value",
}


@dataclasses.dataclass(frozen=True)
class FitProvenance:
    """What a run needs to reproduce this fit, and what slice B's
    `manifest.json` carries into the artifact
    (`ARCHITECTURE.md` §10; `PR5_EXECUTION_PLAN.md` §6). PR 5's exit
    criterion "runs reproduce results from locked model, rule, data, split,
    and metric versions" is met by this field set or it is not met.
    """

    source_path: str
    source_sha256: str
    split_path: str
    split_version: str
    split_half: str  # the loader's word: "train" | "eval"
    split_role: str  # the pre-registration's word: "fit" | "dev"
    text_view: str
    embedding_provider: str
    embedding_provider_version: str
    pooling: str
    seed: int
    estimator: Mapping[str, object]
    n_feature_rows: int
    exhausted_excluded: tuple[tuple[str, str, str], ...]  # (prompt_uid, hazard, stage)


@dataclasses.dataclass(frozen=True)
class LEModels:
    """Both fitted targets plus the provenance of the fit that produced them.

    Held together because they are fitted from one feature pass and shipped
    in one artifact -- but they are **separate models** (`S1`), and neither
    reads the other.
    """

    legitimization: TargetModel
    enablement: TargetModel
    provenance: FitProvenance


def _target_rows(
    frame: pd.DataFrame, features: PipelineFeatures, target: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(X, y, hazards)` for `target`: the target's eligible rows, restricted
    to those the evaluator would actually score (i.e. that survived stages
    1-7), in the frame's own order.
    """
    eligible = legitimization_rows(frame) if target == "legitimization" else frame
    index = features.row_index()
    scorable = set(index)

    positions = [index[str(uid)] for uid in eligible["prompt_uid"] if str(uid) in scorable]
    kept = eligible[eligible["prompt_uid"].astype(str).isin(scorable)]

    return (
        features.pooled[positions],
        kept[_LABEL_COLUMN[target]].to_numpy(dtype=np.int64),
        features.hazards[positions],
    )


def fit_models_from_features(
    frame: pd.DataFrame, features: PipelineFeatures, provenance: FitProvenance
) -> LEModels:
    """Fit both targets from an already-built feature pass.

    Separated from `fit_release_models` so the embedding pass is paid once
    and so a caller can fit against substituted features (a stub provider in
    a test) without re-deriving the eligibility rules.
    """
    models = {}
    for target in ("legitimization", "enablement"):
        X, y, hazards = _target_rows(frame, features, target)
        models[target] = fit_target_model(X, y, hazards, target=target)

    return LEModels(
        legitimization=models["legitimization"],
        enablement=models["enablement"],
        provenance=provenance,
    )


def fit_release_models(
    *,
    split: str = "train",
    provider=None,
    pooling=None,
    text_view: str = "working",
    allow_download: bool = False,
) -> LEModels:
    """Fit Release 1.1's L and E models on the frozen interim split.

    `split` defaults to `"train"` -- the pre-registration's *fit* half, and
    the only value D-73 permits for the artifact that ships. It is a
    parameter rather than a literal so a diagnostic refit is expressible and
    **visible in `FitProvenance`**, not so a caller can quietly consume the
    dev slice.

    `provider`/`pooling` default to the real BGE encoder and mean pooling
    (offline by default, D-6); this is one embedding pass over the split, run
    once, outside every fit loop.
    """
    if split not in _SPLIT_ROLE:
        raise ValueError(f"split must be one of {sorted(_SPLIT_ROLE)}, got {split!r}")

    frame = load_interim(split=split)
    features = build_pipeline_features(
        frame,
        provider=provider,
        pooling=pooling,
        text_view=text_view,
        allow_download=allow_download,
    )

    manifest = json.loads(INTERIM_SPLIT.read_text())
    provenance = FitProvenance(
        source_path=INTERIM_SOURCE.name,
        source_sha256=manifest["source_sha256"],
        split_path=INTERIM_SPLIT.name,
        split_version=manifest["split_version"],
        split_half=split,
        split_role=_SPLIT_ROLE[split],
        text_view=features.text_view,
        embedding_provider=features.provider_name,
        embedding_provider_version=features.provider_version,
        pooling=features.pooling_name,
        seed=DEFAULT_SEED,
        estimator=dict(ESTIMATOR_PARAMS),
        n_feature_rows=len(features.prompt_uids),
        exhausted_excluded=tuple(
            (row.prompt_uid, row.hazard, row.exhausted_at) for row in features.exhausted_rows
        ),
    )

    return fit_models_from_features(frame, features, provenance)


assert_no_fixed_rule_import(sys.modules[__name__])
