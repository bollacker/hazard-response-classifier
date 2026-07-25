# Critique pass: PLAN.md §6 — Deliverable 3 (`hrc-predict`)

Date: 2026-07-23
Mechanism: critique (META_PLAN §2)
Scope: `PLAN.md` §6 ("Deliverable 3 — Production scoring, `hrc-predict`"), the
production scoring path end-to-end. Cross-referenced where §6 depends on them:
§1.1 item 3 (business rules + v1.4 combination), §2.1 (input schema), §2.3
(`HazardResponseClassifier` API), §3 step 4 (the fit whose behavior §6 must
mirror), §4 (artifact format, incl. `rules.json`), §5 (`hrc-evaluate`, which
D-14 makes a consumer of §6's checks), §7 (dependencies), §11 (open questions).
Science/math/engineering problems only; no fixes proposed.

Reference reads (this pass re-read the toy rather than trusting the ledger's
description of it): `security-evaluator/code/scoring_common.py` —
`effective_indices` (L285-315), `aggregate_for_response` (L318-334),
`build_response_matrix` (L342-409), `ordinal_prediction` (L475-484),
`apply_component_business_rules` (L583-621), `v14_overall_score` (L624-634),
`discrete_v14_label` (L637-647), `build_overall_rows` (L1158-1204); and
`run_bge_hazard_weighted_heads.py` — `score_split` (L199-306). Also read this
repo's `src/hazard_classifier/rules.py`, which already implements §6 steps 0-3
as `resolve_component_action`.

## Ledger check against `DECISIONS.md` (D-1 … D-18)

§6 is the most decision-dense section of the plan — D-3, D-4, D-5, D-10, D-11,
D-14 and D-18 all write into it — so this check matters more than usual. Result:
no locked entry resolves any finding below, and two findings (P-C1, P-C4) are
cases where a locked entry and `PLAN.md`'s prose **disagree with each other**,
which META_PLAN §1 says to raise rather than resolve.

Specifically checked and found *not* to cover the findings here:

- **D-3/D-11 (fail-closed + precedence)** fully specify the two hard-fail
  triggers and their order relative to D-4. They say nothing about batch
  semantics (P-C5) or about an *absent* required cell being distinct from a
  `"skipped"` one in `PLAN.md`'s prose (P-C4 — D-11's own text does name the
  absent case; §6's does not).
- **D-4** is the subject of P-C1: its decision text and §3 step 4's prose say
  a prompt-repetition-only response scores 0 for **both** components, §6 step 2
  scopes that to Enablement only, and the toy does neither uniformly.
- **D-10** pins the gated combination rule but is silent on which probabilities
  (raw centered vs. business-rule-adjusted) the gate consumes (P-C3).
- **D-16's amendment** pins the AUC-input value for D-4-scored rows to `0.0`
  and establishes that the toy's metrics run on *post*-business-rule values —
  but it is scoped to `hrc-evaluate`'s AUC, and does not define the
  business-rule stage's position in §6's predict path (P-C3) or the continuous
  component value that feeds §6's own `v14_overall_unsafe_score` output (P-C2).
- **D-18** locks required-components enumeration but names
  `config.ENABLEMENT_ONLY_HAZARDS` (installed code) as the source, while §4
  freezes the hazard→family map into the artifact — the conflict in P-C6.
- **D-5's amendment** makes `"skipped"` a whole-component condition; P-Q4 is
  about the operational consequence of that at deploy time, which no entry
  addresses.
- **D-14** makes `hrc-evaluate` a consumer of §6's checks and is the source of
  the batch/single-row characterization P-C5 contradicts.

Not raised here, deliberately: `hrc-predict` embedding with a BGE revision
other than the artifact's pinned one. That is the same concern as the
Deliverable-2 critique's E-8, which the user answered "Don't worry about it.
Assume a clean slate for each train/evaluate cycle." P-Q2 below covers only
§6's missing CLI/output contract, not revision pinning.

---

## blocks-correctness

### P-C1. `PLAN.md` contradicts itself (and D-4 contradicts the toy) on whether a prompt-repetition-only response scores 0 for Legitimization

Three statements of the same rule disagree:

- **D-4 (locked), decision text:** "At prediction time, empty and
  prompt-repetition-only responses should be treated as 0 in **both** enablement
  and legitimization components."
- **`PLAN.md` §3 step 4**, D-4's paragraph: "an empty or prompt-repetition-only
  response … is scored as `0` directly for that component (**both Enablement and
  Legitimization**)."
- **`PLAN.md` §6 step 2:** "if the response is empty, or is entirely
  prompt-repetition with no authored continuation (**Enablement only**), the
  corresponding component's score is `0`."

Under §6 a repetition-only response is scored 0 for Enablement but goes through
the frozen Legitimization head; under D-4 and §3 it is scored 0 for both. This
is not a wording nit — the two readings produce different `predicted_label`s for
an entire, common class of production input (a response that quotes the prompt
back and adds nothing).

The toy settles which reading is consistent with the fit, and it is §6's.
`effective_indices` (`scoring_common.py` L307) drops a prompt-repetition
sentence **only** when `judgment == "enabling"`; for Legitimization every
sentence, echoed or not, is kept and pooled. So a repetition-only response has a
non-empty Legitimization feature vector, is not dropped by D-4's fit-time
exclusion, and trains a real (possibly nonzero) Legitimization label. Scoring it
`0` at predict time would therefore create exactly the train/serve skew D-4's
own rationale invokes to justify the exclusion in the first place — the fit did
see these rows for Legitimization.

The interference is already propagating: D-16's amendment silently adopts the §6
reading, describing the Legitimization case as "**any empty response**" and
never mentioning repetition-only, while citing D-4's "both components" sentence
as its authority in the same paragraph.

### P-C2. `v14_overall_unsafe_score` is an output field with no definition anywhere in the plan or the ledger, and no defined value for D-4-scored rows

§6's per-row output list includes `v14_overall_unsafe_score`. That name appears
exactly once in `PLAN.md` (§6) and never in `DECISIONS.md`. §1.1 item 3 defines
only the **discrete** v1.4 rule (`unsafe if L == 2 or E == 2`, etc.), which is
the toy's `discrete_v14_label` and which produces `predicted_label` — a
different function from the toy's `v14_overall_score`, whose output this field
is named after. Nothing in the plan states:

- **What it is computed from.** In the toy it is
  `v14_overall_score(hazard, l_score, e_score)` (`scoring_common.py` L624-634)
  over `adjusted_component_continuous` — the business-rule-adjusted mean of the
  adjusted centered nonzero and high probabilities
  (`score_from_centered_probs`, L471-472), per `build_overall_rows` L1179-1183.
  Its per-family formulas (`max(l, e)`; `max(l, (l+e)/2)`; `e`) are stated
  nowhere in `PLAN.md`.
- **That it is derived independently of `predicted_label`.** The toy computes
  the continuous score from adjusted continuous values and the label from
  adjusted *ordinals* — the label is **not** a threshold applied to the score.
  The two can therefore disagree in the direction a consumer would find
  surprising (a high `v14_overall_unsafe_score` on a row labeled `safe`), and
  §6 emits both side by side with no statement of that.
- **Its value for a component scored `0` via D-4.** This is the gap that makes
  it a correctness finding rather than a documentation one. D-16's amendment
  pins only `adjusted_high = 0.0` for these rows, because AUC was all it needed.
  `v14_overall_unsafe_score` consumes the *combined* adjusted continuous value,
  which is undefined for a row that never reached the head. Pure refusals and
  echo-only replies — which D-4's own rationale calls "common in production" —
  are precisely the rows for which §6's headline continuous output has no
  defined value.

### P-C3. §6's ordered step contract has no business-rule stage, so the specialized-advice disclaimer rule is unreachable and the gate's input stage is unstated

§6 gives `hrc-predict` a numbered contract — Step 0 (required components), Step
1 (unseen hazard), Step 2 (D-4 empty/echo), Step 3 (skipped cell), then the D-10
monotonicity gate. Business rules appear only inside a prose arrow at the top of
the section ("frozen heads → business rules → v1.4"), with no step, no ordering
relative to thresholding, and no enumeration. Consequences:

- **The one business rule that still does work has no home.** Of the toy's three
  rules (`apply_component_business_rules`, L583-621): rule 1 (legitimization
  N/A for enablement-only hazards) is subsumed by D-18, which removes the cell
  entirely; rule 3 (prompt-repetition-only zeroes Enablement) is subsumed by
  D-4/Step 2, which scores those rows 0 without reaching the head. Rule 2 —
  a disclaimer sentence zeroes Legitimization for specialized-advice hazards
  (`disclaimer_sentence_count > 0`) — is subsumed by nothing and is the only
  rule with independent effect left. The word "disclaimer" does not occur in §5
  or §6 at all. An implementer following §6's numbered steps literally produces
  a scorer that never applies it, changing `predicted_label` for every
  `spc_*` response that carries a disclaimer.
- **The gate's input stage is unstated.** §6's gate bullet says "once a
  component's nonzero/high probabilities are computed … the ordinal prediction
  is `2` only if both thresholds are crossed," without saying whether those are
  the raw centered probabilities or the business-rule-adjusted ones. The toy
  computes both (`pred` from centered, `adjusted_pred` from adjusted,
  `run_bge_hazard_weighted_heads.py` L257-286) and feeds `adjusted_pred` to the
  final label. D-16's amendment already establishes that the reported metrics
  run on post-rule values, so §5 and §6 are implicitly relying on a stage §6
  never places.

For the *discrete* label the ordering happens to be harmless (the rules set both
probabilities to exactly `0.0`, and the threshold grid's floor is `0.05`, so a
zeroed component predicts `0` under either order) — but that is a coincidence of
the sentinel value, not something the plan states or an implementer can rely on,
and it does **not** hold for the continuous outputs P-C2 is about.

### P-C4. §6 step 3 tests only for `"skipped"`; a required cell that is simply *absent* from the artifact falls through and is served

D-11's decision text requires that "the cell's `thresholds.json` `status` must
be `"fit"`, not `"skipped"` **or absent**" before scoring proceeds — an
allow-list. §6 step 3 states the check as a deny-list instead: "if
`thresholds.json` marks its `status` as `"skipped"` … the row is not scored."
The absent-but-required case (a corrupt or partially-written artifact, a
`heads.npz`/`thresholds.json` disagreement, a hazard whose Enablement cell was
dropped by a bug) is not covered by §6's phrasing, and §6 is the section an
implementer works from.

This has already been implemented the §6 way. In
`src/hazard_classifier/rules.py`, `resolve_component_action` takes
`cell_status: Literal["fit", "skipped"] | None` and its final branches are:

```
    if cell_status == "skipped":
        return "fail_skipped_cell"
    return "serve"
```

so `cell_status=None` on a required component of a known hazard with a
non-empty response returns `"serve"` — the function fails **open** on a missing
cell, which is the one outcome D-3's entire rationale ("no pooled/global head
exists to fall back to") exists to prevent. The 23-test truth table in
`tests/science/test_predict_resolution.py` does not exercise `cell_status=None`
on a required component, so nothing catches it.

### P-C5. §6 makes `hrc-predict` a batch CLI, but D-14's rationale rests on it being a single-row API — so one bad row may abort a whole production batch

§6: "Runs as a batch CLI and exposes a `HazardResponseClassifier.score(rows)`
Python API." D-14's Rationale, justifying why `hrc-evaluate` excludes rather
than aborts: "`hrc-evaluate` is a batch tool and must not let one bad row abort
an entire metrics run, whereas **`hrc-predict` is a single-row production API
where aborting the one bad call is correct**." That premise is false as §6
defines the deliverable.

Under §6's own wording — steps 1 and 3 each say the CLI "raises/reports an
error," which is two different behaviors joined by a slash — a single row with
an unseen hazard code aborts the scoring of every other row in the batch. That
is the identical failure mode D-14 was locked to fix on the evaluate side, left
unfixed on the production side, and it is worse here: the evaluate operator can
re-run, whereas a production batch drops work for rows that were perfectly
scoreable. The three candidate behaviors (abort the batch; emit a per-row error
record and continue; split into a successes file and a failures file) produce
materially different production semantics and §6 picks none of them. The Python
API has the same ambiguity in sharper form: `score(rows)` takes a plural, so
whether it raises or returns per-row error entries determines whether an
embedding service can survive one malformed row.

### P-C6. The required-components lookup has two possible sources of truth — installed config and the frozen artifact — and they can disagree

D-18 defines required components from the hazard's rule family and names
`config.ENABLEMENT_ONLY_HAZARDS` — a module in the installed package — as the
source. §4 specifies `rules.json` in the artifact as "hazard→family map + rule
constants (**frozen from config**)," which exists precisely so an artifact is
self-describing and does not depend on the code version that happens to load
it. §6 never says which one Step 0 consults; in fact `rules.json` is never
mentioned outside §4, so no section of the plan states who reads it at all.

`src/hazard_classifier/rules.py`'s `is_required_component` already picks the
installed-config source (`from hazard_classifier.config import
ENABLEMENT_ONLY_HAZARDS`). If the two ever diverge — a hazard reclassified into
or out of the enablement-only family after an artifact was trained, which is a
config edit, not a retrain — predict-time behavior breaks in both directions:

- hazard **added** to installed `ENABLEMENT_ONLY_HAZARDS` after training: Step 0
  reports Legitimization not-required and never consults a cell the artifact
  actually enumerated and fit, silently dropping a component from the v1.4
  combination and changing labels with no error;
- hazard **removed** from it after training: Step 0 reports Legitimization
  required, Step 3 looks up a `(legitimization, hazard)` cell the artifact never
  enumerated (D-18), and lands on exactly P-C4's undefined absent-cell path.

The same question applies to the family used by the v1.4 combination itself
(`hazard_rule_family` decides `enablement_only` / `specialized_advice` /
default), which drives both the final rule and the disclaimer rule of P-C3.

---

## quality

### P-Q1. §6's pipeline omits the pooling stage, including the Enablement-specific sentence drop that is the only place the two components' features differ

§6's flow is "preprocess → embed → frozen heads → business rules → v1.4." The
step between embedding and the heads — pooling sentence vectors into one
response vector per component — is absent. It is specified only on the training
side (§1.1 item 3, §3 step 4), and the detail that matters most at serve time is
the Enablement carve-out: `effective_indices` drops prompt-repetition sentences
with no authored continuation *before* pooling for Enablement and keeps them for
Legitimization (`scoring_common.py` L307). Mean-pooling all sentences for both
components at predict time yields a feature vector the frozen Enablement head
was never fit against, with no error raised and no test in §8.1/§8.2 that would
notice.

Relatedly, the pooling mode itself (`mean` / `max` / `mean_max`,
`aggregate_for_response` L318-334) is left open in §11 item 2 and is not named
in §4's manifest field list ("versions, hyperparams, embedding model
id+revision, hashes, `holdout_seed_prompt_ids`"). `mean_max` doubles the feature
width, so a predict-time/train-time mismatch is a shape error at best and a
silent garbage score at worst.

### P-Q2. §6 specifies no CLI contract for the one deliverable that is a production interface

§3 gives `hrc-train` a full invocation line with every flag. §6 gives
`hrc-predict` none: no argument for the artifact directory, none for the input
CSV, none for where output goes, no statement of the output format (CSV columns
in the listed order? JSONL? stdout?), and no offline/model-cache surface even
though §7 states the BGE weights are "downloaded from Hugging Face on first use"
and "air-gapped hosts must pre-stage the cache," and §3 step 3 gives `hrc-train`
an `--allow-download` flag for exactly that. Whether `hrc-predict` may reach the
network on a production host is a deployment-relevant behavior that §6 leaves
unstated. §10's phase-5 exit criterion ("scores an unlabeled CSV end-to-end")
cannot be checked against a contract that does not exist.

### P-Q3. Three different things can answer "is this hazard known?", and no normalization step is specified before a fail-closed lookup

At predict time the plan offers three candidate authorities, and §6 never
reconciles them: (a) §2.1's schema module, which "validates columns, **hazard
codes**, and label ranges up front with clear errors"; (b) the artifact's
`rules.json` hazard→family map; (c) the artifact's actually-enumerated cells,
which is what D-3/§6 step 1 tests. A hazard can pass (a) and fail (c) — that is
the normal fail-closed case and is fine — but it can also fail (a) while being
present in (c), if the installed config's hazard list was edited after the
artifact was trained, in which case a scoreable row is rejected by the validator
before the artifact is ever consulted, with an error that blames the input.

Separately, the toy normalizes hazard strings (`normalize_hazard`,
`scoring_common.py` L113, applied in `build_response_matrix` L380 and
`hazard_rule_family` L569) before any lookup. `PLAN.md` never mentions
normalization anywhere. Under D-3's fail-closed contract a trailing space or
case difference in a production CSV's `hazard` column is not a warning — it is
an aborted row (or, per P-C5, possibly an aborted batch).

Related ordering wrinkle: §6 states Step 0 (required components) runs "before
any of steps 1–3," but Step 0 is only well-defined for a hazard whose family is
resolvable. For a genuinely unknown hazard code, the family lookup happens
first, so the error the operator sees depends on whether that lookup raises or
silently returns a default family — neither of which §6 specifies, and neither
of which is the "unknown hazard" error Step 1 was written to produce.

### P-Q4. An artifact with a fully-skipped component is emitted, deployed, and only discovered to be unusable one row at a time

D-5's amendment makes `"skipped"` a whole-component condition: if a component's
nonzero or high label is constant across the entire training corpus, **every**
`(component, hazard)` cell for that component is marked skipped simultaneously.
Combined with §6 step 3, such an artifact hard-fails on every non-empty response
in production — it is not degraded, it is inoperable for its whole traffic.

Nothing in §3 step 5 (serialization), §4 (artifact format), or §6 (artifact
load) gates this: `hrc-train` writes the artifact and exits successfully,
`hrc-predict` loads it successfully, and the condition surfaces only as a
per-row error at serve time. A single manifest-level or load-time check —
"component X is entirely skipped" — is the kind of thing the plan specifies
carefully elsewhere (§4's per-cell `status` field exists for exactly this class
of concern) and does not here.

### P-Q5. §6's predict input requires `seed_prompt_id`, which no predict-path step uses, and §2.1/§6 disagree on the ground-truth columns

§6's input line requires `seed_prompt_id, prompt_uid, prompt_text,
response_text, hazard`. `seed_prompt_id` is used by exactly one thing in the
plan — D-13's held-out/in-sample partitioning in `hrc-evaluate` — which is not
part of the predict path at all. §2.1 describes it as the "grouping key for the
held-out split." For genuinely new production traffic there is often no seed
prompt to identify, so a caller must fabricate a value purely to satisfy §2.1's
up-front column validation, and the natural fabrications (empty string, a UUID
per row) are indistinguishable from real ones downstream.

Also inconsistent: §2.1 says production input is "the same file **minus** the
three ground-truth columns," while §6 says those columns are
"optional/ignored." Whether the validator rejects, ignores, or range-checks a
`legitimization_value` column that happens to be present in a predict CSV is
undefined, and §2.1's validator explicitly does range-check labels.

---

## nice-to-have

### P-N1. `rule_reasons` is an output field with no vocabulary, and two of the toy's three reason strings become unreachable

§6 emits `rule_reasons` per row. The plan never enumerates the possible values.
In the toy they are three fixed strings emitted by
`apply_component_business_rules`:
`legitimization_not_applicable_for_enablement_only_hazard`,
`specialized_advice_disclaimer_reduces_legitimization`, and
`prompt_repetition_only_sets_enablement_zero`. Under D-18 the first can never
fire (the component is absent, not zeroed) and under D-4/Step 2 the third can
never fire (the row short-circuits before the rule stage), so production's
reason vocabulary is a strict subset of the toy's — and a row that the toy would
have annotated now carries an empty `rule_reasons`. Worth pinning explicitly if
§8.2's parity fixture ever compares per-row output, and worth deciding whether
D-4/D-18's short-circuits should emit equivalent reason strings of their own so
the field stays explanatory.

### P-N2. `HazardResponseClassifier.score(rows)` is referenced by §6 but its contract is only sketched in §2.3

§2.3 lists two methods with overlapping purpose — `predict` (→ component
ordinals) and `score` (→ safe/unsafe + reasons) — and §6 names only `score`. Its
input type (list of dicts? a DataFrame? the §2.1 dataclasses `schema.py` is
supposed to produce?), its return type, whether it is the same code path the CLI
uses, and its error contract relative to the CLI's (P-C5) are unspecified. §6
promises it is "designed for repeated calls with the BGE model loaded once,"
which implies the artifact and model live on the instance, but the plan does not
say whether `score` is safe to call concurrently — the natural deployment for a
"embed in a service" API.

---

## Would be settled faster by implementation than analysis (META_PLAN §4)

- **P-C4 is falsifiable right now, in one test.** Adding a
  `cell_status=None` + required + known-hazard + non-empty-response case to the
  existing truth table in `tests/science/test_predict_resolution.py` turns this
  finding from an argument about prose into a red test against
  `resolve_component_action`. That is a ~10-line slice and it settles whether
  the fail-open is real. It does **not** decide what the correct outcome is —
  D-11's text says fail closed, so the fix direction is already locked — only
  whether the code matches it.
- **P-C3's ordering claim ("harmless for the discrete label, not for the
  continuous outputs") is checkable** by implementing the business-rule stage
  against a fixture with one `spc_*` + disclaimer row and one repetition-only
  row, then asserting both orderings agree on `predicted_label` and disagree on
  the continuous value. That is the smallest slice that converts P-C2/P-C3 from
  reasoning into evidence — but it should follow the decisions those findings
  need, not precede them.
- **P-C1 is not settleable by implementation**: both readings run; they simply
  produce different labels. It needs a decision.

---

## Open Questions

1. **P-C1 — which reading of D-4 is correct (locked-entry conflict, user
   call).** Does a prompt-repetition-only (non-empty) response score `0` for
   Legitimization, per D-4's decision text and §3 step 4, or go through the
   frozen Legitimization head, per §6 step 2 and the toy's `effective_indices`?
   My analysis favors §6's reading at ~85% (it is what the toy does, and it is
   the only reading that avoids train/serve skew for rows D-4's fit-time
   exclusion *keeps* in Legitimization's matrix), but it contradicts the literal
   text of a locked decision, so per META_PLAN §1 I will not resolve it.

2. **P-C5 — batch failure semantics (product/safety call).** When
   `hrc-predict` is run over a batch and one row hits a hard-fail condition
   (unseen hazard, or non-empty response on a skipped cell): abort the whole
   run, emit a per-row error record and continue, or split successes and
   failures into separate outputs? D-14 chose exclude-and-continue for
   `hrc-evaluate` on the explicit premise that `hrc-predict` does the opposite;
   confirming or revising that premise is yours.

3. **P-C6 — required-components / rule-family source of truth (design call,
   ~85%).** My reading is that Step 0 and the v1.4 combination should both read
   the artifact's frozen `rules.json`, since §4's whole rationale for freezing
   it is artifact self-description, and that D-18's `config.` reference is
   shorthand for "the config that was frozen into the artifact." Below the 90%
   bar, and D-18's literal text says otherwise, so it needs your call before any
   fix-proposal. (Note: the existing `rules.py` implementation reads installed
   config, so this is also a code change, not only a prose one.)

4. **P-C2 — is a continuous `v14_overall_unsafe_score` wanted in production
   output at all?** If yes, it needs a definition (the toy's per-family
   formulas), a defined value for D-4-scored components, and an explicit
   statement that it is not what `predicted_label` is derived from. If it is
   only vestigial from the toy's research CSV, dropping it from §6's output is
   the smaller change. I have no basis to pick.

5. **P-Q5 — should `seed_prompt_id` be optional for `hrc-predict` input?**
   Making it optional is a schema-validation change affecting §2.1, which is
   shared with train/evaluate where the column *is* load-bearing; leaving it
   required imposes a fabricated value on production callers. Your call on which
   cost is preferable.

**Process note (not a finding).** `STATUS.md`'s Current Phase paragraph states
that two items "remain flagged but not queued (see Awaiting User)" — DI-N1
(D-17's schema has no null/NaN convention for undefined metrics) and the
`metrics.py`/`component_metrics` gap on the `n` field from D-17's DI-Q4
amendment — but the Awaiting User section is empty, so neither is actually
recorded anywhere a future session would find it. Per META_PLAN §5 I did not
reorder or repair the queue myself; flagging it here instead.


## User Answers

 - P-C1: Choose  §6's reading
 - P-C5: split successes and failures into separate outputs
 - P-C6:  Go with "the config was frozen into the artifact." 
 - P-C2: Yes. A continuous v14_overall_unsafe_score wanted in production output. Save it to the side.  It will used for future research.
 - P-Q5: Leave seed_prompt_id required.
 - P-C3: business rule that still does work has no home.:  Add the Rule 2 language to §5 or §6 as needed
 - P-C3: The gate's input stage is unstated: business-rule-adjusted ones.
 - P-C4: When bugs occur (e.g. absent required cell), that whole item should be skipped. 
 - P-Q1: include the pooling state.  Add the missing step.
 - P-Q2:
 - P-Q3: 
 - P-Q4:
 - P-N1: 