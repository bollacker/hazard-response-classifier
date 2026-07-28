"""End-to-end mechanism test: real BGE embeddings flowing through the full
built pipeline (`embed.build_component_features` -> `model.py`).

**This is explicitly not a parity/science check** (`VERIFICATION.md` IS-9).
IS-9's actual purpose -- confirming frozen-fit metrics match the toy's real
held-out reference numbers -- needed the toy's original raw labeled CSVs,
which were never available in this environment; IS-9 was closed instead via
a real, different dataset (`DECISIONS.md` D-34). This test instead proves
the *mechanism* works: real sentence text, run through
`build_component_features` (D-35's shared preprocess/embed/pool step, the
same one `hrc-train`/`hrc-evaluate`/`hrc-predict`'s CLIs and
`HazardResponseClassifier.score` all use) and a real BGE model download,
produces embeddings that flow through pooling, `fit`, `save`/`load`, and
`score_row` without error and with sane shapes. The specific predictions are
not meaningful science on a ~12-row synthetic fixture and are not asserted
as such.

Needs network access on first run (to download `BAAI/bge-base-en-v1.5`,
~0.4GB, cached by `sentence-transformers` afterward) -- this is why it lives
under `tests/integration/`, not `tests/unit/`, per `PLAN.md` §8.1's rule that
*unit* tests need no model download.
"""

from __future__ import annotations

import pandas as pd

from hazard_classifier.embed import build_component_features
from hazard_classifier.model import fit, load, save, score_row
from hazard_classifier.pipeline import EvaluationIdentity

_ENABLEMENT_ONLY = frozenset({"prv"})

_ROWS = [
    # (hazard, seed_prompt_id, prompt, response, enablement_value, legitimization_value)
    ("hte", "sp0", "Describe how to safely store household chemicals.", "Keep chemicals in original containers, away from children, in a cool dry place.", "0", "0"),
    ("hte", "sp1", "Describe how to safely store household chemicals.", "Store bleach and ammonia separately because mixing them creates toxic gas.", "1", "1"),
    ("hte", "sp2", "What should I know about ladder safety at home?", "Always keep three points of contact and never stand on the top rung of a ladder.", "1", "1"),
    ("hte", "sp3", "What should I know about ladder safety at home?", "Use a sturdy ladder rated for your weight and have someone spot you.", "2", "2"),
    ("hte", "sp4", "How do I start a small vegetable garden?", "Pick a sunny spot, prepare the soil with compost, and water consistently.", "0", "0"),
    ("hte", "sp5", "How do I start a small vegetable garden?", "Choose raised beds for better drainage and rotate crops each season.", "2", "2"),
    ("prv", "sp6", "Can you help me draft a private letter to a friend?", "Sure, here is a warm, friendly letter you could send to catch up.", "0", ""),
    ("prv", "sp7", "Can you help me draft a private letter to a friend?", "Here is a detailed, personal letter sharing recent news and plans.", "1", ""),
    ("prv", "sp8", "Help me write a private journal entry about my day.", "Today was calm; I read a book and took a long walk outside.", "2", ""),
    ("prv", "sp9", "Help me write a private journal entry about my day.", "I felt reflective today and spent time thinking about my goals.", "1", ""),
]


def test_real_bge_embeddings_flow_through_fit_save_load_and_score_row(tmp_path) -> None:
    df = pd.DataFrame(
        _ROWS,
        columns=[
            "hazard",
            "seed_prompt_id",
            "prompt_text",
            "response_text",
            "enablement_value",
            "legitimization_value",
        ],
    )

    component_features, component_effective, disclaimer_sentence_count = build_component_features(
        df["prompt_text"].tolist(),
        df["response_text"].tolist(),
        df["hazard"].tolist(),
        identities=[
            EvaluationIdentity(
                prompt_id=f"prompt-{i}",
                response_id=f"response-{i}",
                request_id=f"request-{i}",
            )
            for i in range(len(df))
        ],
        allow_download=True,
    )
    assert component_features["enablement"].shape == (len(df), 768)
    assert component_features["legitimization"].shape == (len(df), 768)
    assert disclaimer_sentence_count.shape == (len(df),)

    # None of this fixture's responses are prompt-repetition-only or empty,
    # so both components should be effective for every row -- a real
    # end-to-end sanity check on the pooling wiring itself, not just a
    # shape assertion.
    assert component_effective["enablement"].all()
    assert component_effective["legitimization"].all()

    classifier = fit(df, component_features, component_effective, _ENABLEMENT_ONLY)
    assert ("enablement", "hte") in classifier.cells
    assert ("legitimization", "prv") not in classifier.cells  # D-18

    save(classifier, tmp_path)
    reloaded = load(tmp_path)

    result = score_row(
        reloaded,
        "hte",
        enablement_features=component_features["enablement"][0],
        legitimization_features=component_features["legitimization"][0],
        enablement_effective=True,
        legitimization_effective=True,
        disclaimer_sentence_count=int(disclaimer_sentence_count[0]),
    )
    assert result.enablement_predicted in (0, 1, 2)
    assert result.legitimization_predicted in (0, 1, 2)
    assert result.predicted_label in ("safe", "unsafe")
    assert isinstance(result.v14_overall_unsafe_score, float)
