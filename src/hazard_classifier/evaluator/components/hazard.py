"""Stage 3: hazard detection (`docs/ARCHITECTURE.md` §7, `docs/SCIENCE.md`
§Hazard detection). Placeholder: no approved implementation exists yet
(blocked on the Standards team's fixed examples). Passes the supplied
hazard through untouched and returns no additional hazards.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord


class HazardDetectionPlaceholder:
    stage: ClassVar[str] = "hazard_detection"
    implementation: ClassVar[str] = "placeholder"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "placeholder"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="not_evaluated",
            facts={},
            text_out=None,
            errors=(),
        )
        # `detected_hazards` is left untouched (empty unless another stage
        # ever populates it) -- a placeholder returns no additional hazards.
        return dataclasses.replace(record, observations=record.observations + (observation,))
