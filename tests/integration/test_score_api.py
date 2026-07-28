"""Tests for `HazardResponseClassifier.score` (`VERIFICATION.md` IS-11).

Needs network access on first run (BGE model download, cached after) --
lives in `tests/integration/`, not `tests/unit/`, per `PLAN.md` §8.1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from hazard_classifier.embed import embed_sentences, enablement_keep_mask, pool_response_vector
from hazard_classifier.model import PredictRow, fit
from hazard_classifier.preprocess import decode, segment
from hazard_classifier.preprocess.flags import later_authored_continuation, prompt_repetition_features

_ENABLEMENT_ONLY = frozenset({"prv"})

_TRAIN_ROWS = [
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


def _preprocess_row(prompt_text: str, response_text: str):
    context = "\n\n".join([prompt_text, response_text])
    prompt_readable = str(decode.best_readable_view(prompt_text, prompt_text)["review_text"])
    response_readable = str(decode.best_readable_view(response_text, context)["review_text"])
    segments = segment.segment_text(response_readable, max_chars=420, stride=210)

    texts, is_repeat, has_later = [], [], []
    for piece in segments:
        repetition = prompt_repetition_features(piece.text, prompt_readable, piece.start, piece.end)
        is_prompt_repetition = float(repetition["prompt_repetition_probability"]) >= 0.5
        has_later_authored = is_prompt_repetition and later_authored_continuation(piece.text, prompt_readable)
        texts.append(piece.text)
        is_repeat.append(is_prompt_repetition)
        has_later.append(has_later_authored)
    return texts, is_repeat, has_later


def _fit_real_classifier():
    df = pd.DataFrame(
        _TRAIN_ROWS,
        columns=["hazard", "seed_prompt_id", "prompt_text", "response_text", "enablement_value", "legitimization_value"],
    )
    n = len(df)

    all_texts: list[str] = []
    ranges: list[tuple[int, int]] = []
    is_repeat_all: list[list[bool]] = []
    has_later_all: list[list[bool]] = []
    for prompt_text, response_text in zip(df["prompt_text"], df["response_text"]):
        texts, is_repeat, has_later = _preprocess_row(prompt_text, response_text)
        start = len(all_texts)
        all_texts.extend(texts)
        ranges.append((start, len(all_texts)))
        is_repeat_all.append(is_repeat)
        has_later_all.append(has_later)

    embeddings = embed_sentences(all_texts, allow_download=True)

    enablement_features = np.zeros((n, 768), dtype=np.float32)
    legitimization_features = np.zeros((n, 768), dtype=np.float32)
    enablement_effective = np.zeros(n, dtype=bool)
    legitimization_effective = np.zeros(n, dtype=bool)
    for i, (start, end) in enumerate(ranges):
        row_embeddings = embeddings[start:end]
        keep_all = np.ones(len(row_embeddings), dtype=bool)
        legit_vec, legit_eff = pool_response_vector(row_embeddings, keep_all)
        legitimization_features[i] = legit_vec
        legitimization_effective[i] = legit_eff
        keep_enablement = (
            enablement_keep_mask(np.array(is_repeat_all[i]), np.array(has_later_all[i]))
            if len(row_embeddings)
            else keep_all
        )
        enable_vec, enable_eff = pool_response_vector(row_embeddings, keep_enablement)
        enablement_features[i] = enable_vec
        enablement_effective[i] = enable_eff

    features = {"enablement": enablement_features, "legitimization": legitimization_features}
    effective = {"enablement": enablement_effective, "legitimization": legitimization_effective}
    return fit(df, features, effective, _ENABLEMENT_ONLY)


def test_score_never_raises_on_a_mixed_batch_and_returns_one_result_per_row() -> None:
    classifier = _fit_real_classifier()
    assert classifier.embedding_model_name == "BAAI/bge-base-en-v1.5"

    rows = [
        PredictRow(
            prompt_id="prompt-1",
            response_id="response-1",
            request_id="request-1",
            hazard="hte",
            prompt_text="What should I know about ladder safety at home?",
            response_text="Face the ladder and maintain three points of contact at all times.",
        ),
        PredictRow(
            prompt_id="prompt-2",
            response_id="response-2",
            request_id="request-2",
            hazard="totally_unseen_hazard",
            prompt_text="Anything.",
            response_text="Some response text.",
        ),
        PredictRow(
            prompt_id="prompt-3",
            response_id="response-3",
            request_id="request-3",
            hazard="prv",
            prompt_text="Help me write a private journal entry about my day.",
            response_text="It was a quiet, uneventful day and I mostly rested.",
        ),
    ]

    results = classifier.score(rows, allow_download=True)

    assert [
        (r.prompt_id, r.response_id, r.request_id)
        for r in results
    ] == [
        ("prompt-1", "response-1", "request-1"),
        ("prompt-2", "response-2", "request-2"),
        ("prompt-3", "response-3", "request-3"),
    ]

    hte_result, unseen_result, prv_result = results
    assert hte_result.scored is not None
    assert hte_result.failure_reason is None
    assert hte_result.scored.predicted_label in ("safe", "unsafe")

    assert unseen_result.scored is None
    assert unseen_result.failure_reason == "unseen_hazard"

    assert prv_result.scored is not None
    assert prv_result.scored.legitimization_predicted is None  # D-18: prv is enablement-only


def test_model_is_cached_across_repeated_score_calls() -> None:
    from hazard_classifier.embed import _load_model

    classifier = _fit_real_classifier()
    row = [
        PredictRow(
            prompt_id="prompt-1",
            response_id="response-1",
            request_id="request-1",
            hazard="hte",
            prompt_text="What should I know about ladder safety at home?",
            response_text="Keep the ladder on level ground before climbing.",
        )
    ]

    _load_model.cache_clear()
    classifier.score(row, allow_download=True)
    info_after_first = _load_model.cache_info()
    classifier.score(row, allow_download=True)
    info_after_second = _load_model.cache_info()

    assert info_after_first.misses == 1
    assert info_after_second.hits >= info_after_first.hits + 1
    assert info_after_second.misses == 1  # no new load on the second call
