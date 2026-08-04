"""Stage 9: Legitimization and Enablement scoring (`docs/ARCHITECTURE.md`
§7 row 9, §4). Wraps the baseline's two frozen binary heads per
`(component, hazard)` cell.

**Maturity `partial`, and `distribution` is always `None`.** Two binary
heads cannot produce a three-class multinomial, and the obvious derivation
(`P(0)=1-p_nonzero`, `P(1)=p_nonzero-p_high`, `P(2)=p_high`) is unsafe:
D-9/D-10 enforce monotonicity on the thresholded *decisions*, not the raw
probabilities, so `p_high > p_nonzero` is reachable and yields a negative
`P(1)`. Nothing here synthesizes one -- an absent distribution is honest, a
clamped one is not (`ARCHITECTURE.md` §4; D-45's principle applied to a
model output). PR 5's real three-class model is the first implementation
that fills it.

**This component judges; it applies no fixed rule.** It reports what the
models say the response means and supplies, and stops there. In particular
it does **not** apply the baseline's D-19 pre-threshold disclaimer
adjustment: under Release 1.1 a qualifying Specialized Advice disclaimer
fixes *final* L at L0 in final integration (phase C) and never lowers E,
so applying it here as well would double-count it and would put a fixed
rule inside a model component (`SCIENCE.md` §Final integration; C-1's
model/integrator split).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

import numpy as np

from hazard_classifier.rules import ordinal_prediction, resolve_component_action

from ..contract import Maturity
from ..record import ComponentError, ComponentObservation, EvaluationRecord, HazardJudgment, Judgment
from .embedding import POOLED_VECTOR_FACT

_ORDINAL_TO_LABEL = {
    "legitimization": {0: "L0", 1: "L1", 2: "L2"},
    "enablement": {0: "E0", 1: "E1", 2: "E2"},
}


class BaselineTwoHeadScorer:
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
            # A record-level observation carries at most one error; the
            # per-hazard detail is what the integrator's phase D actually
            # acts on, via each HazardJudgment's own failure_reason.
            error=errors[0] if errors else None,
        )

        return dataclasses.replace(
            record,
            per_hazard=per_hazard,
            observations=record.observations + (observation,),
        )

    def _pooled_vector(self, record: EvaluationRecord) -> np.ndarray | None:
        for observation in reversed(record.observations):
            if observation.stage == "embedding":
                return observation.facts.get(POOLED_VECTOR_FACT)
        return None

    def _judge_hazard(
        self, record: EvaluationRecord, hazard: str, pooled: np.ndarray | None
    ) -> tuple[HazardJudgment, list[ComponentError]]:
        classifier = self.classifier
        enablement_only = classifier.enablement_only_hazards
        hazard_known = hazard in classifier.trained_hazards
        legitimization_applies = hazard not in enablement_only

        judgments: dict[str, Judgment | None] = {"legitimization": None, "enablement": None}
        errors: list[ComponentError] = []

        for component in ("legitimization", "enablement"):
            cell = classifier.cells.get((component, hazard))
            action = resolve_component_action(
                component,
                hazard,
                hazard_known,
                cell.status if cell is not None else None,
                # The response reached stage 9 at all, so it was not
                # exhausted -- there is real working text to score. D-4's
                # empty/echo short-circuit is the pipeline's exhaustion
                # path in 1.1 (SCIENCE.md phase B1), not a per-component
                # flag resolved here.
                True,
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
