"""Slice 1A tests (`docs/planning/PR1_EXECUTION_PLAN.md`) for
`hazard_classifier/evaluator/record.py`.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path
from types import MappingProxyType

import pytest

from hazard_classifier.evaluator.record import (
    ComponentError,
    ComponentObservation,
    EvaluationRecord,
    Flags,
    HazardJudgment,
    Judgment,
    TextViews,
)

RECORD_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "src" / "hazard_classifier" / "evaluator" / "record.py"
)


def _make_record(**overrides) -> EvaluationRecord:
    defaults = dict(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="prompt",
        response_text="response",
        supplied_hazard="hte",
        run=None,
        texts=TextViews(original="response", decoded="response", working="response"),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=("hte",),
        flags=Flags(),
        per_hazard={},
        overall_result="non_violating",
        overall_failure_reason=None,
    )
    defaults.update(overrides)
    return EvaluationRecord(**defaults)


def test_record_replace_returns_a_new_instance_without_mutating_the_original() -> None:
    record = _make_record()
    updated = dataclasses.replace(record, exhausted_at="prompt_repetition")

    assert record.exhausted_at is None
    assert updated.exhausted_at == "prompt_repetition"
    assert record is not updated


def test_per_hazard_field_is_a_read_only_mapping() -> None:
    judgment = HazardJudgment(
        hazard="hte",
        source="supplied",
        legitimization_applies=True,
        provisional_l=None,
        provisional_e=None,
        final_l=None,
        final_e=None,
        decided_by="B1",
        result="non_violating",
        failure_reason=None,
    )
    record = _make_record(per_hazard={"hte": judgment})

    assert isinstance(record.per_hazard, MappingProxyType)
    assert record.per_hazard["hte"] is judgment
    with pytest.raises(TypeError):
        record.per_hazard["hte"] = judgment  # type: ignore[index]


def test_flags_default_to_not_evaluated_everywhere() -> None:
    flags = Flags()

    assert flags.empty_payload == "not_evaluated"
    assert flags.decoding_failed == "not_evaluated"
    assert flags.prompt_repetition == "not_evaluated"
    assert flags.narrative == "not_evaluated"
    assert flags.refusal == "not_evaluated"
    assert flags.sa_disclaimer == "not_evaluated"
    assert dict(flags.narrative_subtypes) == {}


def test_flags_narrative_subtypes_is_a_read_only_mapping() -> None:
    flags = Flags(narrative_subtypes={"role_play": "detected"})

    assert isinstance(flags.narrative_subtypes, MappingProxyType)
    with pytest.raises(TypeError):
        flags.narrative_subtypes["role_play"] = "not_detected"  # type: ignore[index]


def test_judgment_distribution_accepts_none() -> None:
    judgment = Judgment(label="L1", distribution=None, model_version="baseline-v1")

    assert judgment.distribution is None


def test_judgment_distribution_accepts_a_three_class_tuple() -> None:
    judgment = Judgment(label="L1", distribution=(0.1, 0.7, 0.2), model_version="pr5-v1")

    assert judgment.distribution == (0.1, 0.7, 0.2)


def test_component_observation_facts_is_a_read_only_mapping() -> None:
    observation = ComponentObservation(
        stage="decoding",
        implementation="baseline",
        version="1",
        maturity="working",
        outcome="ran",
        facts={"decoded": True},
        text_out="decoded text",
        errors=(),
    )

    assert isinstance(observation.facts, MappingProxyType)
    with pytest.raises(TypeError):
        observation.facts["decoded"] = False  # type: ignore[index]


def test_component_error_carries_stage_message_and_optional_hazard() -> None:
    error = ComponentError(stage="decoding", message="could not decode", hazard="hte")

    assert error.stage == "decoding"
    assert error.message == "could not decode"
    assert error.hazard == "hte"
    # hazard is optional -- a record-wide error names no single hazard.
    assert ComponentError(stage="decoding", message="x").hazard is None


def test_record_module_imports_nothing_else_from_evaluator_package() -> None:
    """The slice's own stated requirement: "record.py imports nothing else
    from evaluator/ -- assert structurally, by inspecting the module's
    imports." Parses `record.py`'s source rather than trusting a read.
    """
    tree = ast.parse(RECORD_MODULE_PATH.read_text(), filename=str(RECORD_MODULE_PATH))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                pytest.fail(
                    f"record.py has a relative import (a sibling module in "
                    f"evaluator/): level={node.level}, module={node.module!r}"
                )
            if node.module and node.module.startswith("hazard_classifier.evaluator"):
                pytest.fail(f"record.py imports from evaluator/: {node.module!r}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("hazard_classifier.evaluator"):
                    pytest.fail(f"record.py imports from evaluator/: {alias.name!r}")
