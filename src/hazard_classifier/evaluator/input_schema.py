"""The Release 1.1 input schema and record construction
(`docs/planning/PR7_EXECUTION_PLAN.md` §4, `docs/ARCHITECTURE.md` §4).

**A new module, never an extension of `schema.py`** (PR7 plan §1's standing
constraint, D-48): `schema.py`'s `REQUIRED_COLUMNS`/`Mode` are the baseline's
own input contract -- `seed_prompt_id, prompt_uid, prompt_text, response_text,
hazard` -- and carry neither `request_id` nor `response_id`, which every 1.1
output record needs (`ARCHITECTURE.md` §4's identity fields). Extending the
baseline schema to also carry the 1.1 columns would make one module serve two
input contracts that must never drift into each other; this module is the
1.1 contract's only home.

Two things this module deliberately does **not** do, both left to other,
later code:

- **Hazard validity.** Whether a supplied hazard is missing, unrecognized, or
  outside the run's configured scope is `run.validate_supplied_hazard`'s job,
  checked against a `RunContext.hazard_scope` that does not exist until
  `run.open_run` has run. Conflating the two would raise a run rejection from
  a CSV reader with no scope to name -- this module only normalizes the
  column's *form* (`schema.normalize_hazard`), the same structural step the
  baseline schema applies to its own `hazard` column, never its *membership*.
- **Scoring, or anything the pipeline decides.** `build_record` constructs the
  pre-integration placeholder every existing pipeline test already expects
  (`overall_result="failure"`, `overall_failure_reason="not yet evaluated"`)
  and nothing more.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd

from ..schema import normalize_hazard
from .record import EvaluationRecord, Flags, TextViews
from .run import RunContext

__all__ = [
    "REQUIRED_COLUMNS",
    "InputSchemaError",
    "InputRow",
    "load_csv",
    "parse_rows",
    "build_record",
]

# `PR7_EXECUTION_PLAN.md` §4's work list, verbatim, with the hazard column
# named to match the record (`EvaluationRecord.supplied_hazard`) rather than
# the baseline's `hazard` -- "the 1.1 schema should match the record, since
# that is what every downstream document calls it."
REQUIRED_COLUMNS: tuple[str, ...] = (
    "request_id",
    "prompt_uid",
    "response_id",
    "prompt_text",
    "response_text",
    "supplied_hazard",
)

# Identity columns must never be blank ("Identity is the input's contract" --
# PR7_EXECUTION_PLAN.md §4). `prompt_text`/`response_text` are deliberately
# excluded: a blank `response_text` is legitimate domain input (stage 1's
# whole job is detecting exactly that case), and nothing in `SCIENCE.md`
# forbids a blank prompt either. `supplied_hazard` is excluded for the
# reason stated in the module docstring -- its blankness is a run rejection,
# not a structural defect, and is checked by `run.validate_supplied_hazard`.
_IDENTITY_COLUMNS: tuple[str, ...] = ("request_id", "prompt_uid", "response_id")


class InputSchemaError(ValueError):
    """A structural violation of the 1.1 input schema: a missing column, a
    blank identity value, or a duplicate `response_id`. Never raised for a
    hazard-validity problem -- see the module docstring.
    """


@dataclasses.dataclass(frozen=True)
class InputRow:
    """One structurally validated 1.1 input row, ready for `build_record`
    once a `RunContext` exists. `supplied_hazard` is already normalized
    (`schema.normalize_hazard`) -- the same canonical form
    `run.validate_supplied_hazard` computes internally and the form every
    hazard in `RunContext.hazard_scope` is assumed to already be in -- so
    `EvaluationRecord.supplied_hazard` and `RunContext.hazard_scope` are
    always compared in the same space.
    """

    request_id: str
    prompt_uid: str
    response_id: str
    prompt_text: str
    response_text: str
    supplied_hazard: str


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


def parse_rows(df: pd.DataFrame) -> tuple[InputRow, ...]:
    """Validate an already-loaded frame against the 1.1 schema and return
    one `InputRow` per data row, in input order (determinism, §6 of the
    plan: "write rows in input order").

    Raises `InputSchemaError` naming the offending column or row for: a
    missing required column; a blank identity value (`request_id`,
    `prompt_uid`, or `response_id`); a duplicate `response_id`.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise InputSchemaError(
            f"1.1 input is missing required column(s): {', '.join(missing)}"
        )

    rows: list[InputRow] = []
    seen_response_ids: dict[str, int] = {}
    duplicates: list[str] = []

    for i, record in enumerate(df.to_dict(orient="records")):
        for column in _IDENTITY_COLUMNS:
            if _is_blank(record[column]):
                raise InputSchemaError(
                    f"1.1 input row {i} has a blank required value for column "
                    f"{column!r} -- identity is the input's contract and is "
                    "never synthesized"
                )

        response_id = str(record["response_id"]).strip()
        if response_id in seen_response_ids:
            duplicates.append(response_id)
        else:
            seen_response_ids[response_id] = i

        rows.append(
            InputRow(
                request_id=str(record["request_id"]).strip(),
                prompt_uid=str(record["prompt_uid"]).strip(),
                response_id=response_id,
                prompt_text=str(record["prompt_text"]),
                response_text=str(record["response_text"]),
                supplied_hazard=normalize_hazard(record["supplied_hazard"]),
            )
        )

    if duplicates:
        raise InputSchemaError(
            f"1.1 input has duplicate response_id(s): {', '.join(sorted(set(duplicates)))}"
        )

    return tuple(rows)


def load_csv(path: str | Path) -> tuple[InputRow, ...]:
    """Load and validate a 1.1 input CSV. See `parse_rows` for the checks
    performed and the errors raised.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return parse_rows(df)


def build_record(row: InputRow, run_context: RunContext) -> EvaluationRecord:
    """Construct the pre-integration `EvaluationRecord` for one validated
    input row, once `run.open_run` has produced `run_context`
    (`PR7_EXECUTION_PLAN.md` §4). This is the *only* place a 1.1 record is
    built from raw input -- every stage after this one only ever calls
    `dataclasses.replace` on what this function returns.

    The contract, field by field:

    - `texts` starts every view (`original`, `decoded`, `working`) at the
      verbatim response text, with no history and no published `named`
      views yet -- stage 2 onward is what changes any of that.
    - `exhausted_at` is `None`: nothing has run yet, so nothing could have
      emptied the working text.
    - `observations`, `per_hazard` start empty; no stage has run and no
      hazard has been judged.
    - `detected_hazards` starts empty -- stage 3 (hazard detection) is what
      would populate it, and in 1.1 it is a placeholder that never does.
    - `evaluated_hazards` is set to `(row.supplied_hazard,)` and pinned by a
      test (`tests/unit/test_evaluator_input_schema.py`): this is correct in
      1.1 *because* stage 3 is a placeholder that always returns no
      additional hazards, not because merging `detected_hazards` in is
      unnecessary in general. **Nothing after this function ever updates
      `evaluated_hazards`** -- when stage 3 becomes a real implementation,
      the merge belongs there, not here: `ARCHITECTURE.md` §2 says
      `hazard_scope` "constrains which *additional* hazards detection may
      return", and a real stage-3 component can read
      `record.run.hazard_scope` to bound what it adds before the merge. This
      function must not grow that logic to compensate.
    - `overall_result`/`overall_failure_reason` start at the pre-integration
      placeholders every existing pipeline test already expects
      (`"failure"` / `"not yet evaluated"`) -- final integration (stage 10)
      is the only stage that ever writes a real result.
    """
    response = row.response_text
    return EvaluationRecord(
        request_id=row.request_id,
        prompt_uid=row.prompt_uid,
        response_id=row.response_id,
        prompt_text=row.prompt_text,
        response_text=response,
        supplied_hazard=row.supplied_hazard,
        run=run_context,
        texts=TextViews(original=response, decoded=response, working=response),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=(row.supplied_hazard,),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )
