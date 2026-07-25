"""Hazard-family sets and hyperparameters shared across preprocessing,
scoring, and metrics."""

SPECIALIZED_ADVICE_HAZARDS = {"spc_ele", "spc_fin", "spc_hlt", "spc_lgl"}
ENABLEMENT_ONLY_HAZARDS = {"prv", "sxc_prn"}

# Ported verbatim from the toy's `scoring_common.DEFAULT_SEED`
# (`run_bge_hazard_weighted_heads.py` L97, `scoring_common.py` L455): the
# `LogisticRegression(random_state=...)` seed for each `BinaryHead` fit
# (`heads.py`), not to be confused with `hrc-train`'s `--holdout-seed-fraction`
# row-selection split (`DECISIONS.md` D-1), a different mechanism entirely.
DEFAULT_SEED = 20260628

# The toy's BGE model (`PLAN.md` §1.1 item 2). Lives here, not in `embed.py`,
# so `model.py` can record it on a fitted `HazardResponseClassifier` (D-23:
# predict-time embeddings must come from the artifact, never a hardcoded
# default) without pulling in `embed.py`'s `sentence-transformers`/`torch`
# dependency for callers who never touch real embeddings (every `model.py`
# test in this project fits/scores against synthetic feature arrays).
DEFAULT_EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
