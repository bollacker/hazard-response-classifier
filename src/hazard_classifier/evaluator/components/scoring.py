"""Stage 9: Legitimization and Enablement scoring (`docs/ARCHITECTURE.md`
§7 row 9, §4).

**Two implementations, both registered** (§6 keys the registry on
`(stage, implementation_id)`, and PR 7's runner selects by id):

- `MultinomialPerHazardScorer` (`multinomial_per_hazard`) -- Release 1.1's
  real model, **working**. It emits the three-class distribution
  `SCIENCE.md` requires.
- `BaselineTwoHeadScorer` (`baseline_two_head`) -- PR 1's wrapped baseline,
  **partial**, kept rather than replaced. It is the only implementation that
  exercises §4's `distribution=None` path, and PR 1 through PR 4's tests
  select it; removing it would leave a component contract untested.

Neither applies a fixed rule. Both report what the models say the response
means and supplies, and stop there -- applicability, the disclaimer modifier,
and the L/E-to-result tables are final integration's alone
(`ARCHITECTURE.md` §9).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

import numpy as np

from hazard_classifier.rules import ordinal_prediction, resolve_component_action

from ..artifact import EvaluatorArtifact
from ..contract import Maturity
from ..record import ComponentError, ComponentObservation, EvaluationRecord, HazardJudgment, Judgment
from .embedding import POOLED_VECTOR_FACT

_COMPONENTS = ("legitimization", "enablement")

_ORDINAL_TO_LABEL = {
    "legitimization": {0: "L0", 1: "L1", 2: "L2"},
    "enablement": {0: "E0", 1: "E1", 2: "E2"},
}

# Every response that reaches stage 9 has real working text: the pipeline's
# §3.1 short-circuit sends an exhausted record straight to stage 10, so D-4's
# empty/echo case is `SCIENCE.md` phase B1's, never a per-component flag
# resolved here. Named once rather than repeated as a bare `True` argument at
# each `resolve_component_action` call site.
_REACHED_STAGE_NINE_SO_TEXT_EXISTS = True


class BaselineTwoHeadScorer:
    """PR 1's wrapped baseline: the two frozen binary heads per
    `(component, hazard)` cell.

    **Maturity `partial`, and `distribution` is always `None`.** Two binary
    heads cannot produce a three-class multinomial, and the obvious
    derivation (`P(0)=1-p_nonzero`, `P(1)=p_nonzero-p_high`, `P(2)=p_high`)
    is unsafe: D-9/D-10 enforce monotonicity on the thresholded *decisions*,
    not the raw probabilities, so `p_high > p_nonzero` is reachable and
    yields a negative `P(1)`. Nothing here synthesizes one -- an absent
    distribution is honest, a clamped one is not (`ARCHITECTURE.md` §4;
    D-45's principle applied to a model output).

    **Kept registered after PR 5, deliberately.** `MultinomialPerHazardScorer`
    is Release 1.1's model, but this is the only implementation that exercises
    §4's `distribution=None` path, and PR 1 through PR 4's tests select it.

    **This component judges; it applies no fixed rule.** In particular it does
    **not** apply the baseline's D-19 pre-threshold disclaimer adjustment:
    under Release 1.1 a qualifying Specialized Advice disclaimer fixes *final*
    L at L0 in final integration (phase C) and never lowers E, so applying it
    here as well would double-count it and would put a fixed rule inside a
    model component (`SCIENCE.md` §Final integration; C-1's model/integrator
    split).
    """

    stage: ClassVar[str] = "scoring"
    implementation: ClassVar[str] = "baseline_two_head"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "partial"

    def __init__(self, classifier) -> None:
        """`classifier` is a fitted/loaded baseline
        `HazardResponseClassifier`. Its frozen hazard-family sets are the
        serve-time source of truth (D-23) -- installed config is never
        consulted here.
        """
        self.classifier = classifier

    @property
    def model_version(self) -> str:
        return f"{self.implementation}:{self.version}"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        pooled = self._pooled_vector(record)

        per_hazard = dict(record.per_hazard)
        errors: list[ComponentError] = []

        for hazard in record.evaluated_hazards:
            judgment, hazard_errors = self._judge_hazard(record, hazard, pooled)
            per_hazard[hazard] = judgment
            errors.extend(hazard_errors)

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="error" if errors else "ran",
            facts={"scored_hazards": tuple(record.evaluated_hazards)},
            text_out=None,
            # Every error, one per failing `(target, hazard)` -- D-76. This
            # component is why §4's field is a tuple: it can fail twice for
            # one hazard (both targets unavailable) and again for the next.
            errors=tuple(errors),
        )

        return dataclasses.replace(
            record,
            per_hazard=per_hazard,
            observations=record.observations + (observation,),
        )

    def _pooled_vector(self, record: EvaluationRecord) -> np.ndarray | None:
        return _pooled_vector(record)

    def _judge_hazard(
        self, record: EvaluationRecord, hazard: str, pooled: np.ndarray | None
    ) -> tuple[HazardJudgment, list[ComponentError]]:
        classifier = self.classifier
        enablement_only = classifier.enablement_only_hazards
        hazard_known = hazard in classifier.trained_hazards
        legitimization_applies = hazard not in enablement_only

        judgments: dict[str, Judgment | None] = {"legitimization": None, "enablement": None}
        errors: list[ComponentError] = []

        for component in _COMPONENTS:
            cell = classifier.cells.get((component, hazard))
            action = resolve_component_action(
                component,
                hazard,
                hazard_known,
                cell.status if cell is not None else None,
                _REACHED_STAGE_NINE_SO_TEXT_EXISTS,
                enablement_only,
            )

            if action == "not_required":
                continue
            if action in ("fail_unseen_hazard", "fail_skipped_cell"):
                errors.append(
                    ComponentError(
                        stage=self.stage,
                        message=f"{component} unavailable for hazard {hazard!r}: {action}",
                        hazard=hazard,
                    )
                )
                continue
            if pooled is None:
                errors.append(
                    ComponentError(
                        stage=self.stage,
                        message=f"{component} for hazard {hazard!r}: no pooled embedding available",
                        hazard=hazard,
                    )
                )
                continue

            assert cell is not None  # guaranteed by resolve_component_action's contract
            features = np.asarray([pooled])
            nonzero = float(cell.nonzero_head.predict_proba_centered(features)[0])
            high = float(cell.high_head.predict_proba_centered(features)[0])
            ordinal = int(
                ordinal_prediction(
                    np.asarray([nonzero]),
                    np.asarray([high]),
                    cell.nonzero_threshold,
                    cell.high_threshold,
                )[0]
            )
            judgments[component] = Judgment(
                label=_ORDINAL_TO_LABEL[component][ordinal],
                distribution=None,  # ARCHITECTURE.md §4 -- never synthesized
                model_version=self.model_version,
            )

        return (
            HazardJudgment(
                hazard=hazard,
                source="supplied" if hazard == record.supplied_hazard else "detected",
                legitimization_applies=legitimization_applies,
                provisional_l=judgments["legitimization"],
                provisional_e=judgments["enablement"],
            ),
            errors,
        )


class MultinomialPerHazardScorer:
    """Release 1.1's L and E models: a flat three-class multinomial softmax
    per `(target, hazard)` cell, loaded from a 1.1 evaluator artifact
    ([D-68](../../../docs/planning/DECISIONS.md#d-68);
    `PR5_EXECUTION_PLAN.md` §7).

    **The first implementation that fills `Judgment.distribution`.**
    `SCIENCE.md` §Legitimization Scoring and §Enablement Scoring require a
    three-class multinomial over L0/L1/L2 and E0/E1/E2, which no two-head
    structure can produce (`ARCHITECTURE.md` §4). The label is the
    distribution's `argmax` -- `PREREGISTRATION_LE_STRUCTURE.md` §6: every
    non-`L3` candidate decides by argmax, and there are no thresholds to
    apply.

    **`model_version` is the artifact's, not this class's.** `SCIENCE.md`
    §Legitimization/Enablement Training require models to be "trained and
    versioned separately from scoring" and every run to "use an existing,
    locked model version" -- so the version on a judgment names the *fitted
    model*, while this component's own implementation and version are already
    recorded on its `ComponentObservation`. The baseline scorer reports its
    code twice because it has no artifact of its own to name.

    **Working, and still not evaluated.** Maturity `working` says the
    component does what `ARCHITECTURE.md` §7 row 9 specifies. It says nothing
    about quality: no approved per-outcome criteria exist, so both models are
    reported *not evaluated* (`SCIENCE.md` §Evidence and outputs), and D-68
    is a null result. A well-formed distribution that sums to 1 is not
    evidence the numbers in it are right -- a cell fitted on ~42 rows of two
    classes returns three tidy numbers exactly as readily as a good one does.

    **This component judges; it applies no fixed rule.** Applicability, the
    phase C disclaimer modifier, and the L/E-to-result tables belong to final
    integration alone. `legitimization_applies` here is a *report* of the
    enablement-only test, identical to the baseline scorer's, not a decision
    this component makes.
    """

    stage: ClassVar[str] = "scoring"
    implementation: ClassVar[str] = "multinomial_per_hazard"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "working"

    def __init__(self, artifact: EvaluatorArtifact) -> None:
        """`artifact` is a loaded 1.1 evaluator artifact
        (`evaluator/artifact.py`). Its frozen `rules.json` is the serve-time
        source of truth for hazard families and hazard support (D-23) --
        installed config is never consulted here.
        """
        self.artifact = artifact

    @property
    def model_version(self) -> str:
        return f"{self.artifact.artifact_id}:{self.artifact.artifact_version}"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        pooled = _pooled_vector(record)

        per_hazard = dict(record.per_hazard)
        errors: list[ComponentError] = []

        for hazard in record.evaluated_hazards:
            judgment, hazard_errors = self._judge_hazard(record, hazard, pooled)
            per_hazard[hazard] = judgment
            errors.extend(hazard_errors)

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="error" if errors else "ran",
            facts={
                "scored_hazards": tuple(record.evaluated_hazards),
                "model_version": self.model_version,
            },
            text_out=None,
            # Every error, one per failing `(target, hazard)` -- D-76. This
            # component is why §4's field is a tuple: it can fail twice for
            # one hazard (both targets unavailable) and again for the next,
            # and a single-error field made it discard all but the first.
            errors=tuple(errors),
        )

        return dataclasses.replace(
            record,
            per_hazard=per_hazard,
            observations=record.observations + (observation,),
        )

    def _model(self, component: str):
        return getattr(self.artifact.models, component)

    def _judge_hazard(
        self, record: EvaluationRecord, hazard: str, pooled: np.ndarray | None
    ) -> tuple[HazardJudgment, list[ComponentError]]:
        rules = self.artifact.rules
        enablement_only = rules.enablement_only_hazards
        hazard_known = hazard in rules.supported_hazards
        legitimization_applies = hazard not in enablement_only

        judgments: dict[str, Judgment | None] = {"legitimization": None, "enablement": None}
        errors: list[ComponentError] = []

        for component in _COMPONENTS:
            model = self._model(component)
            cell = model.cells.get(hazard)
            # `resolve_component_action`'s allow-list (D-20) reads exactly
            # `"fit"`; a cell D-45 left unavailable, and one absent for any
            # other reason, both fail closed identically.
            cell_status = "fit" if cell is not None else "skipped"

            action = resolve_component_action(
                component,
                hazard,
                hazard_known,
                cell_status,
                _REACHED_STAGE_NINE_SO_TEXT_EXISTS,
                enablement_only,
            )

            if action == "not_required":
                continue
            if action in ("fail_unseen_hazard", "fail_skipped_cell"):
                # D-45: unavailable is unavailable. Never a substituted
                # judgment, never a uniform distribution -- the integrator's
                # phase D turns this into a per-hazard failure.
                errors.append(
                    ComponentError(
                        stage=self.stage,
                        message=f"{component} unavailable for hazard {hazard!r}: {action}",
                        hazard=hazard,
                    )
                )
                continue
            if pooled is None:
                errors.append(
                    ComponentError(
                        stage=self.stage,
                        message=f"{component} for hazard {hazard!r}: no pooled embedding available",
                        hazard=hazard,
                    )
                )
                continue

            assert cell is not None  # guaranteed by the cell_status the action was resolved from
            # The cell directly, not `model.predict_proba` -- a NaN row is
            # structurally unreachable this way, so an unavailable cell can
            # only ever leave through the `ComponentError` path above.
            distribution = cell.predict_proba(np.asarray([pooled]))[0]
            ordinal = int(np.argmax(distribution))
            judgments[component] = Judgment(
                label=_ORDINAL_TO_LABEL[component][ordinal],
                distribution=(
                    float(distribution[0]),
                    float(distribution[1]),
                    float(distribution[2]),
                ),
                model_version=self.model_version,
            )

        return (
            HazardJudgment(
                hazard=hazard,
                source="supplied" if hazard == record.supplied_hazard else "detected",
                legitimization_applies=legitimization_applies,
                provisional_l=judgments["legitimization"],
                provisional_e=judgments["enablement"],
            ),
            errors,
        )


def _pooled_vector(record: EvaluationRecord) -> np.ndarray | None:
    """Stage 8's published vector, read back off the record. Stages
    communicate through the record, never by importing each other (§6).
    """
    for observation in reversed(record.observations):
        if observation.stage == "embedding":
            return observation.facts.get(POOLED_VECTOR_FACT)
    return None
