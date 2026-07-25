# Critique pass: DECISIONS.md cross-decision consistency review

Date: 2026-07-23
Mechanism: critique (META_PLAN §2)
Scope: `DECISIONS.md` entries D-1 through D-10, reviewed against each other for
mutual consistency. The question is not "is any single decision good?" but "do
two or more locked decisions contradict, silently interact to produce an
unintended/under-specified outcome, or has one decision's stated rationale or
scope been undermined by a later decision without that being flagged?" PLAN.md
prose is referenced only where it is needed to see a decision-to-decision
interaction; findings are about the ledger, not general plan quality (that was
covered in `critiques/2026-07-23-deliverable-1.md`). No fixes proposed.

Ledger check: This pass *is* a check of the ledger against itself, so there is
no separate "does a locked decision already cover this?" step. For each finding
below I name the specific decisions in tension. Reference read: the toy's
`security-evaluator/code/scoring_common.py` (confirmed AUC is computed rank-wise
on centered probabilities via `safe_auc`, and centering is the strictly
monotone `sigmoid(logit(p) - logit(center_mean))`), used only to verify DR-4.

Severity bands: **blocks-correctness** = two locked decisions give
contradictory or leakage-producing instructions that an implementer following
the ledger literally could get wrong; **quality** = a real cross-decision gap
or over-broad scope that should be reconciled but does not by itself corrupt a
result; **nice-to-have** = staleness/wording/waste that is harmless in behavior.

---

## blocks-correctness

### DR-1. D-7's "all training rows" silently readmits the rows D-1 excludes, into the standardization stats
D-1 states holdout-seed rows are "excluded entirely from §3 step 4's fit
(heads, centering means, and threshold grid search)" and stresses they are
"never trained on for the deployed artifact" precisely to prevent "silent
leakage on exactly the number a reader would quote." D-7 states `mean`/`scale`
are "computed unweighted over **all** training rows for the component." These
two are in direct tension: `mean`/`scale` are part of the head (they parameterize
standardization and therefore every score), yet D-7's phrasing is absolute
("all training rows"), not relative to "rows that survived D-1's exclusion."
An implementer reading D-7 literally computes standardization statistics over
the holdout rows too — which means the holdout rows influence the deployed
artifact's scores, contradicting D-1's "excluded entirely" mandate and its
anti-leakage rationale. The asymmetry is made concrete in PLAN §3 step 4's D-7
note, which explicitly qualifies the row set as "(after D-4's empty/echo-only
exclusion)" but says nothing about D-1's holdout exclusion — citing one
exclusion and omitting the other actively invites the reading that holdout rows
*do* feed `mean`/`scale`. Neither D-1 nor D-7 references the other. Per
META_PLAN §1 this is exactly the "two locked decisions conflict" case that must
be surfaced rather than resolved silently.

### DR-2. D-3 (fail closed) and D-4 (empty ⇒ 0) give contradictory predict-time instructions for the same row, with no precedence in the ledger
For a response that is empty/echo-only *and* whose `(component, hazard)` cell is
skipped (D-5) or genuinely unseen, D-4's decision text says the component score
"should be treated as 0" while D-3's decision text says `hrc-predict` "raises an
error" for any cell that was not actually fit. Read from the ledger alone, these
are contradictory outcomes (score 0 vs. hard error) for one input, and neither
entry states which wins. PLAN §6 resolves it (the D-4 check runs *before* the
D-3 lookup, so empty ⇒ 0 and no error is raised "even if the cell would
otherwise be unfit/skipped"), but that resolution lives only in the plan prose,
which META_PLAN §1 says is *not* the source of truth. The chosen precedence also
has a consequence the ledger never states: an empty response carrying a
completely unknown/garbage `hazard` code is silently scored 0 rather than
failing closed, so D-4 punches a response-content-shaped hole in D-3's
fail-closed guarantee — including for hazards the model was never trained on and
cannot validate. Whether that hole is intended (versus firing hazard validation
regardless of response content) is a decision the ledger does not record.

---

## quality

### DR-3. D-4's per-component exclusion silently redefines the row counts that D-2, D-5, and D-7 all consume, and only some of them acknowledge it
D-4 removes empty/echo-only rows from a component's fit. Three other decisions
are defined in terms of counts that D-4 thereby changes, but D-4 does not name
them and they mostly do not name D-4:
- **D-2** hinges on the `n_own >= 5` per-hazard cliff ("5 rows → hazard-specific
  thresholds, 4 rows → pooled fallback"). After D-4, `n_own` is the *post-
  exclusion* own-hazard count, so D-4's exclusions alone can tip a hazard across
  the n=5 cliff or down to zero rows. D-2 never says its counts are net of D-4.
- **D-5** defines "zero-training-row cells"; whether a cell is zero-row is
  determined *after* D-4's exclusion (a cell can be non-empty in the raw CSV yet
  zero-row for Enablement once echo-only rows are dropped). D-5's ledger text
  says "zero training rows" without referencing D-4; only PLAN's D-5 note adds
  "after D-4's exclusion."
- **D-7** (see DR-1) computes `mean`/`scale` over "all training rows," which D-4
  also narrows.
The net effect is that the definition of "the training rows for a component"
lives in D-4 but is consumed by D-2, D-5, and D-7 without a consistent
cross-reference, so a reader of any one of those entries can compute the wrong
row set. This is the under-specification pattern, distinct from DR-1's
holdout/leakage contradiction.

### DR-4. The D-2-amendment / D-10 reframing of §8.2 over-broadly loosens the AUC parity guard, which the gate provably cannot move
D-2's amendment and D-10 declare that "§8.2's headline reference numbers ...
which are downstream of those [threshold] values" move under the monotonicity
gate, and PLAN §8.2 accordingly reframes *all* of the reference numbers
(Legit/Enablement exact, AUC, QWK) as a "historical baseline to stay in the
neighborhood of," not a bit-for-bit target. But the gate (D-10) only changes the
discrete thresholded prediction; it does not touch the head probabilities or
their ranking. AUC in the toy is computed rank-wise on centered probabilities
(`safe_auc(actual, score)`), and centering is strictly monotone, so **AUC is
invariant to both the gate and centering** — only the threshold-dependent
metrics (exact, within-one, QWK, MAE) can move. Treating the AUC reference
numbers (≈0.808, ≈0.783) as merely "in the neighborhood" therefore weakens a
guard that D-10 gives no reason to weaken: AUC parity could and arguably should
remain a tight target while only the threshold-driven metrics are loosened. The
amendment's blanket "downstream of those values" claim is true for exact/QWK but
false for AUC.

### DR-5. Several "Touches" lists are now incomplete given the predict-path and cross-decision interactions
- **D-4's** Touches lists only "`PLAN.md` §3 `build_response_matrix` step;
  feature-building code" — the training side. But D-4's own decision text
  mandates a *predict-time* behavior ("At prediction time, empty and
  prediction-only responses should be treated as 0"), which touches the predict
  path / §6 / `cli/predict.py` and interacts with D-3's ordering (DR-2). None of
  that predict-side surface appears in D-4's Touches.
- **D-3's** Touches lists "§11.1; predict-path code and CLI error handling" but
  omits its hard dependency on D-5's `status` field in `thresholds.json`/§4
  (D-3 cannot fail-closed on skipped cells without it) and the D-4 precedence
  interaction (DR-2).
- **D-7's** Touches omits the D-1/D-4 interaction on which rows define
  `mean`/`scale` (DR-1, DR-3).
These are not fatal, but the Touches field is meant to be the "what else does
this reach" index, and for the predict path in particular it currently
under-reports.

---

## nice-to-have

### DR-6. D-5's "degenerate, 0.5-centered threshold search" is stale under D-10, and implies wasted gated work on never-served cells
D-5 says a zero-row cell "still goes through the toy's existing
constant-probability substitution (which yields a degenerate, 0.5-centered
threshold search)." D-10 then changes the objective *inside*
`optimize_ordinal_thresholds` to the gated rule for *every* candidate pair —
including these degenerate cells — so a skipped cell now runs the gated grid
search to produce a threshold pair that D-3 guarantees is never served. This is
wasted rather than contradictory work, and it is fine functionally, but (a) the
ledger nowhere says skipped cells may bypass the (now gated) search, and (b)
D-5's phrase "0.5-centered threshold search" describes the pre-D-10 mechanism
and was not annotated when D-10 landed. Worth a one-line reconciliation so a
future reader does not treat D-5's description as the current behavior.

### DR-7. Two residual wording inconsistencies inside the ledger
- D-4's decision text says empty and "**prediction-only** responses" are treated
  as 0, where every other reference (D-4's own first sentence, PLAN §3/§6) says
  "**prompt-repetition-only**." "prediction-only" reads as a garble and, taken
  literally, is ambiguous about which rows it covers.
- D-2's Rationale still reads "keep §8.2 parity intact rather than let corrected
  thresholds move the reported numbers," which its *own* later amendment
  directly contradicts (the amendment authorizes the gate to move §8.2's
  numbers). The amendment flags the change, so this is not a silent
  contradiction — but the Rationale sentence was left standing unqualified, so a
  reader who stops at Rationale gets the pre-amendment picture.

---

## Open Questions

1. **DR-1 intent.** Did D-1's "excluded entirely from the fit" deliberately
   *not* extend to the `mean`/`scale` standardization statistics (i.e. was it
   acceptable for holdout rows to influence only standardization, but not
   `coef`/`intercept`/`center_mean`/thresholds)? If holdout rows were
   intentionally allowed to feed `mean`/`scale`, D-7's literal wording is
   correct and DR-1 dissolves. My confidence that the intended reading is
   "holdout rows must not touch `mean`/`scale` either" is ~85%, but the intent
   is a user call, not something I can settle from the ledger.
2. **DR-2 intent.** Is the D-4-before-D-3 precedence (an empty response scores 0
   and suppresses the fail-closed error even for a genuinely unknown hazard
   code) the intended product behavior, or should an unknown/unfit hazard fail
   closed regardless of whether the response happens to be empty? Only you can
   decide which safety posture is wanted; the ledger currently records neither.
3. **DR-4 residual.** I verified against the toy that the reported AUC is
   rank-based on centered probabilities and therefore gate-invariant (~90%
   confident it stays invariant end-to-end). The small residual risk is if the
   production §8.2 harness were to redefine "AUC" over post-threshold
   quantities; if so, AUC could move and the blanket reframing would be
   justified. Worth confirming the harness keeps AUC rank-based.
4. **D-6 / determinism (checked, no finding raised).** I checked D-6's
   "unconditional determinism" against D-2's in-sample fit and D-10's gated grid
   search and found no cross-decision conflict: the grid search is exhaustive
   and deterministic on CPU for a fixed input+seed, and the gate does not
   introduce nondeterminism. The only implicit assumption is deterministic
   tie-breaking when two threshold pairs score equally — D-10 rearranges which
   pairs tie but does not make tie-breaking nondeterministic. Flagging only so
   the "checked and cleared" status is on record; no action implied unless you
   want the tie-break rule pinned explicitly.


## User Responses

**DR-1 intent.** the intended reading is "holdout rows must not touch `mean`/`scale` either"
**DR-2 intent.** in production prediction, unknown hazards should be a hard fail
**DR-4 residual.** Don't worry about it
