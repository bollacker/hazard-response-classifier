"""Single source of truth for Release 1.1's interim dataset.

Context (`docs/planning/DECISIONS.md` D-63 through D-66;
`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` slice 0). The Standards team's
dataset is not arriving, so Release 1.1 builds on the Jailbreak v1.0 human
ground truth already in this repository, split by `scripts/build_interim_split.py`
into `data/interim_split_v1.json`.

That manifest records the eval **group ids** and a prose description of the
group key, but no row-level train/eval assignment -- a consumer has to
recompute the group id for every row to use it. Before this module existed,
the only implementation of that recipe was a private function inside
`scripts/build_interim_split.py`, a script, not an importable package: a
consumer that reimplemented the normalization even slightly differently
would silently get a different split, with no error. This module is now that
single implementation; the builder imports `prompt_group_id` from here rather
than defining its own.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

from hazard_classifier.config import ENABLEMENT_ONLY_HAZARDS
from hazard_classifier.metrics import legitimization_eligible_mask
from hazard_classifier.schema import normalize_hazard

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
INTERIM_SOURCE = (
    _REPO_ROOT
    / "data"
    / "jb_1.0_1003_ground_truth_items_for_riki_eval__with_seed_prompt_id.csv"
)
INTERIM_SPLIT = _REPO_ROOT / "data" / "interim_split_v1.json"


class InterimDataError(ValueError):
    """`INTERIM_SOURCE` no longer matches the source `INTERIM_SPLIT` was built
    against, so its split can no longer be trusted to describe this data."""


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_prompt(text: str) -> str:
    """Group key basis. Whitespace-normalized only -- an identity key, not a
    similarity measure, so it must not collapse distinct prompts.
    """
    return " ".join(str(text).split())


def prompt_group_id(prompt_text: str) -> str:
    """`DECISIONS.md` D-64's split key: sha256(whitespace-normalized prompt
    text)[:16]. Group id, not text hash -- used to hold out entire prompt
    groups, never individual rows.
    """
    return hashlib.sha256(_normalize_prompt(prompt_text).encode("utf-8")).hexdigest()[:16]


def load_interim(*, split: str | None = None) -> pd.DataFrame:
    """The interim source CSV, augmented with a normalized `hazard` (D-27),
    `prompt_group_id`, and `split` in {"train", "eval"} assigned from the
    frozen manifest at `INTERIM_SPLIT`.

    Raises `InterimDataError` if `INTERIM_SOURCE`'s current contents no
    longer match the source the frozen split was built against -- a drifted
    source would otherwise silently score against an unknown split with no
    error.
    """
    manifest = json.loads(INTERIM_SPLIT.read_text())

    actual_sha256 = _sha256_file(INTERIM_SOURCE)
    if actual_sha256 != manifest["source_sha256"]:
        raise InterimDataError(
            f"{INTERIM_SOURCE.name} does not match the source "
            f"{INTERIM_SPLIT.name} was built against "
            f"(expected sha256 {manifest['source_sha256']}, got {actual_sha256}). "
            "Rebuild the split with scripts/build_interim_split.py before using this data."
        )

    frame = pd.read_csv(INTERIM_SOURCE)
    frame["hazard"] = frame["hazard"].map(normalize_hazard)
    frame["prompt_group_id"] = frame["prompt_text"].map(prompt_group_id)

    eval_groups = set(manifest["eval_group_ids"])
    frame["split"] = np.where(frame["prompt_group_id"].isin(eval_groups), "eval", "train")

    if split is not None:
        frame = frame[frame["split"] == split].reset_index(drop=True)

    return frame


def legitimization_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows eligible for Legitimization fitting/evaluation -- excludes the
    enablement-only hazards `prv`/`sxc_prn` (`DECISIONS.md` D-15, mechanized
    by `metrics.legitimization_eligible_mask`), which L is `N/A` for under
    `SCIENCE.md` phase A.
    """
    mask = legitimization_eligible_mask(frame["hazard"], ENABLEMENT_ONLY_HAZARDS)
    return frame[mask].reset_index(drop=True)
