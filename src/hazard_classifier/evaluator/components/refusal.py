"""Stage 6: refusal detection (`docs/ARCHITECTURE.md` §7, `docs/SCIENCE.md`
§Refusal detection). Placeholder: no approved implementation exists yet.
Passes content through unchanged; `flags.refusal` is left at `Flags()`'s
`"not_evaluated"` default, never touched here.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord


class RefusalDetectionPlaceholder:
    stage: ClassVar[str] = "refusal_detection"
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
            error=None,
        )
        return dataclasses.replace(record, observations=record.observations + (observation,))
