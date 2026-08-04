"""Stage 1: empty-response detection (`docs/ARCHITECTURE.md` §7,
`docs/SCIENCE.md` §Empty-response detection). Working implementation: a
whitespace-trim test that changes no text.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord


class EmptyResponseDetector:
    stage: ClassVar[str] = "empty_response"
    implementation: ClassVar[str] = "whitespace_trim"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "working"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        is_empty = record.texts.working.strip() == ""

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={"empty": is_empty},
            text_out=None,  # SCIENCE.md §Empty-response detection: changes no text
            error=None,
        )

        return dataclasses.replace(
            record,
            flags=dataclasses.replace(
                record.flags, empty_payload=("detected" if is_empty else "not_detected")
            ),
            observations=record.observations + (observation,),
        )
