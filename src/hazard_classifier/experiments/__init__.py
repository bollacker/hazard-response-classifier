"""The L/E structure-selection comparison harness.

**This package is not shipping code.** It implements
`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` Slice A/B/C: the offline
ablation ladder that selects a structure for `RELEASE_1_1_QUEUE_PROPOSAL.md`
PR 5, under the procedure fixed in
`docs/planning/PREREGISTRATION_LE_STRUCTURE.md`. Nothing here is imported by
`hazard_classifier.evaluator` or any production entry point, and it is kept
in its own package for exactly that reason -- so nothing in it is ever
mistaken for part of the evaluator it is choosing a model for.
"""
