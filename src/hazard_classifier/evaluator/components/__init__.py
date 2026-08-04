"""Stage implementations for the Release 1.1 pipeline (`docs/ARCHITECTURE.md`
§7). Each module here imports `record` and `contract` from the parent
`evaluator` package, and the baseline's `preprocess/*` modules it wraps --
never a sibling module in this package (`ARCHITECTURE.md` §3.2's dependency
rule).
"""
