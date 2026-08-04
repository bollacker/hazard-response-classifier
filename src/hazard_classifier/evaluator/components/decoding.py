"""Stage 2: decoding (`docs/ARCHITECTURE.md` §7, `docs/SCIENCE.md`
§Decoding). Working implementation, wrapping the baseline's
`preprocess/decode.py` `best_readable_view`.

`best_readable_view` always returns a candidate (raw text is always among
them), so it has no failure path today -- `decoding_failed` is always
`"not_detected"` under this implementation. `SCIENCE.md`'s "if it cannot
[recover an accurate rendering], it returns... a decoding-failure flag and
an error" describes a case this wrapped baseline function cannot currently
produce, not a case this component silently ignores.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from hazard_classifier.preprocess.decode import best_readable_view

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord, TextStep


class Decoder:
    stage: ClassVar[str] = "decoding"
    implementation: ClassVar[str] = "baseline_best_readable_view"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "working"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        working = record.texts.working
        # `best_readable_view` also considers substitution maps announced in
        # the prompt (e.g. "A maps to Z") -- context includes the prompt for
        # exactly that reason (PLAN.md §1.1 item 1).
        context = f"{record.prompt_text}\n{working}"
        result = best_readable_view(working, context)
        decoded_text = str(result["review_text"])
        changed = decoded_text != working

        new_history = record.texts.history
        if changed:
            new_history = new_history + (TextStep(stage=self.stage, text=decoded_text),)
        new_texts = dataclasses.replace(
            record.texts, decoded=decoded_text, working=decoded_text, history=new_history
        )

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={
                "transform_method": result["transform_method"],
                "transform_confidence": result["transform_confidence"],
            },
            text_out=decoded_text if changed else None,
            error=None,
        )

        return dataclasses.replace(
            record,
            texts=new_texts,
            flags=dataclasses.replace(record.flags, decoding_failed="not_detected"),
            observations=record.observations + (observation,),
        )
