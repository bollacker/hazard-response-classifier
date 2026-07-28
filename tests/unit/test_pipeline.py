from __future__ import annotations

import pytest

from hazard_classifier.pipeline import (
    ASSESSMENT_STANDARD_VERSION,
    UPSTREAM_COMPONENT_ORDER,
    ComponentJudgment,
    ComponentResult,
    EvaluationIdentity,
    pipeline_manifest,
    prepare_response,
)


def test_prepare_response_emits_ordered_versioned_component_results() -> None:
    identity = EvaluationIdentity(
        prompt_id="prompt-1",
        response_id="response-1",
        request_id="request-1",
    )
    prepared = prepare_response(
        "Explain this request.",
        "This is a separate response.",
        intended_hazard="hte",
        identity=identity,
    )

    assert prepared.assessment_standard_version == ASSESSMENT_STANDARD_VERSION
    assert prepared.intended_hazard == "hte"
    assert prepared.identity == identity
    assert tuple(result.component for result in prepared.component_results) == (
        UPSTREAM_COMPONENT_ORDER
    )
    assert all(
        result.assessment_standard_version == ASSESSMENT_STANDARD_VERSION
        for result in prepared.component_results
    )
    assert all(result.identity == identity for result in prepared.component_results)

    assert prepared.component_result("decoding").status == "implemented"
    assert prepared.component_result("prompt_repetition").status == "partial"
    assert prepared.component_result("disclaimer_analysis").status == "partial"

    for component in ("hazard_detection", "narrative_analysis", "refusal_analysis"):
        result = prepared.component_result(component)
        assert result.status == "placeholder"
        assert result.output_text == result.input_text
        assert result.judgments == ()


def test_production_prepare_requires_identity() -> None:
    with pytest.raises(TypeError, match="identity"):
        prepare_response("prompt", "response")


def test_pipeline_manifest_records_order_versions_and_placeholder_status() -> None:
    manifest = pipeline_manifest()

    assert manifest["assessment_standard_version"] == "1.4"
    assert manifest["pipeline_version"] == "component-contract-v1"
    components = manifest["upstream_components"]
    assert tuple(component["component"] for component in components) == (
        UPSTREAM_COMPONENT_ORDER
    )
    assert {
        component["component"]
        for component in components
        if component["status"] == "placeholder"
    } == {"hazard_detection", "narrative_analysis", "refusal_analysis"}


def test_placeholder_components_cannot_change_text_or_emit_judgments() -> None:
    with pytest.raises(ValueError, match="cannot change text"):
        ComponentResult(
            component="placeholder",
            component_version="placeholder-0",
            assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
            status="placeholder",
            input_text="before",
            output_text="after",
            identity=None,
        )

    with pytest.raises(ValueError, match="cannot emit judgments"):
        ComponentResult(
            component="placeholder",
            component_version="placeholder-0",
            assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
            status="placeholder",
            input_text="same",
            output_text="same",
            identity=None,
            judgments=(ComponentJudgment("unexpected", True),),
        )


def test_prepare_response_preserves_current_prompt_and_disclaimer_flags() -> None:
    prompt = "Explain how to handle this material safely."
    prepared = prepare_response(
        prompt,
        f"{prompt} Consult a qualified professional.",
        identity=EvaluationIdentity("prompt-1", "response-1", "request-1"),
    )

    assert len(prepared.segments) == 2
    assert prepared.segments[0].prompt_repetition_flag is True
    assert prepared.segments[0].later_authored_continuation is False
    assert prepared.segments[1].disclaimer_flag is True
    assert prepared.disclaimer_sentence_count == 1

    prompt_result = prepared.component_result("prompt_repetition")
    assert prompt_result.judgments[0].value == 1
    disclaimer_result = prepared.component_result("disclaimer_analysis")
    assert disclaimer_result.judgments[0].value == 1


def test_prepare_response_keeps_empty_response_distinct() -> None:
    prepared = prepare_response(
        "A prompt.",
        "",
        identity=EvaluationIdentity("prompt-1", "response-1", "request-1"),
    )

    assert prepared.readable_response_text == ""
    assert prepared.segments == ()
    assert prepared.component_result("prompt_repetition").judgments[0].value == 0
    assert prepared.component_result("disclaimer_analysis").judgments[0].value == 0


def test_same_text_in_different_requests_keeps_distinct_identity() -> None:
    first_identity = EvaluationIdentity("prompt-1", "response-1", "request-1")
    second_identity = EvaluationIdentity("prompt-1", "response-1", "request-2")

    first = prepare_response("Same prompt.", "Same response.", identity=first_identity)
    second = prepare_response("Same prompt.", "Same response.", identity=second_identity)

    assert first.identity == first_identity
    assert second.identity == second_identity
    assert first.identity != second.identity
    assert all(result.identity == first_identity for result in first.component_results)
    assert all(result.identity == second_identity for result in second.component_results)


@pytest.mark.parametrize("field", ["prompt_id", "response_id", "request_id"])
def test_evaluation_identity_rejects_blank_ids(field: str) -> None:
    values = {
        "prompt_id": "prompt-1",
        "response_id": "response-1",
        "request_id": "request-1",
    }
    values[field] = " "

    with pytest.raises(ValueError, match=field):
        EvaluationIdentity(**values)
