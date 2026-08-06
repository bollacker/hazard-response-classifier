"""Stage 2: decoding (`docs/ARCHITECTURE.md` §7, `docs/SCIENCE.md`
§Decoding). Wraps the baseline's `preprocess/decode.py` `best_readable_view`.

**Maturity `partial`, not `working` (`DECISIONS.md` D-51).** The decode path
itself works: `best_readable_view` always returns a result, and its
worst case is the un-decoded text (the raw view is always among its
candidates), so this component never drops content and never empties the
working text. What is **not** built is the other half of `SCIENCE.md`
§Decoding's success criterion — "if it cannot [render all substantive
content], it returns the original and best available text, a
decoding-failure flag, and an error." `_detect_decoding_failure` below is a
deliberate stub that always reports success, so no genuine decoding failure
is currently detectable.

**Why the flag is `not_evaluated` and not `not_detected`.** Writing
`not_detected` would claim this component looked for a decoding failure and
found none. It did not look. `ARCHITECTURE.md` §3.1's three-valued flags
exist precisely to keep "ran and found nothing" distinct from "never
checked", and §6 forbids a placeholder from being silently equivalent to a
negative result — the same rule slice 1B's forcing function pins for the
narrative and refusal placeholders. The stub is scoped to the failure
*check*, so only that flag is `not_evaluated`; the stage itself genuinely
ran and reports `outcome="ran"`.
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar

from hazard_classifier.preprocess.decode import best_readable_view

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord, TextStep


def _detect_decoding_failure(decoded_text: str, view: dict) -> bool:
    """**Stub (`DECISIONS.md` D-51): always reports success.**

    This is the seam a real trigger drops into, kept as a named function
    with the signature that trigger will need rather than left as an absent
    concept, so adding one later is a change in one place with a test
    already pointing at it (`tests/unit/test_evaluator_decoding_stub.py`).

    A real implementation would decide, from `view`'s
    `transform_confidence` / `raw_english_score` / `review_english_score`
    and from inspecting `decoded_text` for residual undecoded material,
    whether substantive content survived the decode. Choosing that rule is
    deferred: it is a threshold on real obfuscated data that this project
    does not have, and a false positive there costs a scored result. Until
    then this returns `False` unconditionally, and the caller records the
    flag as `not_evaluated` rather than claiming a negative finding.
    """
    return False


class Decoder:
    stage: ClassVar[str] = "decoding"
    implementation: ClassVar[str] = "baseline_best_readable_view"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "partial"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        working = record.texts.working
        # `best_readable_view` also considers substitution maps announced in
        # the prompt (e.g. "A maps to Z") -- context includes the prompt for
        # exactly that reason (PLAN.md §1.1 item 1).
        context = f"{record.prompt_text}\n{working}"
        result = best_readable_view(working, context)
        decoded_text = str(result["review_text"])
        changed = decoded_text != working

        failed = _detect_decoding_failure(decoded_text, result)

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
                # Recorded so the stub is visible in the output record, not
                # only in this module's source.
                "failure_check": "stub_always_success",
            },
            text_out=decoded_text if changed else None,
            errors=(),
        )

        return dataclasses.replace(
            record,
            texts=new_texts,
            flags=dataclasses.replace(
                record.flags,
                decoding_failed="detected" if failed else "not_evaluated",
            ),
            observations=record.observations + (observation,),
        )
