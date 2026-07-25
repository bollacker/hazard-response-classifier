"""Input schema: CSV loading + validation (`PLAN.md` §2.1, §2.2).

Validates columns, hazard codes, and label ranges up front with clear errors,
replacing the toy's silent `.get("", "")` access (`scoring_common.py`'s
`load_key_rows` and friends).

**Hazard normalization (DECISIONS.md D-27, locked):** the `hazard` column is
normalized once here, on every path, using the toy's `normalize_hazard`
exactly -- `hazard.strip().replace("-", "_")`, no lowercasing -- so
train-time cell-enumeration keys and predict/evaluate-time lookup keys always
agree (`scoring_common.py` L113-114).

**Column requirements are mode-scoped (DECISIONS.md D-24, D-26):**
- `train` / `evaluate`: all eight §2.1 columns are required, including the
  three ground-truth columns.
- `predict`: only `seed_prompt_id, prompt_uid, prompt_text, response_text,
  hazard` are required. The three ground-truth columns are optional and
  **entirely ignored** when present (D-24) -- not even range-checked, so a
  labeled CSV can be reused for prediction unchanged.

**Validation performed here is deliberately family-agnostic (DECISIONS.md
D-26's 2026-07-25 Finding-A amendment).** It never decides whether a hazard is
enablement-only, since that judgment requires the artifact's frozen
`rules.json` (D-23), which does not exist at this layer (no artifact has been
loaded yet). Concretely, this module:
- requires the mode's column set to be present;
- normalizes `hazard`, and (train mode only, when `known_hazards` is given)
  rejects a row whose normalized hazard is not in that set -- "there is no
  artifact to defer to and a malformed code there is a genuine input error"
  (D-27);
- range-checks any **non-blank** `enablement_value`/`legitimization_value`
  against `{0, 1, 2}`.

It never rejects a row for a **blank** ground-truth value -- not even a blank
`enablement_value` on a hazard this module cannot even confirm exists --
because whether a blank is tolerated (D-15/D-18's enablement-only
legitimization carve-out) or a data defect depends on the hazard's family,
which only a per-row check against the loaded artifact can resolve (D-26's
Finding-A amendment; not built here -- that is `hrc-evaluate`'s job, `IS-8`).

**Open question, not resolved here:** `is_safe_ground_truth`'s literal string
encoding is not pinned by any locked decision -- `PLAN.md`'s schema table
names it only as "ground-truth final safe/unsafe," and the toy
(`scoring_common.py` L163) carries it through as an opaque string without
ever parsing it. This module therefore validates only that the column is
present, not the format of its contents. See `VERIFICATION.md` IS-1.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Literal

import pandas as pd

Mode = Literal["train", "evaluate", "predict"]

_CORE_COLUMNS: tuple[str, ...] = (
    "seed_prompt_id",
    "prompt_uid",
    "prompt_text",
    "response_text",
    "hazard",
)
GROUND_TRUTH_COLUMNS: tuple[str, ...] = (
    "enablement_value",
    "legitimization_value",
    "is_safe_ground_truth",
)
_ORDINAL_LABEL_COLUMNS: tuple[str, ...] = ("enablement_value", "legitimization_value")
_ORDINAL_LABEL_VALUES = frozenset({"0", "1", "2"})

REQUIRED_COLUMNS: dict[Mode, tuple[str, ...]] = {
    "train": _CORE_COLUMNS + GROUND_TRUTH_COLUMNS,
    "evaluate": _CORE_COLUMNS + GROUND_TRUTH_COLUMNS,
    "predict": _CORE_COLUMNS,
}


class SchemaError(ValueError):
    """A structural violation of the §2.1 input schema."""


def normalize_hazard(value: object) -> str:
    """DECISIONS.md D-27: `.strip().replace("-", "_")`, no lowercasing --
    ported verbatim from the toy's `normalize_hazard`
    (`scoring_common.py:113-114`).
    """
    return str(value).strip().replace("-", "_")


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


_IS_SAFE_GROUND_TRUTH_VALUES = {"safe": True, "unsafe": False}


def parse_is_safe_ground_truth(value: object) -> bool:
    """`DECISIONS.md` D-30: `is_safe_ground_truth`'s only two valid non-blank
    values are the exact, case-sensitive strings `"safe"`/`"unsafe"`. Raises
    `SchemaError` for anything else (blank included -- a blank reaching this
    function is already a bug in the caller, since D-26's per-row validation
    must reject a blank on a to-be-measured row before parsing is ever
    attempted).
    """
    text = str(value)
    try:
        return _IS_SAFE_GROUND_TRUTH_VALUES[text]
    except KeyError:
        raise SchemaError(
            f"is_safe_ground_truth must be 'safe' or 'unsafe' (D-30); got {text!r}"
        ) from None


def load_csv(
    path,
    mode: Mode,
    known_hazards: Collection[str] | None = None,
) -> pd.DataFrame:
    """Load and validate a CSV against the §2.1 schema for `mode`.

    Raises `SchemaError` for: a missing required column; a non-blank
    `enablement_value`/`legitimization_value` outside `{0, 1, 2}`; (train
    mode only, when `known_hazards` is given) a normalized `hazard` not in
    `known_hazards`. Never raises for a blank ground-truth value. In
    `predict` mode, ground-truth columns are not inspected at all, even if
    present with out-of-range values (D-24).

    `known_hazards` is accepted only for `mode="train"` (D-27: the
    predict/evaluate paths must never reject on hazard membership at this
    layer, since that would abort the run against D-22/D-14) -- passing it
    for another mode raises immediately, rather than silently ignoring a
    caller's mistaken expectation that it would be enforced.
    """
    if known_hazards is not None and mode != "train":
        raise ValueError(
            f"known_hazards is only meaningful for mode='train' (D-27); got mode={mode!r}"
        )

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    required = REQUIRED_COLUMNS[mode]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise SchemaError(
            f"{mode} input is missing required column(s): {', '.join(missing)}"
        )

    df = df.copy()
    df["hazard"] = df["hazard"].map(normalize_hazard)

    if known_hazards is not None:
        known = set(known_hazards)
        unknown = sorted({hazard for hazard in df["hazard"] if hazard not in known})
        if unknown:
            raise SchemaError(
                f"{mode} input has unrecognized hazard code(s): {', '.join(unknown)}"
            )

    if mode != "predict":
        for column in _ORDINAL_LABEL_COLUMNS:
            bad_values = sorted(
                {
                    value
                    for value in df[column]
                    if not _is_blank(value) and value.strip() not in _ORDINAL_LABEL_VALUES
                }
            )
            if bad_values:
                raise SchemaError(
                    f"{mode} input has {column} value(s) outside {{0,1,2}}: "
                    f"{', '.join(bad_values)}"
                )

    return df
