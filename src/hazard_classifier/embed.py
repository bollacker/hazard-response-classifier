"""BGE sentence embedding + response-vector pooling (`PLAN.md` §1.1 item 2,
§3 step 3, package layout).

Ported from the toy's `run_bge_sentence_embeddings.py` (`load_model`/
`encode_texts`) and `scoring_common.py`'s `aggregate_for_response`/
`effective_indices` (mean pooling; the Enablement-only prompt-repetition
sentence drop, `DECISIONS.md` D-4).

**CPU-only (`DECISIONS.md` D-6):** unlike the toy's `best_torch_device`
(auto-selects `cuda`/`mps`/`cpu`), this module always passes `device="cpu"`
-- no device auto-select, no device parameter exposed to callers.

**Layering note:** this module produces the `component_features`/
`component_effective` inputs `model.py`'s `fit`/`score_row` have expected
since IS-4. `build_component_features` (below, D-35) is the shared
raw-text-to-features step every one of `hrc-train`/`hrc-evaluate`/
`hrc-predict`'s CLIs uses, plus `HazardResponseClassifier.score`'s
production Python API -- one implementation of the preprocess/embed/pool
pipeline, not one per caller. It still does not read CSVs itself; a caller
(a CLI, or `score`) supplies already-loaded `prompt_text`/`response_text`
sequences.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np

from hazard_classifier.config import DEFAULT_EMBEDDING_MODEL_NAME

DEFAULT_MODEL_NAME = DEFAULT_EMBEDDING_MODEL_NAME
DEFAULT_MAX_SEQ_LENGTH = 512
EMBEDDING_DIM = 768


@lru_cache(maxsize=4)
def _load_model(
    model_name: str,
    revision: str | None,
    allow_download: bool,
    cache_folder: str | Path | None,
    max_seq_length: int,
):
    """Loads and caches a `SentenceTransformer` by its exact parameters, so
    repeated `embed_sentences` calls with the same model reuse one loaded
    instance instead of reloading from disk every call -- `PLAN.md` §6's
    `HazardResponseClassifier.score(rows)` API is explicitly "designed for
    repeated calls with the BGE model loaded once."
    """
    # Deferred import: sentence-transformers/torch are heavy and only needed
    # here, not by any other module in the package.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        model_name,
        revision=revision,
        cache_folder=str(cache_folder) if cache_folder else None,
        local_files_only=not allow_download,
        device="cpu",
    )
    model.max_seq_length = max_seq_length
    return model


def embed_sentences(
    sentences: list[str],
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    revision: str | None = None,
    allow_download: bool = False,
    cache_folder: str | Path | None = None,
    batch_size: int = 32,
    max_seq_length: int = DEFAULT_MAX_SEQ_LENGTH,
) -> np.ndarray:
    """Embed `sentences` with BGE, batched (`PLAN.md` §3 step 3). Offline by
    default (`local_files_only=True`) -- `allow_download=True` is required
    to fetch weights not already cached, matching `hrc-train`/`hrc-predict`/
    `hrc-evaluate`'s shared `--allow-download` flag (not yet wired to a CLI).

    Returns an `(0, EMBEDDING_DIM)` array for an empty `sentences` list
    without loading the model at all -- a response with zero segments (the
    input to `pool_response_vector`'s empty case) never needs to pay for
    model load or inference.
    """
    if not sentences:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    model = _load_model(model_name, revision, allow_download, cache_folder, max_seq_length)
    return np.asarray(
        model.encode(
            sentences,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False,
        ),
        dtype=np.float32,
    )


def enablement_keep_mask(
    prompt_repetition_flag: np.ndarray,
    later_authored_continuation: np.ndarray,
) -> np.ndarray:
    """Which of a response's sentence embeddings survive into Enablement's
    pooled vector (`DECISIONS.md` D-4, ported from the toy's
    `effective_indices`, `scoring_common.py` L285-315): a sentence is
    dropped only when it is prompt-repetition-only **and** has no authored
    continuation. Legitimization keeps every sentence -- callers pool
    Legitimization's vector over an all-`True` mask instead of calling this.
    """
    prompt_repetition_flag = np.asarray(prompt_repetition_flag, dtype=bool)
    later_authored_continuation = np.asarray(later_authored_continuation, dtype=bool)
    return ~(prompt_repetition_flag & ~later_authored_continuation)


def pool_response_vector(
    sentence_embeddings: np.ndarray, keep_mask: np.ndarray
) -> tuple[np.ndarray, bool]:
    """Mean-pool the sentences selected by `keep_mask` into one response
    vector (`PLAN.md` §1.1 item 3 / §3 step 4: "mean pooling by default" --
    ported from the toy's `aggregate_for_response`'s `"mean"` mode,
    `scoring_common.py` L318-334; the toy's `"max"`/`"mean_max"` modes are
    not reproduced, since no locked decision names them as the production
    default).

    Returns `(vector, effective)`. `effective` is `False` (`DECISIONS.md`
    D-4) when `keep_mask` selects zero sentences (a genuinely empty
    response, or -- for Enablement -- a prompt-repetition-only one); `vector`
    is then an arbitrary zero placeholder that must never be read downstream
    -- `model.py`'s `fit`/`score_row` both short-circuit on `effective=False`
    before ever touching the feature vector (D-4's `component_effective`
    contract).
    """
    keep_mask = np.asarray(keep_mask, dtype=bool)
    width = sentence_embeddings.shape[1] if sentence_embeddings.shape[0] else EMBEDDING_DIM
    if sentence_embeddings.shape[0] == 0 or not keep_mask.any():
        return np.zeros(width, dtype=np.float32), False
    return sentence_embeddings[keep_mask].mean(axis=0).astype(np.float32), True


def build_component_features(
    prompt_texts: Sequence[str],
    response_texts: Sequence[str],
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    revision: str | None = None,
    allow_download: bool = False,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], np.ndarray]:
    """The shared raw-text-to-features step (`DECISIONS.md` D-35): preprocess
    (`preprocess/*`) -> one batched `embed_sentences` call across every row's
    segments together -> pool per component (`enablement_keep_mask`/
    `pool_response_vector` above). Row-aligned with `prompt_texts`/
    `response_texts`; every `hazard_classifier.model` entry point that needs
    real embeddings (`fit`, `evaluate_rows`, `predict_rows`, `score`) takes
    this function's output shape, so this is the **one** implementation of
    that pipeline, not a copy per caller.

    Returns `(component_features, component_effective, disclaimer_sentence_count)`:
    the first two are `{"enablement": ..., "legitimization": ...}` dicts of
    `(n, EMBEDDING_DIM)` / `(n,)` arrays (`model.py`'s `component_features`/
    `component_effective` contract, D-4); the third is an `(n,)` `int64`
    array counting disclaimer sentences per row (`rules.py`'s
    `apply_legitimization_disclaimer_rule` input, D-19).

    Deferred imports (`preprocess.decode`/`segment`/`flags` are cheap, but
    this keeps the heavy-import boundary in one place, matching
    `embed_sentences`/`_load_model`'s own deferred `sentence_transformers`
    import): none needed here beyond the module-level ones -- `preprocess/*`
    has no heavy dependencies, only `embed_sentences` (called below) does.
    """
    from hazard_classifier.preprocess import decode, segment
    from hazard_classifier.preprocess.flags import (
        disclaimer_label,
        later_authored_continuation,
        prompt_repetition_features,
    )

    n = len(prompt_texts)
    all_segment_texts: list[str] = []
    row_segment_ranges: list[tuple[int, int]] = []
    row_is_repeat: list[list[bool]] = []
    row_has_later: list[list[bool]] = []
    disclaimer_sentence_count = np.zeros(n, dtype=np.int64)

    for i, (prompt_text, response_text) in enumerate(zip(prompt_texts, response_texts)):
        context = "\n\n".join([prompt_text, response_text])
        prompt_readable = str(decode.best_readable_view(prompt_text, prompt_text)["review_text"])
        response_readable = str(decode.best_readable_view(response_text, context)["review_text"])
        segments = segment.segment_text(response_readable, max_chars=420, stride=210)

        start = len(all_segment_texts)
        is_repeat: list[bool] = []
        has_later: list[bool] = []
        disclaimer_count = 0
        for piece in segments:
            all_segment_texts.append(piece.text)
            repetition = prompt_repetition_features(piece.text, prompt_readable, piece.start, piece.end)
            is_prompt_repetition = float(repetition["prompt_repetition_probability"]) >= 0.5
            has_later_authored = is_prompt_repetition and later_authored_continuation(piece.text, prompt_readable)
            is_repeat.append(is_prompt_repetition)
            has_later.append(has_later_authored)
            has_disclaimer, _ = disclaimer_label(piece.text)
            if has_disclaimer:
                disclaimer_count += 1
        row_segment_ranges.append((start, len(all_segment_texts)))
        row_is_repeat.append(is_repeat)
        row_has_later.append(has_later)
        disclaimer_sentence_count[i] = disclaimer_count

    all_embeddings = embed_sentences(
        all_segment_texts, model_name=model_name, revision=revision, allow_download=allow_download
    )

    enablement_features = np.zeros((n, EMBEDDING_DIM), dtype=np.float32)
    legitimization_features = np.zeros((n, EMBEDDING_DIM), dtype=np.float32)
    enablement_effective = np.zeros(n, dtype=bool)
    legitimization_effective = np.zeros(n, dtype=bool)

    for i, (start, end) in enumerate(row_segment_ranges):
        row_embeddings = all_embeddings[start:end]
        keep_all = np.ones(len(row_embeddings), dtype=bool)
        legit_vec, legit_eff = pool_response_vector(row_embeddings, keep_all)
        legitimization_features[i] = legit_vec
        legitimization_effective[i] = legit_eff

        keep_enablement = (
            enablement_keep_mask(np.array(row_is_repeat[i], dtype=bool), np.array(row_has_later[i], dtype=bool))
            if row_embeddings.shape[0]
            else keep_all
        )
        enable_vec, enable_eff = pool_response_vector(row_embeddings, keep_enablement)
        enablement_features[i] = enable_vec
        enablement_effective[i] = enable_eff

    component_features = {"enablement": enablement_features, "legitimization": legitimization_features}
    component_effective = {"enablement": enablement_effective, "legitimization": legitimization_effective}
    return component_features, component_effective, disclaimer_sentence_count
