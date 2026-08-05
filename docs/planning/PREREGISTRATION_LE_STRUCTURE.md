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
  levels: **10 non-reference levels** (§8's 2026-08-04 amendment; enumerated
  directly from §2.3's table: Loss `{L1,L2}`, Weighting `{W2,W3}`, Sharing
  `{S2}`, Hazard-conditioning `{H1,H2}`, Branching `{B1}`, Representation `{}`,
  Pooling `{P2,P3}`), so **10 fits per target (L, E)**.
- **Stage 2 — finalists.** Combine the best level of each axis into one
  composite; add at most **3** further hand-picked combinations where stage 1
  suggests an interaction. Maximum **4 finalists per target**.
- **Total: at most 14 fitted configurations per target, 28 overall.**

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

**2026-08-04 — stage 1's fit count corrected: 10 non-reference levels, not 12
(§2.4).** Found while starting slice B: §2.3's own table, enumerated directly
(each axis's levels minus its `=R` level; Representation contributes zero
since `V1` is its only level), gives 10, not 12 — Sharing contributes exactly
one (`S2`) and every other axis matches, so the original "12" appears to have
double-counted at least one axis (plausibly treating `S1`/`H3` or `W1`/`B2`'s
own reference levels as if they were additional non-reference ones). This is
the same class of defect §10 lesson 2 names — a summary number that looks
authoritative and was not recomputed from the table it summarizes.

**What changed:** §2.4's stage 1 count (10, not 12; 10 fits/target, not 12)
and the derived total budget (§2.4: 14/target, 28 overall — not 16/32).
**What did not change:** §2.3's table itself, which is correct and was the
source used to recompute this; the specific ten named levels
(`L1, L2, W2, W3, S2, H1, H2, B1, P2, P3`) are unambiguous from it regardless
of the summary sentence's count. No candidate was added or dropped — only the
stated total was wrong.

**Why recorded as an amendment rather than silently corrected:** the § 2.4
budget is quoted as a hard cap in `QUEUE_ITEM_2_EXECUTION_PLAN.md` ("Do not
expand the budget" / "That is the whole budget") and cited from `STATUS.md`;
silently changing a number treated as non-negotiable elsewhere is exactly what
§8's amendment mechanism exists to make visible instead.

**2026-08-05 — §4's closing rule applies to every two-head variant, not
only to `R`; and the pool it ranks over is named.** Found while re-examining
slice C: the first implementation of the selection rule enforced the
worst-class floor and the separation test but **not** §4's closing
requirement that the selection "produces a genuine three-class
distribution". It therefore selected `S2` for the L target — a structure
with exactly the defect §2.2 excludes `R` for.

**Nothing in this document changed.** §2.2, §4's closing sentence, and §6's
payload table (`thresholds.json` retained only for `L3`; "every other
candidate decides by `argmax` over the distribution") already said this
together. What was missing was the reading that ties them: the
distribution property is **structural**, so every level that varies one axis
from `R` while keeping its `L3` two-head loss — `W2`, `W3`, `H1`, `H2`,
`B1`, `P2`, `P3`, and `S2` — inherits `R`'s inability to emit one. Only `L1`
and `L2` qualify. This is recorded because the misreading was easy and
consequential, not because the specification moved.

**One genuine gap is filled.** §4 does not say which pool the closing rule
ranks over when no *finalist* qualifies. Taken as **every candidate
evaluated in this item, stage 1 and stage 2 together**. The alternative —
selecting nothing — would leave PR 5 with no structure despite the ladder
having measured qualifying ones, and §4's own wording ("the highest-ranked
candidate that produces a genuine three-class distribution") reads
naturally over everything ranked, not over the finalist subset alone.

**And a third correction, from the same re-examination: §4 step 3's
comparator is the next-ranked *eligible* candidate, not `R`.** Step 3
requires the top candidate's paired interval "against the next-ranked
candidate" to exclude zero. An earlier implementation tested it against `R`
— but `R` can never be selected, so separating from it decides nothing.
Step 3 exists to establish that the winner is distinguishable from the
runner-up it was actually chosen over, and that runner-up is whatever would
have been selected instead: on the E target, `L1` (macro-F1 0.5289), not
`R`. Measured correctly, the E composite's margin over `L1` is +0.0069 with
a 95% interval of (−0.0233, +0.0393) — comfortably not separated, the same
verdict the wrong comparator happened to give, on the right basis. Where a
target has only one eligible candidate (L), step 3 is **not applicable**
rather than passed or failed, and is recorded as such.

**2026-08-04 — the ladder's candidate list is closed (§2.3), restated.** Not a
change; a confirmation made when the harness gained a `MajorityClassBaseline`
diagnostic. §2.3's levels are fixed and none may be added without an
amendment, so that baseline is **not** a ladder candidate, is not eligible for
selection, and does not appear in `stage1.json`'s candidate list. It exists
only as a known-answer anchor for the harness (§3's majority-class figures)
and may be reported as a reference line, clearly marked as not a candidate.
