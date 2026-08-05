# Pre-registration: L/E model structure selection

**Required by [`DECISIONS.md` D-59](DECISIONS.md#d-59). Written 2026-08-04,
before any candidate structure has been fitted to any data.** This document
fixes how the winning structure is chosen. Deviating from it later is
permitted and expected — but each deviation is recorded as a dated amendment
at the end of this file, with its reason, rather than made silently.

This is `STATUS.md` queue item 2's first deliverable and PR 5's entry
condition.

---

## 0. What changed, and why this document still matters

D-59 required pre-registration *before the evaluation set exists*, on the
reasoning that a selection rule written after the label distribution is
visible cannot be shown not to have been shaped by it.

The Standards team's dataset is not arriving ([D-63](DECISIONS.md#d-63)).
Release 1.1 instead uses the Jailbreak v1.0 human ground truth already in this
repository, and that data **is** visible — its class balance is quoted in §3
below.

D-59's protection is preserved by a different move
([D-66](DECISIONS.md#d-66)): **the interim evaluation slice is a development
set, not a held-out evaluation set.** It may be looked at, iterated on, and
reused. Nothing measured on it is a benchmark result. When a real, fixed
evaluation set arrives, structure selection is re-run as a *fresh* selection
under a re-issued pre-registration — not confirmed, and not merely re-fitted.

So the honest statement of what this document buys: it prevents the selection
*rule* from being reverse-engineered from candidate *results*, which is still
worth having. It does not claim the rule is uninformed by the data's shape.

---

## 1. Data

| | |
|---|---|
| Source | `data/jb_1.0_1003_ground_truth_items_for_riki_eval__with_seed_prompt_id.csv` |
| SHA-256 | `8fdbec27dbcec27b0d2df4a1e3106f98e3e72d746bd0faa939f57e6a49922ddf` |
| Rows | 859, each carrying human L and E judgments on the 0/1/2 scale |
| Split | `data/interim_split_v1.json`, built by `scripts/build_interim_split.py` |
| Split version | `interim-v1`, seed `20260804`, 25% of prompt groups held out |
| Fit / dev | 635 / 224 rows; 180 prompt groups, 48 held out |

**Grouping is on normalized prompt text, not `seed_prompt_id`**
([D-64](DECISIONS.md#d-64)). The source has 30 seed prompts, each mapping to
exactly one hazard, so a seed-grouped holdout must place an entire hazard on
one side. Prompt-level grouping yields 180 groups, 11 per hazard (26 for
`hte`), with every hazard and every L/E class present on both sides and zero
prompt overlap.

**Residual leakage, stated up front.** Other attack variants derived from the
same seed prompt can appear in fit and dev. Selection is therefore mildly
optimistic about generalization to a genuinely new seed prompt. This is the
cost of making per-hazard evaluation possible at all, and it is the first
thing to re-examine when real data arrives.

**Row eligibility.**

- The **E model** uses all 859 rows.
- The **L model** excludes the enablement-only hazards `prv` and `sxc_prn`
  (96 rows), because `SCIENCE.md` phase A makes final L `N/A` for them. Their
  L labels exist in the source but are unused. L therefore fits on 763 rows.

---

## 2. Candidate space

### 2.1 Hard constraints on what may be a candidate

- **Linear models on frozen embeddings only.** Every candidate reads the
  shared embedding pass (`ARCHITECTURE.md` §8) and fits parameters on top of
  it. No candidate fine-tunes an encoder. This is not a scientific claim that
  fine-tuning would not win — it is a deliberate scope bound that keeps
  [D-37](DECISIONS.md#d-37)'s no-pickle artifact constraint satisfiable by
  `.npz` + JSON for every candidate, and keeps fitting reproducible on CPU.
  A structure requiring a different payload format is out of scope for 1.1
  and would need its own decision.
- **No prompt input** ([D-60](DECISIONS.md#d-60)).
- **No candidate applies a fixed rule from `SCIENCE.md`.** Applicability,
  disclaimer, and result-table logic live in final integration. A candidate
  that encodes phase A, C, or the L/E tables is disqualified, not adjusted.

### 2.2 The reference structure

Selection is an **ablation ladder from a declared reference**, not a grid
search. The reference is the incumbent — the mechanism the baseline already
uses — so that changing it requires evidence:

> **R — two thresholded binary heads**, fitted per `(component, hazard)`,
> mean-pooled BGE representation, no class weighting, decisions made by an
> optimized threshold pair.

R is the incumbent for procedural reasons only. `SCIENCE.md` requires a
three-class multinomial distribution that R structurally cannot produce
(`ARCHITECTURE.md` §4), so R **cannot be the final selection**. It is on the
ladder as the reference point every candidate's improvement is measured
against, and as the thing PR 1's wrapper currently ships as `partial`.

### 2.3 The axes and their levels

One axis varies at a time from R. Levels are fixed here; none may be added
later without an amendment.

| Axis | Levels |
|---|---|
| **Loss** | `L1` multinomial softmax cross-entropy · `L2` ordinal cumulative-link (proportional odds) · `L3` two thresholded binary heads *(= R)* |
| **Weighting** | `W1` none *(= R)* · `W2` inverse-frequency class weights · `W3` explicit equal-per-class weights |
| **Sharing** | `S1` separate L and E models *(= R)* · `S2` one shared parameterization with two output blocks |
| **Hazard-conditioning** | `H1` hazard-agnostic pooled · `H2` hazard appended as a one-hot feature · `H3` per-hazard models *(= R)* |
| **Branching** | `B1` flat three-class · `B2` hierarchical: non-zero, then high-given-non-zero *(= R)* |
| **Representation** | `V1` BGE `bge-base-en-v1.5` *(= R, fixed for 1.1)* |
| **Pooling** | `P1` mean *(= R)* · `P2` max · `P3` mean and max concatenated |

**Representation is deliberately a single level.** Comparing encoders is a
larger undertaking than 224 dev rows can support, and `ARCHITECTURE.md` §8
already makes the provider a configuration swap. Recorded as an axis
*not* exercised in 1.1 rather than silently dropped.

**`H3` (per-hazard) is pre-declared as probably underpowered.** 635 fit rows
across 15 hazards is roughly 42 rows per hazard over three classes. It stays
on the ladder because it is the incumbent's structure and dropping it
unmeasured would beg the question — but a poor `H3` result should be read as
"not enough data per hazard here", not as evidence against hazard
conditioning in general.

### 2.4 Comparison budget

- **Stage 1 — ablation.** From R, vary one axis at a time across all its
  levels: 12 non-reference levels, so **12 fits per target (L, E)**.
- **Stage 2 — finalists.** Combine the best level of each axis into one
  composite; add at most **3** further hand-picked combinations where stage 1
  suggests an interaction. Maximum **4 finalists per target**.
- **Total: at most 16 fitted configurations per target, 32 overall.**

No adaptive expansion. If stage 2 is inconclusive the tie-break in §4 decides;
the budget is not extended, because an extended search on a dev set this size
is how a selection rule becomes a description of noise.

---

## 3. Metric

**Primary: macro-averaged per-class F1** over the three classes, computed
separately for L and for E.

Macro-averaging is the direct encoding of `SCIENCE.md`'s requirement that all
three outcomes be treated as equally important: each class contributes
equally regardless of frequency. A single accuracy figure is not used at any
point, because the class balance —

| | 0 | 1 | 2 |
|---|---|---|---|
| L (763 eligible rows) | 434 | 187 | 142 |
| E (859 rows) | 546 | 170 | 143 |

— means a majority-class predictor scores 0.569 on L and 0.636 on E while
being useless on the classes that matter.

**Guard: worst-class F1 floor.** Any candidate whose lowest per-class F1 is
below **0.25** on either target is disqualified regardless of its macro score.
The floor is pre-set here, and it is a *screening* threshold, not a success
criterion — it exists to reject candidates that solve two classes by
abandoning the third. It is deliberately low; approved success criteria are
the Standards team's to set (`STANDARDS_REQUEST.md` Ask B) and do not exist.

**Coverage: a candidate is measured on the rows it can score.** A
`(target, hazard)` cell that could not be fitted is *unavailable*
([D-45](DECISIONS.md#d-45)), not wrong: its rows are excluded from that
candidate's metric and the resulting coverage is reported with every figure.
A paired comparison uses the rows both candidates scored. Per
[D-67](DECISIONS.md#d-67) this is a recorded departure from `SCIENCE.md`
§Evidence and outputs' same-rows requirement — accepted because the
alternatives are to count an unanswered row as a wrong answer or to let the
weakest candidate shrink the evidence base for every other one. It binds
mainly on `R` and `H3`, the structures with per-hazard cells to lose.

**Uncertainty: cluster bootstrap over prompt groups**, 1000 resamples,
resampling *groups* rather than rows. Rows sharing a prompt group are
correlated, so a row-level bootstrap would understate the interval. This is
also the method `SCIENCE.md` §Evidence and outputs (Estimability) requires be
recorded alongside every reported metric.

---

## 4. Selection rule

Applied per target (L and E independently — they may select different
structures).

1. **Disqualify** any candidate failing §2.1's constraints or the §3
   worst-class floor.
2. **Rank** surviving candidates by macro-F1 on the dev slice.
3. **Require separation.** The top candidate is selected outright only if the
   bootstrap 95% interval for its macro-F1 *difference* against the
   next-ranked candidate excludes zero. Compute the difference per resample —
   paired on the same resampled groups — not by comparing two marginal
   intervals, which is a strictly weaker test.
4. **If separation fails**, the candidates are tied and §4.1 decides.

### 4.1 Tie-break, in order

1. **Higher worst-class F1.** Equal importance is the requirement; the
   candidate that fails least badly on its weakest outcome wins.
2. **Fewer fitted parameters.** Simpler structure at indistinguishable
   performance.
3. **Closer to the reference R.** Do not change the incumbent's structure
   without evidence that the change bought something.

R itself can never be the final selection (§2.2). If R survives to the end,
the selection is the highest-ranked candidate that produces a genuine
three-class distribution, and *that outcome is itself the finding*: it means
the ablation found no structure that beats the incumbent on this data, and it
must be reported that way rather than dressed up as a positive selection.

---

## 5. Touch budget for the real evaluation set

Binding whenever a fixed Standards-team evaluation set arrives.

- Everything in this document runs against the **interim dev slice**. Any
  number produced here is a dev-set number and is **not** a benchmark result,
  not a generalization estimate, and not reportable under `SCIENCE.md`
  §Evidence and outputs.
- The real evaluation set is **untouched until a re-issued pre-registration
  exists**. Selection is then re-run as a fresh selection, not a confirmation
  of this one. The interim winner enters that process as one candidate among
  the others, with no privileged status.
- The real evaluation set is touched **once** for the finally selected
  structure. A second touch invalidates it as a held-out set and requires a
  new split.

---

## 6. What each candidate implies for the artifact

Closing [D-37](DECISIONS.md#d-37)'s open format half and
[D-49](DECISIONS.md#d-49)'s deferred artifact finalization, as D-59 requires.

Every candidate in §2.3 is linear on frozen embeddings, so all of them
serialize identically and `ARCHITECTURE.md` §10's table stands unchanged:

| Candidate family | `model/` payload |
|---|---|
| Multinomial softmax (`L1`) | coefficient matrix `(n_features, 3)` + intercept `(3,)` per target, `.npz`; class order in JSON |
| Ordinal cumulative-link (`L2`) | coefficient vector `(n_features,)` + two ordered cutpoints per target, `.npz` + JSON |
| Two binary heads (`L3` = R) | the baseline's existing `heads.npz` layout, unchanged |
| Shared parameterization (`S2`) | one shared coefficient block plus two output blocks, same `.npz` conventions |
| Hazard-conditioned (`H2`, `H3`) | the above, keyed by hazard in JSON; `H3` additionally records which `(target, hazard)` cells were fit, so [D-45](DECISIONS.md#d-45)'s unfittable-is-unavailable rule still applies |

`thresholds.json` is retained only for `L3`; every other candidate decides by
`argmax` over the distribution and has no thresholds to store.

**No pickle, no `joblib`, for any candidate** — D-37 carries in full.

---

## 7. What this selection cannot establish

For the release's limitations disclosure (D-47 inventory, `README.md`).

- **No approved success criteria exist**, so no candidate can be reported as
  scientifically successful. `SCIENCE.md` §Legitimization Scoring and
  §Enablement Scoring require both models be reported as **not evaluated**
  regardless of what this procedure selects.
- **The labels are out-of-version** ([D-63](DECISIONS.md#d-63)): human
  judgments made against Jailbreak v1.0, used to select a structure for a v1.4
  evaluator. Measured compatibility is 97.2% — applying `SCIENCE.md`'s three
  L/E-to-result tables to the human L/E values reproduces the v1.0
  safe/unsafe label on 835 of 859 rows — with disagreement concentrated in the
  two families whose tables changed between versions (enablement-only 7.3%,
  Specialized Advice 7.4%, default 0.2%).
- **Attacked prompts only** ([D-65](DECISIONS.md#d-65)). Every row is a
  response to an attacked prompt; `SCIENCE.md` §Legitimization Training
  requires naive coverage too, and no modification of this data can supply it.
- **Dev-set numbers only** (§5).
- **Per-hazard claims are weak.** 224 dev rows across 15 hazards is roughly 15
  rows per hazard; per-hazard intervals will be wide and should be reported
  with them, never as point estimates.

---

## 8. Amendments

Each amendment gets a dated entry here stating what changed and why, per D-59.

**2026-08-04 — coverage under D-45 unavailability (§3).** Raised while building
the comparison harness (slice A), which had to decide what a metric does with a
row a candidate could not score. This document fixed the metric and the
uncertainty method but said nothing about coverage, and D-45 guarantees the
case arises: `R` fits per `(component, hazard)` and some cells on 635 fit rows
across fifteen hazards will be unfittable.

**What changed:** §3 gains the coverage rule — excluded, not counted wrong,
with coverage reported and paired comparisons run on the shared rows.

**Why it is recorded rather than decided silently:** it is a departure from
`SCIENCE.md` §Evidence and outputs' requirement that comparable
implementations use the same rows. Kurt's call, locked as
[D-67](DECISIONS.md#d-67), which carries the reasoning and the rejected
alternatives. The gap was in this document, not a deviation from it — but the
value of a pre-registration is that the procedure is complete and visible
before results exist, so filling the gap is logged here the same way a
deviation would be.

**2026-08-04 — the ladder's candidate list is closed (§2.3), restated.** Not a
change; a confirmation made when the harness gained a `MajorityClassBaseline`
diagnostic. §2.3's levels are fixed and none may be added without an
amendment, so that baseline is **not** a ladder candidate, is not eligible for
selection, and does not appear in `stage1.json`'s candidate list. It exists
only as a known-answer anchor for the harness (§3's majority-class figures)
and may be reported as a reference line, clearly marked as not a candidate.
