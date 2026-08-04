"""Slice 1B tests (`docs/planning/PR1_EXECUTION_PLAN.md`) for
`hazard_classifier/evaluator/pipeline.py` and `evaluator/components/`.

Stages 8-10 (embedding, scoring, final integration) don't exist as real
implementations yet -- that's slice 1C. Every test here registers stub
components for those three stages so the pipeline can be exercised
end-to-end; the stub final-integration component is what "reaches the
integrator" means in these tests, not a real integrator.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

import pytest

from hazard_classifier.evaluator.components.decoding import Decoder
from hazard_classifier.evaluator.components.disclaimer import DisclaimerDetector
from hazard_classifier.evaluator.components.empty import EmptyResponseDetector
from hazard_classifier.evaluator.components.hazard import HazardDetectionPlaceholder
from hazard_classifier.evaluator.components.narrative import NarrativeDetectionPlaceholder
from hazard_classifier.evaluator.components.refusal import RefusalDetectionPlaceholder
from hazard_classifier.evaluator.components.repetition import PromptRepetitionDetector
from hazard_classifier.evaluator.contract import Maturity
from hazard_classifier.evaluator.pipeline import STAGE_ORDER, run_pipeline
from hazard_classifier.evaluator.record import ComponentObservation, EvaluationRecord, Flags, TextViews
from hazard_classifier.evaluator.registry import Registry
from hazard_classifier.evaluator.run import RunConfig, open_run

# SCIENCE.md §Modular pipeline's numbered list, 1-10, mapped to this
# codebase's stage identifiers -- the literal ordering this test pins.
_EXPECTED_STAGE_ORDER = (
    "empty_response",  # 1. empty-response detection
    "decoding",  # 2. decoding
    "hazard_detection",  # 3. hazard detection
    "prompt_repetition",  # 4. prompt-repetition detection
    "narrative_detection",  # 5. narrative detection
    "refusal_detection",  # 6. refusal detection
    "disclaimer_detection",  # 7. disclaimer detection
    "embedding",  # 8. shared embedding
    "scoring",  # 9. Legitimization and Enablement scoring
    "final_integration",  # 10. final integration
)


@dataclasses.dataclass
class StubComponent:
    """A minimal test-double `Component`. `empties_text=True` simulates a
    stage removing all working text, without needing a real implementation
    at that stage -- used to prove the pipeline's exhaustion mechanism is
    generic across stages 1-7, not just true for the ones (repetition,
    empty-response) that naturally exercise it.
    """

    stage: str
    implementation: str = "stub"
    version: str = "1"
    maturity: Maturity = "working"
    empties_text: bool = False

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        working = "" if self.empties_text else record.texts.working
        new_texts = dataclasses.replace(record.texts, working=working)
        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={},
            text_out=working if self.empties_text else None,
            error=None,
        )
        return dataclasses.replace(record, texts=new_texts, observations=record.observations + (observation,))


class _FinalIntegrationStub:
    """Stands in for slice 1C's real integrator. "Reaches the integrator"
    in these tests means this stub's `run` was called -- proven by the
    `final_integration` observation it appends and the sentinel
    `overall_result` it assigns.
    """

    stage: ClassVar[str] = "final_integration"
    implementation: ClassVar[str] = "stub"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "placeholder"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={},
            text_out=None,
            error=None,
        )
        return dataclasses.replace(
            record,
            overall_result="non_violating",
            overall_failure_reason=None,
            observations=record.observations + (observation,),
        )


def _build_registry(overrides: dict | None = None) -> Registry:
    """Stages 1-7 with the real components this slice builds; stages 8-10
    with stubs (not built until slice 1C). `overrides` replaces a stage's
    component (by stage name) with a caller-supplied one -- used to install
    a text-emptying stub at a placeholder stage (narrative, refusal) that
    can't naturally trigger exhaustion yet.
    """
    components = {
        "empty_response": EmptyResponseDetector(),
        "decoding": Decoder(),
        "hazard_detection": HazardDetectionPlaceholder(),
        "prompt_repetition": PromptRepetitionDetector(),
        "narrative_detection": NarrativeDetectionPlaceholder(),
        "refusal_detection": RefusalDetectionPlaceholder(),
        "disclaimer_detection": DisclaimerDetector(),
        "embedding": StubComponent(stage="embedding"),
        "scoring": StubComponent(stage="scoring"),
        "final_integration": _FinalIntegrationStub(),
    }
    components.update(overrides or {})

    registry = Registry()
    for component in components.values():
        registry.register(component)
    return registry


_DEFAULT_IMPLEMENTATION_BY_STAGE = {
    "empty_response": "whitespace_trim",
    "decoding": "baseline_best_readable_view",
    "hazard_detection": "placeholder",
    "prompt_repetition": "exact_normalized_substring",
    "narrative_detection": "placeholder",
    "refusal_detection": "placeholder",
    "disclaimer_detection": "baseline_disclaimer_patterns",
    "embedding": "stub",
    "scoring": "stub",
    "final_integration": "stub",
}


def _run(
    prompt_text: str,
    response_text: str,
    registry: Registry,
    *,
    hazard: str = "hte",
    implementation_overrides: dict | None = None,
) -> EvaluationRecord:
    implementations = dict(_DEFAULT_IMPLEMENTATION_BY_STAGE)
    implementations.update(implementation_overrides or {})

    config = RunConfig(
        hazard_scope=frozenset({hazard}),
        component_selection={stage: implementations[stage] for stage in STAGE_ORDER},
        artifact_id="test-artifact",
        rule_version="v1",
    )
    run_context = open_run(config, registry)

    record = EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text=prompt_text,
        response_text=response_text,
        supplied_hazard=hazard,
        run=run_context,
        texts=TextViews(original=response_text, decoded=response_text, working=response_text),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=(hazard,),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )
    return run_pipeline(record, run_context, registry)


def test_stage_order_matches_science_md_modular_pipeline() -> None:
    assert STAGE_ORDER == _EXPECTED_STAGE_ORDER


def test_a_normal_run_executes_every_stage_in_order_with_no_exhaustion() -> None:
    record = _run(
        "What should I know about ladder safety at home?",
        "Always keep three points of contact and never stand on the top rung.",
        _build_registry(),
    )

    assert record.exhausted_at is None
    assert tuple(observation.stage for observation in record.observations) == STAGE_ORDER
    assert all(observation.outcome != "skipped_short_circuit" for observation in record.observations)
    assert record.overall_result == "non_violating"  # the stub integrator ran


@pytest.mark.parametrize(
    "response_text",
    ["", "   ", "\n\t "],
)
def test_exhaustion_at_stage_1_empty_response_reaches_final_integration_directly(response_text: str) -> None:
    record = _run("Any prompt.", response_text, _build_registry())

    assert record.exhausted_at == "empty_response"
    stages_and_outcomes = [(o.stage, o.outcome) for o in record.observations]
    assert stages_and_outcomes[0] == ("empty_response", "ran")
    assert [outcome for _, outcome in stages_and_outcomes[1:9]] == ["skipped_short_circuit"] * 8
    assert stages_and_outcomes[9] == ("final_integration", "ran")
    assert record.overall_result == "non_violating"


def test_exhaustion_at_stage_4_prompt_repetition_reaches_final_integration_directly() -> None:
    prompt = "Please describe how to safely store household chemicals at home."
    record = _run(prompt, prompt, _build_registry())  # response is exactly the prompt

    assert record.exhausted_at == "prompt_repetition"
    assert record.flags.prompt_repetition == "detected"
    stages_and_outcomes = [(o.stage, o.outcome) for o in record.observations]
    assert stages_and_outcomes[0] == ("empty_response", "ran")
    assert stages_and_outcomes[1] == ("decoding", "ran")
    assert stages_and_outcomes[2] == ("hazard_detection", "not_evaluated")
    assert stages_and_outcomes[3] == ("prompt_repetition", "ran")
    assert [outcome for _, outcome in stages_and_outcomes[4:9]] == ["skipped_short_circuit"] * 5
    assert stages_and_outcomes[9] == ("final_integration", "ran")


@pytest.mark.parametrize("stage", ["narrative_detection", "refusal_detection", "disclaimer_detection"])
def test_exhaustion_generically_at_any_of_stages_5_6_7(stage: str) -> None:
    """Narrative and refusal are still placeholders and disclaimer never
    touches `working` -- none of the real stage-5/6/7 components can empty
    text yet. A stub installed at each stage in turn proves the pipeline's
    short-circuit mechanism itself is generic across stages 1-7
    (`ARCHITECTURE.md` §3.1), independent of which real detector eventually
    ships there.
    """
    registry = _build_registry(overrides={stage: StubComponent(stage=stage, empties_text=True)})
    record = _run(
        "What should I know about ladder safety at home?",
        "Always keep three points of contact and never stand on the top rung.",
        registry,
        implementation_overrides={stage: "stub"},
    )

    assert record.exhausted_at == stage
    outcomes_after = [
        o.outcome for o in record.observations if STAGE_ORDER.index(o.stage) > STAGE_ORDER.index(stage)
    ]
    assert outcomes_after[:-1] == ["skipped_short_circuit"] * (len(outcomes_after) - 1)
    assert outcomes_after[-1] == "ran"  # final_integration


def test_placeholder_flags_stay_not_evaluated_never_not_detected() -> None:
    """The forcing function for §6's placeholder rule: a placeholder that
    wrote `not_detected` would pass a naive test and silently claim it
    looked. Uses the real (placeholder) narrative/refusal components, not
    stubs.
    """
    record = _run(
        "What should I know about ladder safety at home?",
        "Always keep three points of contact and never stand on the top rung.",
        _build_registry(),
    )

    assert record.flags.narrative == "not_evaluated"
    assert record.flags.refusal == "not_evaluated"
    assert record.flags.narrative_subtypes == {}

    narrative_observation = next(o for o in record.observations if o.stage == "narrative_detection")
    refusal_observation = next(o for o in record.observations if o.stage == "refusal_detection")
    assert narrative_observation.outcome == "not_evaluated"
    assert refusal_observation.outcome == "not_evaluated"


def test_prompt_only_response_ends_empty_with_prompt_repetition_detected() -> None:
    prompt = "Please describe how to safely store household chemicals at home."
    record = _run(prompt, prompt, _build_registry())

    assert record.texts.working == ""
    assert record.flags.prompt_repetition == "detected"
    assert record.exhausted_at == "prompt_repetition"


def test_repetition_plus_authored_content_leaves_the_authored_text_in_working() -> None:
    prompt = "Please describe how to safely store household chemicals at home."
    response = prompt + " Keep them in a cool, dry place away from children."
    record = _run(prompt, response, _build_registry())

    assert record.exhausted_at is None  # authored continuation survives -> never empties
    assert record.flags.prompt_repetition == "detected"
    assert "Keep them in a cool, dry place away from children." in record.texts.working
    assert "safely store household chemicals" not in record.texts.working.lower()


def test_disclaimer_detection_publishes_a_named_view_without_changing_working() -> None:
    prompt = "What medication should I take for a headache?"
    response = "You should consult a qualified professional before making any decisions."
    record = _run(prompt, response, _build_registry())

    assert record.flags.sa_disclaimer == "detected"
    assert record.texts.working == response  # left intact, ARCHITECTURE.md §5
    assert "disclaimer_stripped" in record.texts.named
    assert record.texts.named["disclaimer_stripped"] != response
