#!/usr/bin/env python3
"""Measure the gap between the text the Release 1.1 L/E structure selection
was *fitted* on and the text the evaluator actually *scores*.

**Why this exists.** `docs/SCIENCE.md` §Legitimization Training and
§Enablement Training both require the models be trained "on human ground
truth using working text filtered through the preceding components", and
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5's work list restates it. The structure
selection that produced `DECISIONS.md` D-68 did **not** do this:
`experiments/features.py` embeds the interim frame's raw `response_text`
directly, with no decoding pass and no prompt-repetition removal.
`PREREGISTRATION_LE_STRUCTURE.md` does not mention the input text view
anywhere -- not in §1's data description, not in §2.1's hard constraints,
and not in §7's list of what the selection cannot establish.

So PR 5 must decide what its production models are fitted on
(`PR5_EXECUTION_PLAN.md` §3, gate G-1), and this probe is what answers that
with a measurement instead of an argument. It reports how far the two texts
actually diverge on the 859 interim rows, and -- the sharp end -- how many
rows **exhaust**: rows whose working text goes empty, which at serve time
are decided by `SCIENCE.md` phase B1 and never reach the L/E models at all,
yet still carry human labels a naive fit would train on.

**What this probe is not.** It measures text, not model quality. It cannot
say whether the selected structure would still win on working-text features
-- only re-running the selection could, which
`PREREGISTRATION_LE_STRUCTURE.md` §5 and D-66 reserve for a real evaluation
set under a re-issued pre-registration.

Fidelity: stages 1-7 are applied in `pipeline.STAGE_ORDER` order with §3.1's
exhaustion short-circuit, using the same components the pipeline resolves
through its registry. Stages 8-10 are irrelevant here (they read text, never
write it) and are not run, so no embedding pass, no artifact, and no network
are needed. The whole probe is pure Python.

Run:  python scripts/probe_working_text_delta.py
      python scripts/probe_working_text_delta.py --show-examples
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hazard_classifier.evaluator.components.decoding import Decoder  # noqa: E402
from hazard_classifier.evaluator.components.disclaimer import DisclaimerDetector  # noqa: E402
from hazard_classifier.evaluator.components.empty import EmptyResponseDetector  # noqa: E402
from hazard_classifier.evaluator.components.hazard import HazardDetectionPlaceholder  # noqa: E402
from hazard_classifier.evaluator.components.narrative import (  # noqa: E402
    NarrativeDetectionPlaceholder,
)
from hazard_classifier.evaluator.components.refusal import (  # noqa: E402
    RefusalDetectionPlaceholder,
)
from hazard_classifier.evaluator.components.repetition import (  # noqa: E402
    PromptRepetitionDetector,
)
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews  # noqa: E402
from hazard_classifier.interim_data import load_interim  # noqa: E402

# Stages 1-7 in `pipeline.STAGE_ORDER` order. Stage 8 onward never writes
# text, so the working view is final after stage 7.
_TEXT_STAGES = (
    ("empty_response", EmptyResponseDetector()),
    ("decoding", Decoder()),
    ("hazard_detection", HazardDetectionPlaceholder()),
    ("prompt_repetition", PromptRepetitionDetector()),
    ("narrative_detection", NarrativeDetectionPlaceholder()),
    ("refusal_detection", RefusalDetectionPlaceholder()),
    ("disclaimer_detection", DisclaimerDetector()),
)


def _blank_record(prompt: str, response: str, hazard: str) -> EvaluationRecord:
    return EvaluationRecord(
        request_id="probe",
        prompt_uid="probe",
        response_id="probe",
        prompt_text=prompt,
        response_text=response,
        supplied_hazard=hazard,
        run=None,
        texts=TextViews(original=response, decoded=response, working=response),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=(hazard,),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )


def _run_text_stages(prompt: str, response: str, hazard: str) -> tuple[EvaluationRecord, str]:
    """Apply stages 1-7 with `ARCHITECTURE.md` §3.1's short-circuit, mirroring
    `pipeline.run_pipeline` without needing a run context or registry.
    Returns the final record and the stage that exhausted it (or "").
    """
    record = _blank_record(prompt, response, hazard)
    for stage, component in _TEXT_STAGES:
        record = component.run(record)
        if record.texts.working.strip() == "":
            return dataclasses.replace(record, exhausted_at=stage), stage
    return record, ""


def _percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), q)) if values else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-examples", action="store_true", help="print sample changed rows")
    args = parser.parse_args()

    frame = load_interim()

    changed: list[dict] = []
    exhausted: list[dict] = []
    decode_changed = 0
    repetition_changed = 0
    same_length_changed = 0
    unchanged = 0
    rel_deltas: list[float] = []
    per_hazard: dict[str, dict[str, int]] = {}

    for row in frame.itertuples(index=False):
        response = str(row.response_text)
        prompt = str(row.prompt_text)
        hazard = str(row.hazard)
        record, exhausted_at = _run_text_stages(prompt, response, hazard)
        working = record.texts.working

        bucket = per_hazard.setdefault(hazard, {"rows": 0, "changed": 0, "exhausted": 0})
        bucket["rows"] += 1

        # Decompose the two stages that can actually rewrite text, because
        # they carry very different risk: stage 2 (decoding) normalizes the
        # *same* content, while stage 4 (prompt repetition) **removes**
        # spans. A fit/serve gap made of decoding alone is a different
        # problem from one made of deletions.
        if record.texts.decoded != response:
            decode_changed += 1
        if working != record.texts.decoded:
            repetition_changed += 1
        if working != response and len(working) == len(response):
            same_length_changed += 1

        entry = {
            "prompt_uid": str(row.prompt_uid),
            "hazard": hazard,
            "before": len(response),
            "after": len(working),
            "l": str(row.legitimization_value),
            "e": str(row.enablement_value),
            "response": response,
            "working": working,
        }

        if exhausted_at:
            exhausted.append({**entry, "stage": exhausted_at})
            bucket["exhausted"] += 1

        if working != response:
            changed.append(entry)
            bucket["changed"] += 1
            if len(response):
                rel_deltas.append(100.0 * (len(response) - len(working)) / len(response))
        else:
            unchanged += 1

    total = len(frame)
    print("=" * 88)
    print("Working-text delta probe -- PR5_EXECUTION_PLAN.md gate G-1, slice 0")
    print("=" * 88)
    print(f"interim rows                                      {total}")
    print(f"working text identical to response_text           {unchanged}  ({100*unchanged/total:.1f}%)")
    print(f"working text differs                              {len(changed)}  ({100*len(changed)/total:.1f}%)")
    print(f"  ...decoding (stage 2) rewrote the text          {decode_changed}")
    print(f"  ...repetition removal (stage 4) removed a span  {repetition_changed}")
    print(f"  ...changed but SAME LENGTH (normalization only) {same_length_changed}")
    print(f"rows that EXHAUST (working empties, stages 1-7)   {len(exhausted)}  ({100*len(exhausted)/total:.1f}%)")
    print()
    print("These are the rows the selection was fitted on but the evaluator")
    print("never scores: an exhausted row is decided by SCIENCE.md phase B1 and")
    print("skips stages 8-10 entirely, so no L/E model ever sees it.")
    print()

    if changed:
        print("Character reduction on changed rows (% of original length)")
        print(f"  median   {_percentile(rel_deltas, 50):6.1f}%")
        print(f"  p90      {_percentile(rel_deltas, 90):6.1f}%")
        print(f"  max      {max(rel_deltas):6.1f}%")
        print()

    if exhausted:
        by_stage: dict[str, int] = {}
        for item in exhausted:
            by_stage[item["stage"]] = by_stage.get(item["stage"], 0) + 1
        print("Exhausted rows by stage, and the human labels they carry")
        for stage, count in sorted(by_stage.items(), key=lambda kv: -kv[1]):
            print(f"  {stage:<22} {count}")
        label_counts: dict[str, int] = {}
        for item in exhausted:
            key = f"L{item['l']}/E{item['e']}"
            label_counts[key] = label_counts.get(key, 0) + 1
        print("  labels: " + ", ".join(f"{k}={v}" for k, v in sorted(label_counts.items())))
        print()

    print("Per hazard (rows / changed / exhausted) -- the fit is per hazard, so")
    print("a concentration here matters more than the overall rate")
    for hazard in sorted(per_hazard):
        bucket = per_hazard[hazard]
        print(
            f"  {hazard:<10} {bucket['rows']:>4}   {bucket['changed']:>4}   {bucket['exhausted']:>4}"
        )

    if args.show_examples:
        print()
        print("=" * 88)
        print("Sample changed rows (longest reductions first)")
        print("=" * 88)
        for item in sorted(changed, key=lambda d: d["after"] - d["before"])[:5]:
            print(f"\n[{item['hazard']}] {item['prompt_uid']}  {item['before']} -> {item['after']} chars")
            print(f"  response: {item['response'][:200]!r}")
            print(f"  working:  {item['working'][:200]!r}")


if __name__ == "__main__":
    main()
