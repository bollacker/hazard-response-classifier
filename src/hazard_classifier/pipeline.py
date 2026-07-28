"""Versioned component handoffs for response preprocessing.

This module introduces the shared structure required to add Assessment
Standard 1.4 components without changing the classifier's current scoring
behavior.  Existing decoding, prompt-repetition, and disclaimer behavior is
wrapped here.  Components that do not yet exist are explicit pass-through
placeholders: they cannot change text or emit judgments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from hazard_classifier.preprocess import decode, segment
from hazard_classifier.preprocess.flags import (
    disclaimer_label,
    later_authored_continuation,
    prompt_repetition_features,
)

ASSESSMENT_STANDARD_VERSION = "1.4"
PIPELINE_VERSION = "component-contract-v1"

ComponentStatus = Literal["implemented", "partial", "placeholder"]
JudgmentValue = str | bool | int | float | tuple[str, ...] | None


@dataclass(frozen=True)
class ComponentSpec:
    """The version and implementation status frozen into model artifacts."""

    component: str
    component_version: str
    status: ComponentStatus


UPSTREAM_COMPONENT_SPECS: tuple[ComponentSpec, ...] = (
    ComponentSpec("decoding", "1", "implemented"),
    ComponentSpec("hazard_detection", "placeholder-0", "placeholder"),
    ComponentSpec("prompt_repetition", "1", "partial"),
    ComponentSpec("narrative_analysis", "placeholder-0", "placeholder"),
    ComponentSpec("refusal_analysis", "placeholder-0", "placeholder"),
    ComponentSpec("disclaimer_analysis", "1", "partial"),
)

UPSTREAM_COMPONENT_ORDER: tuple[str, ...] = tuple(
    spec.component for spec in UPSTREAM_COMPONENT_SPECS
)
_SPEC_BY_COMPONENT = {
    spec.component: spec for spec in UPSTREAM_COMPONENT_SPECS
}


@dataclass(frozen=True)
class ComponentJudgment:
    """One named categorical or numeric output from a component."""

    name: str
    value: JudgmentValue
    reason: str = ""


@dataclass(frozen=True)
class EvaluationIdentity:
    """Opaque datastore IDs for one prompt/response/request evaluation."""

    prompt_id: str
    response_id: str
    request_id: str

    def __post_init__(self) -> None:
        for field_name in ("prompt_id", "response_id", "request_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be a non-empty opaque ID.")


@dataclass(frozen=True)
class ComponentResult:
    """The standard handoff produced by every upstream component."""

    component: str
    component_version: str
    assessment_standard_version: str
    status: ComponentStatus
    input_text: str
    output_text: str
    identity: EvaluationIdentity | None
    judgments: tuple[ComponentJudgment, ...] = ()

    def __post_init__(self) -> None:
        if self.status == "placeholder":
            if self.output_text != self.input_text:
                raise ValueError("A placeholder component cannot change text.")
            if self.judgments:
                raise ValueError("A placeholder component cannot emit judgments.")


@dataclass(frozen=True)
class PreparedSegment:
    """One decoded response segment with the currently active flags."""

    text: str
    start: int
    end: int
    segment_type: str
    prompt_repetition_flag: bool
    later_authored_continuation: bool
    prompt_repetition_probability: float
    prompt_repetition_type: str
    prompt_repetition_similarity: float
    prompt_repetition_source_span: str
    prompt_repetition_response_span: str
    disclaimer_flag: bool
    disclaimer_reason: str


@dataclass(frozen=True)
class PreparedResponse:
    """The complete upstream handoff consumed by embedding and pooling."""

    identity: EvaluationIdentity | None
    pipeline_version: str
    assessment_standard_version: str
    prompt_text: str
    intended_hazard: str
    original_response_text: str
    readable_prompt_text: str
    readable_response_text: str
    segments: tuple[PreparedSegment, ...]
    component_results: tuple[ComponentResult, ...]

    def component_result(self, component: str) -> ComponentResult:
        for result in self.component_results:
            if result.component == component:
                return result
        raise KeyError(component)

    @property
    def disclaimer_sentence_count(self) -> int:
        return sum(segment.disclaimer_flag for segment in self.segments)


def _placeholder(
    component: str,
    text: str,
    identity: EvaluationIdentity | None,
) -> ComponentResult:
    spec = _SPEC_BY_COMPONENT[component]
    return ComponentResult(
        component=component,
        component_version=spec.component_version,
        assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
        status=spec.status,
        input_text=text,
        output_text=text,
        identity=identity,
    )


def pipeline_manifest() -> dict[str, object]:
    """Return the component contract stored with every new model artifact."""

    return {
        "pipeline_version": PIPELINE_VERSION,
        "assessment_standard_version": ASSESSMENT_STANDARD_VERSION,
        "upstream_components": [
            {
                "component": spec.component,
                "component_version": spec.component_version,
                "status": spec.status,
            }
            for spec in UPSTREAM_COMPONENT_SPECS
        ],
    }


def _prepare_response(
    prompt_text: str,
    response_text: str,
    intended_hazard: str = "",
    *,
    identity: EvaluationIdentity | None,
    max_chars: int = 420,
    stride: int = 210,
) -> PreparedResponse:
    """Run the current upstream stages and return their ordered handoffs.

    This is deliberately behavior-preserving.  Prompt repetition and
    disclaimers are still flags only; the current pooling and business rules
    continue to consume those flags exactly as before.
    """

    context = "\n\n".join([prompt_text, response_text])
    prompt_readable = str(decode.best_readable_view(prompt_text, prompt_text)["review_text"])
    response_decoding = decode.best_readable_view(response_text, context)
    response_readable = str(response_decoding["review_text"])

    component_results: list[ComponentResult] = [
        ComponentResult(
            component="decoding",
            component_version=_SPEC_BY_COMPONENT["decoding"].component_version,
            assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
            status=_SPEC_BY_COMPONENT["decoding"].status,
            input_text=response_text,
            output_text=response_readable,
            judgments=(
                ComponentJudgment(
                    "transform_method",
                    str(response_decoding["transform_method"]),
                ),
                ComponentJudgment(
                    "transform_confidence",
                    float(response_decoding["transform_confidence"]),
                ),
            ),
            identity=identity,
        ),
        _placeholder("hazard_detection", response_readable, identity),
    ]

    raw_segments = segment.segment_text(response_readable, max_chars=max_chars, stride=stride)
    repetition_rows: list[tuple[segment.Segment, dict[str, object], bool]] = []
    repeated_count = 0
    continuation_count = 0
    for piece in raw_segments:
        repetition = prompt_repetition_features(
            piece.text,
            prompt_readable,
            piece.start,
            piece.end,
        )
        is_repetition = float(repetition["prompt_repetition_probability"]) >= 0.5
        has_continuation = is_repetition and later_authored_continuation(
            piece.text,
            prompt_readable,
        )
        repeated_count += int(is_repetition)
        continuation_count += int(has_continuation)
        repetition_rows.append((piece, repetition, has_continuation))

    component_results.append(
        ComponentResult(
            component="prompt_repetition",
            component_version=_SPEC_BY_COMPONENT[
                "prompt_repetition"
            ].component_version,
            assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
            status=_SPEC_BY_COMPONENT["prompt_repetition"].status,
            input_text=response_readable,
            output_text=response_readable,
            judgments=(
                ComponentJudgment("repeated_segment_count", repeated_count),
                ComponentJudgment(
                    "authored_continuation_segment_count",
                    continuation_count,
                ),
            ),
            identity=identity,
        )
    )
    component_results.append(
        _placeholder("narrative_analysis", response_readable, identity)
    )
    component_results.append(
        _placeholder("refusal_analysis", response_readable, identity)
    )

    prepared_segments: list[PreparedSegment] = []
    disclaimer_count = 0
    for piece, repetition, has_continuation in repetition_rows:
        has_disclaimer, disclaimer_reason = disclaimer_label(piece.text)
        disclaimer_count += int(has_disclaimer)
        prepared_segments.append(
            PreparedSegment(
                text=piece.text,
                start=piece.start,
                end=piece.end,
                segment_type=piece.segment_type,
                prompt_repetition_flag=(
                    float(repetition["prompt_repetition_probability"]) >= 0.5
                ),
                later_authored_continuation=has_continuation,
                prompt_repetition_probability=float(
                    repetition["prompt_repetition_probability"]
                ),
                prompt_repetition_type=str(repetition["prompt_repetition_type"]),
                prompt_repetition_similarity=float(
                    repetition["prompt_repetition_similarity"]
                ),
                prompt_repetition_source_span=str(
                    repetition["prompt_repetition_source_span"]
                ),
                prompt_repetition_response_span=str(
                    repetition["prompt_repetition_response_span"]
                ),
                disclaimer_flag=has_disclaimer,
                disclaimer_reason=disclaimer_reason,
            )
        )

    component_results.append(
        ComponentResult(
            component="disclaimer_analysis",
            component_version=_SPEC_BY_COMPONENT[
                "disclaimer_analysis"
            ].component_version,
            assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
            status=_SPEC_BY_COMPONENT["disclaimer_analysis"].status,
            input_text=response_readable,
            output_text=response_readable,
            judgments=(
                ComponentJudgment("disclaimer_sentence_count", disclaimer_count),
            ),
            identity=identity,
        )
    )

    if tuple(result.component for result in component_results) != UPSTREAM_COMPONENT_ORDER:
        raise RuntimeError("Upstream component order changed unexpectedly.")

    return PreparedResponse(
        identity=identity,
        pipeline_version=PIPELINE_VERSION,
        assessment_standard_version=ASSESSMENT_STANDARD_VERSION,
        prompt_text=prompt_text,
        intended_hazard=intended_hazard,
        original_response_text=response_text,
        readable_prompt_text=prompt_readable,
        readable_response_text=response_readable,
        segments=tuple(prepared_segments),
        component_results=tuple(component_results),
    )


def prepare_response(
    prompt_text: str,
    response_text: str,
    intended_hazard: str = "",
    *,
    identity: EvaluationIdentity,
    max_chars: int = 420,
    stride: int = 210,
) -> PreparedResponse:
    """Prepare one identified production response."""

    return _prepare_response(
        prompt_text,
        response_text,
        intended_hazard,
        identity=identity,
        max_chars=max_chars,
        stride=stride,
    )


def prepare_legacy_response(
    prompt_text: str,
    response_text: str,
    intended_hazard: str = "",
    *,
    max_chars: int = 420,
    stride: int = 210,
) -> PreparedResponse:
    """Prepare an old CSV row that has no canonical datastore identity."""

    return _prepare_response(
        prompt_text,
        response_text,
        intended_hazard,
        identity=None,
        max_chars=max_chars,
        stride=stride,
    )
