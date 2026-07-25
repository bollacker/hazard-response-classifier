# Integration Check — D-19 through D-24 against the full ledger

Date: 2026-07-25
Mechanism: Integration pass (META_PLAN §2) — the queued check over the six
decisions appended in one Deliverable-3 fix-proposal pass (D-19–D-24, plus the
D-4 P-C1 amendment), against the *entire* ledger and against each other for
second-order conflict. The prior fix-proposal did only per-decision checks.
Scope: D-19, D-20, D-21, D-22, D-23, D-24 (+ D-4's P-C1 amendment).

Ledger check: This closes the last formally-open integration item in STATUS.md.
It supersedes the "spot-verified" note left by the 2026-07-25 D-25–D-28
consistency audit with a systematic pass.

---

## Result

**No new conflict found. D-19–D-24 compose with each other and with the whole
ledger.** Two caveats, both already known and tracked (not new findings): the
`resolve_component_action` code currently fails **open** on D-20's absent-cell
case (queued implementation slice), and focus-point (d)'s attribution was stale
in the queue note (corrected below, already reflected in D-21's text).

## Focus points from the queue item

**(a) D-19's business-rule stage composes with D-4's step-2 short-circuit and
D-10's gate.** Traced a specialized-advice hazard (`spc_*`, so *not*
enablement-only → both components required, D-18) with a **prompt-repetition-only**
(non-empty) response carrying a **disclaimer** sentence:
- Step 0 (D-27/D-18): `spc_*` present in `rules.json` → family `specialized_advice`,
  required `{Enablement, Legitimization}`.
- Step 1 (D-3/D-11): known → pass.
- Step 2 (D-4, P-C1 amendment): repetition-only → **Enablement scored 0 directly**
  (echoed sentences dropped, zero effective Enablement sentences; head never
  invoked); **Legitimization not short-circuited** (keeps echoed sentences).
- D-19 stage: runs **only** for Legitimization (the short-circuited Enablement
  never reaches it — consistent with D-21's "the stage never runs for a
  short-circuited component"). Rule 2 (disclaimer, `spc_*` + disclaimer) →
  `adjusted_L` nonzero/high/combined = `0.0`; `rule_reasons +=
  specialized_advice_disclaimer_reduces_legitimization`. Rule 3
  (repetition-only zeroes Enablement) is confirmed **dead/subsumed** — Enablement
  was already zeroed by D-4 step 2, and the stage doesn't run for it.
- D-10 gate: on adjusted probs. `adjusted_E = 0.0` (D-16 sentinel), `adjusted_L =
  0.0` (rule 2), both below the 0.05 grid floor → `E=0, L=0`.
- v1.4 discrete (`specialized_advice`): unsafe iff `L==2` or (`L==1` and `E==2`)
  → **safe**. v14 continuous (D-21): `max(L,(L+E)/2)=0`.
- **Composes cleanly.** The two orderings the queue flagged (D-4 step-2 *before*
  the D-19 stage; the D-19 stage *before* the D-10 gate) both hold, and the
  stage correctly runs per-component only for the non-short-circuited component.

**(b) D-20's absent-required-cell vs D-18's not-required cell — Step 0 first.**
`resolve_component_action`'s first branch is `if not is_required_component(...)
: return "not_required"`. So a not-required `(legitimization, prv/sxc_prn)` cell
(D-18) is resolved at Step 0 and never reaches any cell-status check; a
**required** cell that is absent/invalid (D-20) is only ever evaluated *after*
Step 0 confirms it is required. The two "absent" cases therefore cannot collide.
**Design composes.** *Caveat:* the code's Step-3 branch does not yet fail closed
on `cell_status=None` for a required cell — it returns `"serve"` (fails open),
the exact defect D-20 locks a fix for. That is the queued **IS-A / D-20**
implementation slice; the design here is what that slice makes the code match.

**(c) D-22's split-output vs D-14's exclude-from-metrics — one predicate, two
consequences.** Both call the *same* `resolve_component_action` predicate
(D-3/D-4/D-5/D-11/D-20). A `fail_unseen_hazard`/`fail_skipped_cell` result routes
to `hrc-predict`'s `failures.csv` (D-22) or is excluded-and-counted by
`hrc-evaluate` (D-14) — identical detection, different handling, neither aborts.
D-26's blank-label check (Finding A resolution) runs only on rows that *survive*
D-14's exclusion, so it does not fork or perturb this shared predicate.
**Composes.**

**(d) D-21's continuous value for a D-4 row.** Confirmed defined as `0.0`, but the
queue note's attribution ("depends on D-19 setting adjusted=0.0") is **stale**:
D-19's stage never runs for a D-4-short-circuited component, so the `0.0` comes
from **D-16's amendment sentinel** (D-4-scored component → `adjusted_nonzero =
adjusted_high = 0.0`), and `score_from_centered_probs(0.0, 0.0) = 0.0` feeds the
v14 formula. This corrected attribution is already in D-21's text and the
consistency-audit note — recorded here so the queue note isn't mistaken for the
mechanism. **Dependency holds.**

## Broader cross-checks (D-19–D-24 × whole ledger)

- **D-19 × D-2:** the pre-rule (grid-search) vs post-rule (serve) threshold
  asymmetry is D-19's own documented, accepted inheritance from the toy (D-2). No
  conflict.
- **D-19 × D-16:** the reported AUC is on `adjusted_high`, which D-19 produces.
  Consistent (and both are gate-invariant, so D-10 is untouched).
- **D-20 × D-5 × D-28:** absent-required-cell (defect, D-20) and skipped-cell
  (degeneracy, D-5) share one fail-closed consequence; D-28 surfaces the
  *whole-component* skip at train/load, while D-20 covers a *single* corrupt cell
  — disjoint triggers, same serve-time handling. No conflict.
- **D-21 × D-18:** v14 for the `enablement_only` family reads only `E`, never `L`
  (the toy's `Optional` handling), so a not-required Legitimization contributes
  nothing. Consistent.
- **D-22 × D-25 (Finding C):** `failures.csv` columns (`prompt_uid, hazard,
  failure_reason`) carry the same unseen/skipped-or-absent distinction D-14
  counts. Consistent.
- **D-23 × D-27:** `rules.json` = exactly the trained hazards (D-27), frozen
  (D-23), is the sole serve-time family/required-components source for D-18/D-19.
  D-27 reinforces D-23. *Caveat:* `is_required_component` still imports installed
  config — the queued **IS-C / D-23** slice.
- **D-24 × D-26 (Finding A):** ground-truth optional on predict (D-24) vs required
  on evaluate (D-26) is the intended asymmetry; D-26's blank-label check reads
  the same frozen family map D-24's schema is consistent with. No conflict.

## Open Questions

None. D-19–D-24 are mutually consistent and consistent with the full ledger. The
two caveats above are pre-existing, tracked implementation slices (D-20, D-23),
not ledger conflicts.
