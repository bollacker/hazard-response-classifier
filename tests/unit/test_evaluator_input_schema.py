"""Tests for `hazard_classifier/evaluator/input_schema.py`: the 1.1 input
CSV schema and record construction (slice A,
`docs/planning/PR7_EXECUTION_PLAN.md` §4).
"""

from __future__ import annotations

import pandas as pd
import pytest

from hazard_classifier.evaluator.input_schema import (
    REQUIRED_COLUMNS,
    InputRow,
    InputSchemaError,
    build_record,
    load_csv,
    parse_rows,
)
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews
from hazard_classifier.evaluator.run import RunContext


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def _good_row(**overrides) -> dict:
    row = {
        "request_id": "req-1",
        "prompt_uid": "pu-1",
        "response_id": "resp-1",
        "prompt_text": "How do ladders work?",
        "response_text": "Keep three points of contact.",
        "supplied_hazard": "hte",
    }
    row.update(overrides)
    return row


def _run_context(hazard_scope: frozenset[str] = frozenset({"hte"})) -> RunContext:
    return RunContext(
        hazard_scope=hazard_scope,
        rule_version="v1",
        artifact_id="artifact-1",
        component_selections={},
    )


# --- parse_rows / load_csv: structural validation --------------------------


def test_parse_rows_rejects_a_missing_column_naming_it() -> None:
    df = pd.DataFrame([_good_row()]).drop(columns=["response_text"])

    with pytest.raises(InputSchemaError) as excinfo:
        parse_rows(df)

    assert "response_text" in str(excinfo.value)


def test_parse_rows_rejects_a_blank_request_id_naming_the_row() -> None:
    df = _frame([_good_row(request_id="  ")])

    with pytest.raises(InputSchemaError) as excinfo:
        parse_rows(df)

    message = str(excinfo.value)
    assert "request_id" in message
    assert "0" in message


def test_parse_rows_rejects_a_blank_prompt_uid() -> None:
    df = _frame([_good_row(prompt_uid="")])

    with pytest.raises(InputSchemaError) as excinfo:
        parse_rows(df)

    assert "prompt_uid" in str(excinfo.value)


def test_parse_rows_rejects_a_blank_response_id_rather_than_synthesizing_one() -> None:
    """PR7_EXECUTION_PLAN.md §4: "Reject a blank `response_id` rather than
    synthesizing one." A blank response_id is a structural defect, not a row
    the module quietly assigns an id to.
    """
    df = _frame([_good_row(response_id="   ")])

    with pytest.raises(InputSchemaError) as excinfo:
        parse_rows(df)

    assert "response_id" in str(excinfo.value)


def test_parse_rows_allows_a_blank_response_text() -> None:
    """An empty response is legitimate domain input -- stage 1's whole job
    is detecting exactly this case -- so it must not be rejected here.
    """
    df = _frame([_good_row(response_text="   ")])

    rows = parse_rows(df)

    assert rows[0].response_text == "   "


def test_parse_rows_rejects_a_duplicate_response_id() -> None:
    df = _frame(
        [
            _good_row(request_id="req-1", response_id="resp-1"),
            _good_row(request_id="req-2", response_id="resp-1"),
        ]
    )

    with pytest.raises(InputSchemaError) as excinfo:
        parse_rows(df)

    assert "resp-1" in str(excinfo.value)


def test_parse_rows_normalizes_supplied_hazard() -> None:
    """D-27, carried for 1.1: `.strip().replace("-", "_")`, no lowercasing --
    the same normalization the baseline's `hazard` column gets, and the same
    canonical form `run.validate_supplied_hazard` computes internally.
    """
    df = _frame([_good_row(supplied_hazard="spc-fin ")])

    rows = parse_rows(df)

    assert rows[0].supplied_hazard == "spc_fin"


def test_parse_rows_does_not_reject_a_blank_supplied_hazard() -> None:
    """Hazard validity -- including blankness -- is `validate_supplied_hazard`'s
    job against a scope that does not exist yet, not this module's
    (PR7_EXECUTION_PLAN.md §4: "Keep them apart").
    """
    df = _frame([_good_row(supplied_hazard="   ")])

    rows = parse_rows(df)

    assert rows[0].supplied_hazard == ""


def test_parse_rows_does_not_reject_an_unrecognized_hazard_code() -> None:
    """Same boundary as above, from the other direction: a garbage hazard
    code is not this module's concern either.
    """
    df = _frame([_good_row(supplied_hazard="not_a_real_hazard")])

    rows = parse_rows(df)

    assert rows[0].supplied_hazard == "not_a_real_hazard"


def test_parse_rows_preserves_input_order() -> None:
    df = _frame(
        [
            _good_row(request_id="req-1", response_id="resp-1"),
            _good_row(request_id="req-2", response_id="resp-2"),
            _good_row(request_id="req-3", response_id="resp-3"),
        ]
    )

    rows = parse_rows(df)

    assert [row.response_id for row in rows] == ["resp-1", "resp-2", "resp-3"]


def test_load_csv_reads_a_real_file(tmp_path) -> None:
    path = tmp_path / "input.csv"
    pd.DataFrame([_good_row()]).to_csv(path, index=False)

    rows = load_csv(path)

    assert rows == (
        InputRow(
            request_id="req-1",
            prompt_uid="pu-1",
            response_id="resp-1",
            prompt_text="How do ladders work?",
            response_text="Keep three points of contact.",
            supplied_hazard="hte",
        ),
    )


# --- build_record: the pre-integration record contract ---------------------


def test_build_record_matches_the_pr7_contract() -> None:
    row = InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="prompt",
        response_text="response",
        supplied_hazard="hte",
    )
    run_context = _run_context()

    record = build_record(row, run_context)

    assert isinstance(record, EvaluationRecord)
    assert record.request_id == "req-1"
    assert record.prompt_uid == "pu-1"
    assert record.response_id == "resp-1"
    assert record.prompt_text == "prompt"
    assert record.response_text == "response"
    assert record.supplied_hazard == "hte"
    assert record.run is run_context
    assert record.texts == TextViews(original="response", decoded="response", working="response")
    assert record.exhausted_at is None
    assert record.observations == ()
    assert record.detected_hazards == ()
    assert record.flags == Flags()
    assert record.per_hazard == {}
    assert record.overall_result == "failure"
    assert record.overall_failure_reason == "not yet evaluated"


def test_build_record_sets_evaluated_hazards_to_supplied_hazard_only() -> None:
    """`PR7_EXECUTION_PLAN.md` §4: pinned deliberately. This is correct in
    1.1 *because* stage 3 (hazard detection) is a placeholder that always
    returns no additional hazards -- `detected_hazards` is always empty --
    not because merging `detected_hazards` into `evaluated_hazards` is
    unnecessary in general. When stage 3 becomes a real implementation, the
    merge belongs there (it can read `record.run.hazard_scope` to bound what
    it adds), not in this function -- this test exists so a future session
    that adds real hazard detection without touching the merge logic finds a
    failing test here rather than a silent gap.
    """
    row = InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="prompt",
        response_text="response",
        supplied_hazard="hte",
    )

    record = build_record(row, _run_context())

    assert record.evaluated_hazards == ("hte",)
    assert record.detected_hazards == ()


def test_build_record_texts_share_the_verbatim_response_across_all_three_views() -> None:
    row = InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="prompt",
        response_text="the response text",
        supplied_hazard="hte",
    )

    record = build_record(row, _run_context())

    assert record.texts.original == "the response text"
    assert record.texts.decoded == "the response text"
    assert record.texts.working == "the response text"
    assert record.texts.history == ()
    assert dict(record.texts.named) == {}
