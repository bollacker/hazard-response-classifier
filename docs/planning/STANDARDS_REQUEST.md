# Standards team request — Release 1.1 ground truth and success criteria

**Status: drafted, not sent.** From Kurt, on his own signature (`STATUS.md`
§Standards team, 2026-08-04). Riki's concurrence review is scheduled
separately and this request is deliberately not coupled to it.

**Why this exists.** Both asks below were recorded on 2026-08-03 as a
"non-blocking outbound request" with no owner and no date. The 2026-08-04
decision-debt sweep found they are the critical path for `STATUS.md` queue
item 2 and for PR 5, and that nobody was driving them. This document is the
escalation: the same two asks, written to be sendable.

**What is not here.** No dated fallback, and no third ask for
benign-narrative examples — both deliberate omissions, recorded with their
reasons in `STATUS.md` §Standards team.

---

## Context for the reader

The hazard-response classifier is being rebuilt for AILuminate Assessment
Standard 1.4 as a ten-stage pipeline. Two of its stages are statistical models
we cannot validate without your ground truth:

- the **Legitimization (L)** model, which judges whether a response rejects
  (L0), neutrally describes (L1), or accepts (L2) the hazard; and
- the **Enablement (E)** model, which judges whether a response supplies no
  help (E0), general information (E1), or actionable help (E2).

The definitions we are building to are the v1.4 taxonomy's, reproduced in
`docs/SCIENCE.md` §Appendix.

Until these asks are answered, `docs/SCIENCE.md` §Evidence and outputs
requires us to report both models as **not evaluated**. Release 1.1 ships on
that basis as a pre-staging prototype and makes no scientific-success or
quality claim. Answering these is what lets a later release make one.

---

## Ask A — fixed, versioned data

**The higher-priority half.** Queue item 2's structure comparison is defined
as running on one fixed evaluation set, so the data unblocks that work even
before any criteria exist.

We need human-labeled training and held-out evaluation sets with:

1. **The split frozen and identified by version or hash.** We record the data,
   split, judgment, and metric versions in every artifact; a moving dataset
   makes a result unreproducible.
2. **Evaluation rows excluded from training.** No overlap, verifiable from the
   identifiers.
3. **Coverage of responses to both naive and attacked prompts**, per
   `docs/SCIENCE.md` §Legitimization Training. This release is the Jailbreak
   release, so attacked-prompt coverage is the point.
4. **Both L and E labels per row**, on the L0/L1/L2 and E0/E1/E2 scales.
5. **The supplied hazard per row**, using the v1.4 hazard codes.

**One question we need answered with the data:** *are per-hazard claims in
scope for Release 1.1?* This determines whether we need enough rows per hazard
to support per-hazard evaluation, or whether pooled claims suffice. We have
been proceeding on the assumption that per-class sparsity will not be a
design driver (`STATUS.md` §Recorded assumption); if the delivered data is
thin in some class, that assumption is what failed.

**Human labels only.** `docs/SCIENCE.md` §Evidence and outputs is explicit
that AI-generated labels are not human ground truth. If any portion is
model-assisted, we need it identified so it can be excluded or reported
separately.

---

## Ask B — per-outcome success criteria

We need approved criteria before we can call either model successful. Four
parts:

1. **A minimum acceptable value for each of L0, L1, L2, E0, E1, E2
   separately** — six numbers, not two.

2. **The metric they are stated on** — per-class recall, precision, or F1.
   *A single accuracy figure cannot satisfy the requirement*, because a rare
   class hides inside it.

3. **Which reading of "equally important" governs.** `docs/SCIENCE.md`
   requires training to treat all three L outcomes and all three E outcomes as
   equally important, and that phrase admits two readings:

   - **Per-class floors** — every outcome must clear its own threshold.
     **This is our recommendation.**
   - **A macro average** across the three outcomes.

   We recommend floors because a macro average can be met while one outcome
   fails badly — which is precisely the failure the equal-importance
   requirement exists to prevent.

4. **The approved uncertainty method.** `docs/SCIENCE.md` §Evidence and
   outputs (Estimability) requires every reported benchmark metric to carry an
   uncertainty estimate alongside the point value, with the method recorded:
   *a bare point estimate is not a reportable benchmark result.*
   **Bootstrap over evaluation rows is the natural default** and is what we
   will use absent direction otherwise. Note that a per-row multinomial
   distribution is a model output, not an uncertainty estimate over a
   benchmark result, and does not satisfy this.

**Dropped from this ask:** a minimum per-class evaluation-set size, under the
sparsity assumption recorded in `STATUS.md`.

---

## What we do with the answers

- **Ask A** unblocks `STATUS.md` queue item 2 — comparing candidate model
  structures on one fixed evaluation set — and PR 5, which trains and locks
  the selected model.
- **Ask B** unblocks the per-outcome evaluation and the `metrics.json` output,
  and is half of what the release's limitations document needs if Release 1.1
  is ever promoted past prototype (`DECISIONS.md` D-47, D-58).

The selection *procedure* is being pre-registered before the data arrives
(`DECISIONS.md` D-59), so the rule for choosing among candidate structures is
fixed while it is provably uninformed by the labels. We will share it.
