"""The Release 1.1 evaluator (`docs/ARCHITECTURE.md` §§1-13).

A new package alongside the pre-staging baseline in `hazard_classifier`'s
top-level modules, not a rewrite of it (`ARCHITECTURE.md` §3.2). Built
incrementally per `docs/planning/PR1_EXECUTION_PLAN.md`'s slices; only
`record.py`, `contract.py`, `registry.py`, and `run.py` exist so far
(slice 1A -- pure structure, no pipeline, no components yet).
"""
