# Integration/Consistency Audit — D-25–D-28 against the full ledger

Date: 2026-07-25
Mechanism: Integration pass (META_PLAN §2) — a cross-decision consistency
audit, extending the queued D-19–D-24 integration check to the four decisions
locked *after* the last full audit (D-25–D-28), which had received per-decision
ledger checks only.
Scope: All 28 decisions, focused on D-25–D-28 × the rest of the ledger. Primary
concern: the evaluate/serve control flow around hazard authority, ground-truth
validation, and the no-abort guarantee (D-26 × D-27/D-23/D-14/D-22).

Ledger check (per META_PLAN §1): No prior locked decision resolves the D-26 ×
D-27 interaction below. D-26 was locked before D-27; D-26's own full-ledger
check names D-23 but not D-27, and D-27's names D-14/D-22 but not D-26. The last
full consistency audit (STATUS.md, 2026-07-23) covered 24 decisions and predates
all four of these.

---

## Context

The last full `DECISIONS.md` consistency audit stopped at 24 decisions. Since
then D-25 (`hrc-predict` CLI), D-26 (`hrc-evaluate` CLI), D-27 (hazard
normalization / `rules.json` authority), and D-28 (wholly-skipped component)
were locked, and the one queued integration check (STATUS.md Queue) covers only
D-19–D-24. So D-25–D-28 have never been checked against each other or against
the newer entries. This audit fills that gap.

The four focus points of the *queued* D-19–D-24 integration check were also
re-verified in passing and all compose correctly, producing no finding:
(a) D-19's business-rule stage sits between D-4's step-2 short-circuit and
D-10's gate (checked on a specialized-advice + disclaimer + repetition-only
row); (b) D-20's absent-required-cell fail-close vs. D-18's correctly-absent
not-required cell, disambiguated by Step 0 running first; (c) D-22's
split-output vs. D-14's exclude-from-metrics share one predicate and differ only
in consequence; (d) D-21's `0.0` continuous-score value for a D-4 row is sourced
from D-16's sentinel, not D-19's stage. `resolve_component_action`
(`src/hazard_classifier/rules.py`) was also read directly and confirmed to fail
**open** on `cell_status=None`, exactly as D-20's rationale asserts — the ledger
accurately describes the code.

---

## blocks-correctness

### C-1. D-26's blank-ground-truth-label rule conflicts with D-27/D-23 (hazard authority) and D-14/D-22 (no-abort)

D-26 makes a blank `enablement_value`/`legitimization_value`/`is_safe_ground_truth`
on a "not enablement-only" hazard row a hard **error that aborts the whole
`hrc-evaluate` run**, and pins the check as "an evaluate-path `schema.py` rule"
applied up front. Three unrecorded collisions:

1. **Source of the "enablement-only" classification (vs D-23).** The rule must
   decide the row's hazard family. D-23 locks that at evaluate time every
   rule-family lookup reads the artifact's frozen `rules.json`, **not** installed
   config — precisely to stop a hazard reclassified in config after training from
   silently changing serve-time behavior. Implemented as the up-front `schema.py`
   check D-26 describes — where D-27 says the evaluate path has no `rules.json`
   membership resolution — the only available family source is installed config,
   reintroducing exactly D-23's drift: reclassify a hazard's family in config
   after training and a blank `legitimization_value` flips between "error" and
   "tolerated" for the same artifact.

2. **Precedence for a row that is both unseen-hazard and blank-label (vs
   D-14/D-22/D-27).** D-14 locks that an unseen hazard is *excluded from
   measurement and the run continues*; D-27's own ledger check reasserts
   "unknown → excluded, **not abort**." An unseen hazard is absent from
   `rules.json`, so its family is unknowable and it reads as "not
   enablement-only" — so a single unseen-hazard row that *also* carries a blank
   label flips the entire run from D-14's exclude-and-continue to D-26's abort.
   Two locked decisions, opposite outcomes, no recorded precedence.

3. **Timing.** D-26's check is up front in `schema.py`; the unseen-hazard
   determination is per-row against `rules.json` (D-27, §6 Step 0/1). Which runs
   first decides (2), and it is unspecified.

## quality

### Q-1. D-2/D-16's AUC bit-for-bit parity rests on an unverified provenance claim — RESOLVED 2026-07-25 (Finding B)

D-2's amendment keeps AUC as a "bit-for-bit target" for §8.2; D-16's amendment
states as settled fact that §8.2's reference numbers (≈0.808, ≈0.783) "are the
toy's own post-rule `high_auc`." STATUS.md's own E-5 record says this provenance
"is **not confirmed** from the README alone." The toy computes two AUCs per
component; D-16 reports only `high_auc`. If those §8.2 numbers are not `high_auc`,
D-2 (AUC bit-for-bit) and D-16 (high-head only) silently conflict and the parity
harness cannot match. Latent, conditional inconsistency gated on an unverified
fact. **Resolved 2026-07-25** — see User Responses below.

## nice-to-have

### N-1. `seed_prompt_id` output asymmetry in `hrc-predict` — RESOLVED 2026-07-25 (Finding C)

D-25's `failures.csv` carries `seed_prompt_id` while `predictions.csv` omits it,
even though D-24 makes `seed_prompt_id` unused on the predict path (`prompt_uid`
already rejoins either output). Cosmetic, unmotivated asymmetry in the two-file
contract. **Resolved 2026-07-25** — see User Responses below.

---

## User Responses

**C-1 (Finding A):** User accepted the natural reconciliation and directed it be
applied this pass ("accept the natural reconciliation. execute 2 in finding A").
**Q-1 (Finding B):** resolved 2026-07-25 (see the accepted-resolution subsection
below). **N-1 (Finding C):** resolved 2026-07-25 (see the accepted-resolution
subsection below).

### Accepted resolution for C-1 (locked via D-26 amendment, 2026-07-25)

The family-*dependent* part of ground-truth-blank validation moves off the
up-front `schema.py` path and onto the per-row evaluate path, keyed to the
artifact's frozen `rules.json` family map and gated behind D-14's hard-fail
exclusion. Precisely:

1. **Family source = frozen `rules.json` (D-23/D-27), never installed config.**
   Whether a row's hazard is enablement-only is read from the same frozen family
   map every other serve-time lookup uses.
2. **The blank-label error fires only on rows that survive D-14's exclusion.** A
   row that is a D-14 hard-fail — an unseen hazard (absent from `rules.json`), or
   a non-empty response on a `"skipped"`/absent/invalid *required* cell
   (D-5/D-20) — is excluded from measurement and counted (D-14/D-17) *before* its
   ground-truth labels are examined, so a blank label can never promote it to a
   whole-run abort. This preserves D-14/D-22/D-27's "unknown → excluded, never
   abort" guarantee and honors D-26's own rationale ("a measurement tool cannot
   score an unlabeled row against a missing label"): a row that is not measured
   has nothing to score against, so its missing label is moot.
3. **Among surviving (to-be-measured) rows the rule is unchanged:** a known,
   non-enablement-only hazard row with a blank in any of the three ground-truth
   columns is an **error** (D-26's user-accepted "error over exclude" choice,
   open question 2, preserved). A known enablement-only (`prv`/`sxc_prn`) row's
   blank `legitimization_value` is expected and tolerated (D-15/D-18); its
   `enablement_value` and `is_safe_ground_truth` remain required non-blank via
   the base "ground-truth required" rule (§2.1, D-26 `--input`), because those
   are what such a row is measured on.
4. **Family-agnostic structural validation stays up front in `schema.py`:** the
   three ground-truth *columns* must be present, and any *non-blank* value in
   them must be in `{0,1,2}`. These need no artifact and are unchanged. Only the
   family-aware "is this particular blank tolerated?" judgment moves per-row.

This is a re-characterization of D-26's "the blank-label validation is an
evaluate-path schema rule" Touches line — the family-aware half is now a per-row
evaluate check running after Step 0's `rules.json` family resolution and after
D-14's exclusion filter, not an up-front `schema.py` rejection.

**Two precision points beyond the one-line reconciliation, flagged explicitly so
they are visible, not buried:**
- The gate is D-14's *entire* hard-fail filter (unseen **and** skipped/absent
  required cell), not just the unseen-hazard case named in the original
  finding — deferring to D-14 for unseen but not for skipped/absent would be
  internally inconsistent, since D-14 already treats both identically as
  hard-fails. This is the faithful completion of the accepted principle; if the
  user prefers the narrower "unseen-only" gate, that is a one-line change to the
  amendment.
- The base "ground-truth columns required" rule already covers enablement-only
  rows' `enablement_value`/`is_safe_ground_truth` (only `legitimization_value`
  is the documented exception), so there is no column-granularity gap for
  enablement-only rows — checked and dismissed, not a separate finding.

### Full-ledger conflict check on the resolution

- **D-13** (partitioning runs on survivors; an abort, if it fires, precedes it;
  otherwise no effect) — unaffected.
- **D-14** (its exclusion now runs strictly before blank-label validation) —
  reinforced, not contradicted.
- **D-15/D-18** (enablement-only blank-`legitimization` tolerance) — unchanged;
  now mechanized via the same frozen family map.
- **D-20** (absent/invalid required cell is a D-14 hard-fail → excluded → never a
  blank-label abort) — consistent.
- **D-22/D-24** (predict path ignores ground truth entirely) — unaffected.
- **D-23** (family source pinned to frozen `rules.json`) — reinforced.
- **D-27** (`schema.py` still does no `rules.json`-membership rejection on the
  evaluate path; the family-aware blank judgment is per-row) — reinforced.
- **D-28** (a wholly-skipped Legitimization makes non-enablement-only rows D-14
  hard-fails, so evaluating such an artifact never aborts merely because those
  rows carry blank labels) — consistent.

No conflict found.

### Accepted resolution for Q-1 (Finding B) — locked 2026-07-25

Investigation this pass against the committed toy
(`/Users/kurt/git/security-evaluator`) established the provenance **cannot be
read off the repo**: the toy computes two AUCs (`binary_present_auc`, `high_auc`,
`scoring_common.py` L704-705); the README's single "AUC" column is hand-curated;
its source run (`heldout_seed_metrics.csv`) is not committed; git history shows
the column was always just labeled "AUC" (only values changed between runs).
D-16's "these are `high_auc`" claim is therefore unverified and its own argument
circular, and the committed positional evidence (`binary_present_auc` listed
first, grouped with the primary present-vs-absent metrics) leans the *other* way
— not decisively. Both AUCs are gate-invariant, so D-10 is not the risk;
provenance is.

User decisions:
- **Getting the answer:** asking the README author was ruled out — **fall back to
  option 3**: the Phase-4 parity harness settles it empirically by computing
  **both** AUCs from the fixture and matching the reference against both.
- **De-risking the ledger — accept both 4 and 5, applied this pass:**
  - **(4)** D-16's provenance claim is downgraded to a flagged assumption
    ("believed `high_auc`, unverified") and D-2's "AUC bit-for-bit target" is made
    **conditional** on the harness confirming it (a matching note on each). No
    behavior changes.
  - **(5)** The parity check is **decoupled** from D-16's reporting choice: the
    harness reproduces whichever AUC the toy reported (guarding the science),
    while production's user-facing AUC stays `high_auc`-only (D-16). Folded into
    option 3's harness spec.
- **Contingency (named, not triggered):** if the harness finds the reference is
  `binary_present_auc`, reconcile D-16's `high_auc`-only rule with the AUC parity
  target then (widen D-16, replace the reference values, or drop AUC parity).

Applied: `DECISIONS.md` D-16 (provenance note), D-2 (conditional-parity note);
`PLAN.md` §8.2 (harness computes both AUCs and matches against both, decoupled
from production reporting). Empirical confirmation is now a **Phase-4 harness
requirement** tracked in §8.2, not a standalone queue item. Implementation note:
`metrics.py` `component_metrics` computes only `high_auc` today, so the harness
needs a separate `binary_present_auc` path.

### Accepted resolution for N-1 (Finding C) — locked 2026-07-25

Root cause: D-22 said the failures output carries "identifying columns," and
D-25 read that as including `seed_prompt_id` — but `prompt_uid` (the unique
response/row id, §2.1) alone identifies a row, and `seed_prompt_id` is an inert
predict-path passenger (D-24: required only for schema uniformity, consumed by no
predict step, fabricated for label-free traffic).

User decision: **drop `seed_prompt_id` from `failures.csv`** (recommended option
1 over the symmetric alternative of adding it to `predictions.csv`). Rationale:
it aligns the output contract with D-24's inert-passenger semantics, avoids
echoing a meaningless/fabricated value on real traffic, keeps the
lower-blast-radius change (the failures output, not the headline
`predictions.csv`), and loses nothing — `prompt_uid` rejoins either output to the
input, and neither failure reason concerns seed identity.

Applied: `DECISIONS.md` D-25 amendment (`failures.csv` columns →
`prompt_uid, hazard, failure_reason`), cross-reference notes on D-22
("identifying columns" = `prompt_uid`) and D-24 (inert-passenger basis for the
drop); `PLAN.md` §6. `seed_prompt_id` remains a **required input** column (D-24
unchanged); only its appearance in a predict *output* is removed. No consumer
reads it out of `failures.csv`; `hrc-evaluate` writes no failures output at all
(D-14). No behavior change beyond the output column set; no code touched.

---

## Open Questions

None blocking. Finding B (Q-1) is resolved this pass; its *empirical*
confirmation is deferred to the Phase-4 parity harness **by design** (§8.2), not
left open. Finding C (N-1) is also resolved this pass. **All three findings from
this audit (A/C-1, B/Q-1, C/N-1) are now resolved.** The one discretionary point
inside C-1's resolution (the D-14 hard-fail gate is the full filter, not
unseen-only) is stated above and applied; it is called out for visibility rather
than left as a silent choice.
