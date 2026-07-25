# Critique pass: PLAN.md §3 — Deliverable 1 (`hrc-train`)

Date: 2026-07-23
Mechanism: critique (META_PLAN §2)
Scope: PLAN.md §3 steps 1–5 and the §4 artifact fields they produce. Science,
math, and engineering implementation problems only. No fixes proposed.
Ledger check: `DECISIONS.md` has no entries, so nothing here contradicts a
locked decision.
Reference read: `/Users/kurt/git/security-evaluator/code/{run_bge_hazard_weighted_heads.py,scoring_common.py}`
and its README metrics table (Legit heldout n=189/40 seeds, Enablement n=201/43;
implies ~950–1000 labeled rows total, ~800 in train, 768 features).

---

## blocks-correctness

### C-1. "Fit on the full training set" is ambiguous against `--holdout-seed-fraction`
§3 step 4 says heads and thresholds are fit on the **full training set**; §3's
last paragraph adds an optional `--holdout-seed-fraction` that "reserves seed
prompts for the eval stage." The plan never says whether the reserved seeds are
excluded from the fit. If they aren't, `hrc-evaluate`'s headline generalization
numbers are computed on rows the frozen artifact trained on — silent leakage,
and exactly the number a reader will quote. If they are, "full training set"
is wrong wording. The manifest records the split ids but the plan does not say
the fit honors them.

### C-2. Thresholds are grid-searched on in-sample probabilities of the same rows the head was fit on
The toy's `optimize_ordinal_thresholds` searches a 91×91 grid on
`centered_*_train`, i.e. `model.predict_proba` of the training rows. With
n≈800 and p=768 at `C=1.0`, in-sample logistic probabilities are near-separated
— the README's own heldout AUC of 0.78–0.81 against what will be a near-1.0
in-sample AUC is direct evidence. The threshold distribution being optimized
over therefore does not resemble the probability distribution seen at predict
time. The toy partly hid this because every fold repeated the same mistake and
was scored out-of-fold; a frozen artifact bakes one such threshold pair in as
*the* production decision boundary, with no fold to average over. The same
objection applies to `center_mean`, which is the weighted mean of those same
in-sample probabilities.

### C-3. Per-hazard threshold tuning can run on as few as 5 rows
`optimize_thresholds_for_hazard` uses own-hazard rows when `n_own >= 5` and ≥2
distinct labels, else falls back to all hazards. Fitting 2 free parameters by
exhaustive search over 8281 grid points against 5 labeled points is not
estimation, it is memorization; and the fallback boundary is a hard cliff (5
rows → hazard-specific thresholds, 4 rows → global). §3 step 4 does not mention
this rule at all, so the plan as written under-specifies the production
decision boundary for any thin hazard.

### C-4. §11.1's "fall back to a global head" is unimplementable under the §4 artifact spec
`heads.npz` and `thresholds.json` are keyed strictly by `(component, hazard)`.
No global/pooled head is enumerated in §3 step 4 or stored in §4, so the
proposed unseen-hazard fallback has nothing to fall back to. Either the training
step must also fit and serialize an unweighted global head per component, or
predict must fail closed on unknown hazards — the plan currently implies a
capability it does not build.

### C-5. Zero-vector features for responses with no effective sentences
`build_response_matrix` substitutes `zero_feature` when a response contributes
no usable sentences (empty response; or, for Enablement, every sentence is
prompt-repetition with no authored continuation). After standardization a zero
vector becomes `-mean/scale`, a coordinated large-magnitude outlier — not a
neutral point. These rows still enter the fit and still shift the
standardization statistics. In production this is not a corner case: pure
refusals and echo-only responses are among the most common inputs. §3 says
nothing about them.

### C-6. Degenerate `(component, hazard)` cells will still be enumerated and serialized
§3 step 4 says "for each component and hazard." For enablement-only hazards
(`prv`, `sxc_prn`) the legitimization label is blank/NA by §2.1, so the
legitimization cell has zero training rows; other cells may have zero positives
on the "high" head. The toy's single-class path substitutes a constant
probability, which after centering yields exactly 0.5 for every row, and the
grid search then picks an arbitrary threshold pair. The plan does not say which
cells are skipped, what is written for a skipped cell, or how predict
distinguishes "skipped" from "fit." A frozen artifact needs that distinction
explicitly; the toy did not because it re-derived everything per run.

---

## quality

### C-7. §3 step 3's device auto-select contradicts §8.1's determinism test
`--device auto` across CPU/CUDA/MPS produces different float results from BGE,
so "same input + seed ⇒ identical artifact parameters and scores" cannot hold
across hosts. Either the determinism claim is per-device (and must say so, and
the manifest must record the device/dtype), or the device must be pinned. Note
this is the same class of host-dependence the plan is already fixing by
bundling the wordlist — the wordlist was fixed, the accelerator was not.

### C-8. Standardization statistics are unspecified as to which rows define them
The toy computes `mean`/`scale` **unweighted** over all training rows including
other-hazard rows, so they are identical across all hazards for a component,
while `center_mean` is **weighted**. `BinaryHead` in §2.3 stores `{mean, scale}`
per head without saying so. Left unstated, an implementer will plausibly
compute them weighted or on own-hazard rows only, silently changing every
score. This needs to be pinned in the plan, not discovered from the toy.

### C-9. `class_weight="balanced"` and the hazard sample weights interact
sklearn multiplies `class_weight` by `sample_weight`, and computes the
"balanced" factors from `y` alone, ignoring `sample_weight`. So under the 0.25
other-hazard weighting the effective class balance is *not* balanced — the
correction is computed on the wrong (unweighted) marginal. Carried over from
the toy, so parity is preserved, but it is a real statistical wart and the plan
presents hazard weighting as a clean "soft per-hazard head," which it isn't.

### C-10. Ordinal decisions from two independently-fit heads are not monotone
Nothing constrains `P(y=2) ≤ P(y≥1)`, and the two thresholds are searched
independently, so the selected grid point can make the "predict 2" region not a
subset of the "predict ≥1" region (`ordinal_prediction` assigns 2 on the high
head alone). The QWK-optimal point on a small sample can land squarely in that
pathological region. Worth an explicit decision to accept or constrain, since
the artifact freezes it.

### C-11. Manifest provenance is under-specified for the determinism claim
§3 step 5 lists "code version" and a hash of the training file. Reproducing an
artifact also requires: bundled-wordlist version/hash, preprocessing/segmenter
version, feature dtype, `--other-hazard-weight`, the seed, the threshold grid
definition, and the resolved holdout seed-prompt id set. §4 also has no
artifact-format schema version, so a future loader cannot detect an old layout.

---

## nice-to-have

### C-12. Redundant per-hazard storage
Because `mean`/`scale` are hazard-independent (C-8) and the pooled feature is
shared across hazards, storing them per `(component, hazard)` in `heads.npz`
duplicates 768×2 floats × n_hazards per component. Harmless at current sizes,
but it invites drift if someone later makes them genuinely per-hazard without
updating consumers.

---

## Would be settled faster by implementation than by more analysis (META_PLAN §4)

- **C-2 and C-3** are empirical, not arguable. Smallest slice that settles them:
  on the existing labeled data with cached embeddings, fit one component's heads
  once on the full train split, then report (a) in-sample vs. held-out AUC for
  the same head, and (b) the QWK obtained on held-out rows by thresholds tuned
  in-sample versus thresholds tuned on out-of-fold predictions of the training
  rows. If the gap is small, C-2/C-3 downgrade to nice-to-have; if it's large,
  the frozen-fit design needs a threshold-calibration step before anything else
  in Deliverable 1 is built. This is one script against existing artifacts.
- **C-5** is settled by counting: how many rows in the current labeled set
  produce zero effective sentences per component. If it's zero, drop it.

---

## Open Questions

1. **C-1 is a genuine ambiguity, not a defect I should resolve.** Whether
   `hrc-train` fits on all rows or excludes reserved holdout seeds is a
   product decision (one artifact used for both deploy and honest eval, versus
   a train-artifact and a separate final full-data artifact). Needs your call
   before any fix-proposal on C-1.
2. **C-2/C-3 versus parity (§8.2).** Correcting the threshold/centering bias
   would deliberately break bit-parity with the toy's reported numbers, which
   §8.2 currently makes a test. Confidence that a correction *improves* held-out
   performance is well below 90% without the measurement above. Risk-appetite
   call: preserve the toy's science exactly and ship a known-biased boundary, or
   allow the numbers to move.
3. **C-10** — whether monotonicity should be enforced is a domain judgment about
   how the two components are meant to relate; I have no basis to pick.
4. **Process note (not a plan issue):** META_PLAN §5 doesn't define where a
   critique pass's findings are persisted, only that STATUS.md tracks items. I
   wrote them to `critiques/YYYY-MM-DD-<scope>.md` and linked it from
   STATUS.md. Confirm that's the convention you want, or tell me where these
   should live.

## User Responses

- For C-1, If --holdout-seed-fraction is greater than zero, then indeed, those held back samples should not be trained on. 
- For C-2/C-3, preserve the toy's science exactly and ship a known-biased boundary.  We should record the liability risk we are taking.
- C-4: Fail on unknown hazards
- C-5: empty and echo responses should excluded from the fit
- C-6: The substitution a constant probability is ok. Skipped cells will not get used.  The predict will will know to skip those enumerated hazards
- C-7: Just use CPU for everything. 
- C-8: Pin the current reality into the plan
- C-9: Mention this problem in the documentation and preserve the parity
- C-10:  Enforce monotonicity
- C-11: Don't worry about versioning for now.
- C-12: Don't worry about this for now




