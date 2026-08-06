"""The pipeline (`docs/ARCHITECTURE.md` §3): the ten-stage order from
`docs/SCIENCE.md` §Modular pipeline, and §3.1's exhaustion short-circuit.

**No scientific decision logic lives here.** The pipeline decides which
stage runs next and what happens when working text goes empty; it never
decides what a hazard means, what a flag implies, or what result a
response gets. What a stage detected is that stage's own job
(`components/*`); what a result *means* is stage 10's (final integration,
not built until slice 1C).

The pipeline never imports a concrete component -- it resolves each stage's
selected implementation through the `Registry` it is given, by the
`(stage, implementation)` pair `run.open_run` already validated.
"""

from __future__ import annotations

import dataclasses

from .record import ComponentObservation, EvaluationRecord
from .registry import Registry
from .run import RunContext

# SCIENCE.md §Modular pipeline, in order. Stages are numbered 1-10 there;
# indices here are 0-9. Positions 0-6 (stages 1-7) are the only ones the
# §3.1 exhaustion short-circuit can fire after -- stage 1 can already find
# an empty response, and removing text is stages 4-7's job. Positions 7-9
# (stages 8-10: shared embedding, L/E scoring, final integration) are always
# skipped straight past on exhaustion, landing on stage 10.
STAGE_ORDER: tuple[str, ...] = (
    "empty_response",  # 1
    "decoding",  # 2
    "hazard_detection",  # 3
    "prompt_repetition",  # 4
    "narrative_detection",  # 5
    "refusal_detection",  # 6
    "disclaimer_detection",  # 7
    "embedding",  # 8
    "scoring",  # 9
    "final_integration",  # 10
)

_EXHAUSTION_ELIGIBLE_STAGES = frozenset(STAGE_ORDER[:7])
_FINAL_INTEGRATION_STAGE = STAGE_ORDER[-1]


def _is_exhausted(record: EvaluationRecord) -> bool:
    # ARCHITECTURE.md §3.1 / SCIENCE.md §Empty-response detection: "no
    # characters after trimming whitespace" -- the same structural test
    # stage 1 itself uses, applied uniformly to whatever `working` is after
    # any of stages 1-7.
    return record.texts.working.strip() == ""


def run_pipeline(record: EvaluationRecord, run_context: RunContext, registry: Registry) -> EvaluationRecord:
    """Run every stage in `STAGE_ORDER` against `record`, in order, applying
    the exhaustion short-circuit. `run_context` names which implementation
    each stage should use (already validated against `registry` by
    `run.open_run`); `registry` is consulted again here to actually resolve
    and invoke each `Component`.
    """
    for index, stage in enumerate(STAGE_ORDER):
        selection = run_context.component_selections[stage]
        component = registry.get(stage, selection.implementation)
        record = component.run(record)

        if stage in _EXHAUSTION_ELIGIBLE_STAGES and record.exhausted_at is None and _is_exhausted(record):
            record = dataclasses.replace(record, exhausted_at=stage)
            return _skip_to_final_integration(record, index, run_context, registry)

    return record


def _skip_to_final_integration(
    record: EvaluationRecord,
    exhausted_index: int,
    run_context: RunContext,
    registry: Registry,
) -> EvaluationRecord:
    """Record a `"skipped_short_circuit"` observation for every stage
    between the one that just exhausted the text and final integration,
    then run final integration itself -- "the pipeline skips every
    remaining stage and delivers the record straight to final integration"
    (`ARCHITECTURE.md` §3.1).
    """
    skipped_observations: list[ComponentObservation] = []
    for stage in STAGE_ORDER[exhausted_index + 1 : -1]:
        selection = run_context.component_selections[stage]
        component = registry.get(stage, selection.implementation)
        skipped_observations.append(
            ComponentObservation(
                stage=stage,
                implementation=selection.implementation,
                version=selection.version,
                maturity=component.maturity,
                outcome="skipped_short_circuit",
                facts={},
                text_out=None,
                errors=(),
            )
        )

    record = dataclasses.replace(record, observations=record.observations + tuple(skipped_observations))

    final_selection = run_context.component_selections[_FINAL_INTEGRATION_STAGE]
    final_component = registry.get(_FINAL_INTEGRATION_STAGE, final_selection.implementation)
    return final_component.run(record)
