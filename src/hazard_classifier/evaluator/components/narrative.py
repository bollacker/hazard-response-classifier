"""Stage 5: narrative detection (`docs/ARCHITECTURE.md` §7, `docs/SCIENCE.md`
§Narrative detection). Placeholder: blocked on the Standards team's fixed,
human-labeled benign-narrative examples -- analysts do not set that
boundary. Passes content through unchanged; `flags.narrative` and
`flags.narrative_subtypes` are left at `Flags()`'s `"not_evaluated"`
default, never touched here.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord


class NarrativeDetectionPlaceholder:
    stage: ClassVar[str] = "narrative_detection"
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
