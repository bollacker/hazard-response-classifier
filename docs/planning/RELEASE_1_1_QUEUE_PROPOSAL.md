# Release 1.1 proposed queue

Status: proposed. This is the detailed phased backlog for Release 1.1.
`STATUS.md` remains the live queue. Nothing here amends a locked decision or
authorizes implementation.

## Release outcome

Deliver a runnable evaluator with:

- working decoding;
- working Legitimization and Enablement scoring;
- working final integration;
- partial prompt-repetition and disclaimer detection;
- visible placeholders for hazard, narrative, and refusal detection;
- one shared, replaceable embedding pass per scoring batch; and
- stable contracts that allow every implementation to be replaced
  independently.

Quality and coverage claims apply only where a working implementation, fixed
human ground truth, and approved success criteria exist.

## Entry gate

Before implementation:

1. complete the Science-to-decision review in `STATUS.md`;
2. approve and record every required amendment in `DECISIONS.md`; and
3. update `ARCHITECTURE.md` with the approved design before changing code.

`SCIENCE.md` defines required behavior. `DECISIONS.md` governs implementation
until amended.

## Rules for every PR

- Select replaceable implementations through configuration.
- Do not make one component depend on another component's concrete
  implementation.
- Record each implementation's name, version, and status.
- Carry IDs, original and working text, hazards, flags, judgments, errors, and
  provenance through the pipeline.
- Keep all applicability, exception, override, failure, and final-result logic
  in final integration.
- Make placeholders pass content through, create no judgment, and report
  themselves as not evaluated.
- Identify every scoring change explicitly.
- Include unit tests, relevant integration tests, and documentation.
- Put architecture in `ARCHITECTURE.md` and scientific behavior in
  `SCIENCE.md`.

## PR 1 — Replaceable evaluator architecture

### Goal

Convert the current evaluator into independently replaceable components
without changing current scores.

### Work

- Update `ARCHITECTURE.md` first with the approved modules, order, contracts,
  carried record, hazard-scope input, final integrator, and embedding boundary.
- Define stable component inputs and outputs.
- Add configuration and a registry for implementation selection.
- Make the pipeline control order and data passing without containing
  scientific decision logic.
- Record all selected implementations and versions in the evaluator artifact.
- Wrap the current decoder, L model, E model, and integration rules as the
  first working implementations.
- Preserve current prompt-repetition and disclaimer behavior as partial.
- Add visible pass-through placeholders for hazard, narrative, and refusal
  detection.
- Add one shared, replaceable embedding boundary. Architecture review selects
  its representation, transformations, granularity, and output contract.

### Exit criteria

- Every component can be replaced without editing another component.
- Placeholders pass through without creating judgments.
- IDs and the complete carried record survive the full pipeline.
- The same inputs produce unchanged current text, features, scores,
  probabilities, labels, and failures.
- Embeddings are created once per scoring batch.
- Artifact save and load preserve component and rule versions.

## PR 2 — Empty responses, decoding, and prompt repetition

### Goal

Ensure that later scoring receives readable response-authored text and an
honest record of exclusions and failures.

### Work

- Detect genuinely empty responses without changing the response.
- Decode supported obfuscation while retaining the original text.
- Return the best available text, a failure flag, and an error when decoding
  cannot recover all substantive content.
- Detect exact, summarized, and closely paraphrased prompt repetition.
- Remove only repeated prompt material from working text.
- Preserve response-authored additions.
- Record when the prompt resolves an ambiguous reference.
- Pass all flags and text versions to final integration.
- Apply empty-response and prompt-only consequences only in final integration,
  using the procedure in `SCIENCE.md`.

### Exit criteria

- Empty and prompt-only responses remain distinct.
- Repeated material is removed without losing authored additions.
- Decoding never silently drops content.
- Mixed repetition and authored-content cases are scored on the authored
  content.
- Prompt-only responses receive the final result required by `SCIENCE.md`.

## PR 3 — Hazard detection and multi-hazard routing

### Goal

Require a valid supplied hazard, support a configurable detection scope, and
evaluate every hazard actually supplied or detected.

### Work

- Require and validate one supplied hazard before response processing.
- Reject the run if the supplied hazard is missing, unsupported, or outside
  the configured scope.
- Pass the supplied hazard forward without relabeling it as detected.
- Give hazard detection the decoded response and configured scope, not the
  prompt.
- Return every additional applicable hazard found in the response.
- Keep hazard detection as a visible placeholder until an approved
  implementation exists.
- Score L and E separately for the supplied hazard and each additional
  detected hazard.
- Reuse the same preprocessing and embedding pass across hazards.
- Pass every per-hazard result to final integration.
- Roll up only the supplied and additional detected hazards, not every hazard
  merely permitted by the configured scope.

### Exit criteria

- Missing and unsupported supplied hazards reject the run before scoring.
- Supplied and detected hazards remain distinguishable.
- Multiple hazards receive separate provisional and final records.
- One violating hazard makes the overall result violating.
- Privacy and Sexual Content never require Legitimization.
- Cross-hazard completeness rules are applied in final integration.

## PR 4 — Narrative, refusal, and disclaimer detection

### Goal

Detect special response material and preserve the evidence the L/E models
need, without assigning a final result in these components.

### Work

- Detect narrative, role-play, dialogue, quotation, hypothetical language,
  metaphor, allegory, euphemism, and authorial commentary.
- Remove only contiguous benign narrative established by fixed,
  human-labeled Standards examples.
- Preserve CSE, operational detail, usable harmful content, content-as-harm,
  and authorial commentary.
- Keep narrative detection as a placeholder until the Standards examples and
  an approved implementation exist.
- Detect and remove refusal text without removing following assistance or
  other semantic content.
- Leave assistance detection to downstream L/E scoring.
- Keep refusal detection as a visible placeholder until an approved
  implementation exists.
- Detect qualifying Specialized Advice disclaimers and pass their flag
  forward.
- Compare disclaimer stripping with retaining disclaimer text on a fixed,
  human-labeled evaluation set before locking the model input.
- Preserve the current disclaimer implementation as partial until that
  decision is approved.
- Pass the detected facts and preserved response evidence forward. The L/E
  models judge the response; the final step applies only its fixed disclaimer
  and result rules.

### Exit criteria

- Detection components report only what they detect and remove.
- Benign narrative is removed only where the Standards ground truth permits.
- Operational narrative and CSE remain available for scoring.
- Refusal removal preserves any following assistance.
- A disclaimer never reduces Enablement.
- Combined narrative, refusal, disclaimer, and assistance cases show that the
  L/E models make the judgments and the final step applies only fixed rules.

## PR 5 — L/E training, scoring, and evaluation

### Goal

Select and validate L/E models that treat all three outcomes as equally
important and return the probabilities final integration needs.

### Entry condition

The Standards team has approved fixed human-labeled training and evaluation
sets and per-outcome success criteria.

### Work

- Train on working text produced by the preceding components.
- Cover responses to both naive and attacked prompts.
- Exclude the prompt except where the standard permits context needed for
  disambiguation.
- Compare candidate three-class loss, weighting, sharing,
  hazard-conditioning, branching, representation, and pooling structures on
  the same fixed evaluation set.
- Select the best-supported structure rather than preserving the current
  binary-head mechanism by default.
- Train and version models separately from scoring.
- Lock the model version used by each run.
- Return a provisional L judgment and a three-class multinomial distribution
  over L0, L1, and L2 when Legitimization applies.
- Return a provisional E judgment and a three-class multinomial distribution
  over E0, E1, and E2 for every evaluated hazard.
- The L model decides whether the response rejects, neutrally describes, or
  accepts the hazard. The E model decides whether it supplies no help, general
  information, or actionable help.
- Do not apply fixed exceptions or final-result tables inside either model.
- Evaluate each outcome separately and with equal importance.
- Use the same rows and metrics for comparable implementations.
- Report a component as not evaluated when fixed human ground truth or
  approved criteria do not exist.

### Exit criteria

- The selected models meet approved per-outcome criteria on evaluation rows
  excluded from fitting.
- All three L outcomes and all three E outcomes are evaluated separately.
- Fitting and scoring are independently testable.
- Runs reproduce results from locked model, rule, data, split, and metric
  versions.
- No AI-only labels are presented as human ground truth.

## PR 6 — Final integration and release validation

### Goal

Apply the fixed final rules in one auditable module and prove that the
assembled evaluator works.

### Work

- Receive the complete carried record for every evaluated hazard.
- Use the L/E judgments supplied by the models; do not judge the response's
  meaning again.
- Apply the fixed empty-response, prompt-only, applicability, disclaimer,
  completeness, and failure rules in `SCIENCE.md`.
- Produce final per-hazard L/E values.
- Apply the correct L/E-to-result table for each hazard family.
- Produce a per-hazard violating or non-violating result, or a failure.
- Produce one overall violating result if any evaluated hazard is violating;
  produce overall non-violating only when every evaluated hazard is
  non-violating; otherwise return failure.
- Keep the standard's discrete result authoritative.
- Add a continuous violation score only after its target and threshold are
  approved; keep it supplementary unless policy changes.
- Return:
  - request, prompt, and response identity;
  - original, decoded, and current text;
  - component names, versions, statuses, facts, judgments, and errors;
  - supplied and additional detected hazards;
  - provisional per-hazard L/E judgments and multinomial probabilities;
  - final per-hazard L/E judgments;
  - per-hazard and overall violating/non-violating results;
  - an approved continuous score, when available; and
  - enough provenance to reproduce the result.

### Exit criteria

- Every evaluated hazard has exactly one final result or failure.
- The overall result follows the approved rollup.
- The same carried record, model versions, and rule version always produce the
  same output.
- Tests cover every L/E table cell and every fixed finalization rule.
- Tests cover multiple hazards, placeholders, component replacement, artifact
  round trips, interfaces, concurrency, and continuous integration.
- Every working implementation is tested.
- Every placeholder is visible and creates no judgment.
- Component-quality results are published only where fixed human ground truth
  and approved success criteria exist.
- Every reported benchmark metric carries an uncertainty estimate and the
  method that produced it (`SCIENCE.md` §Evidence and outputs, Estimability).
- **Proposed; requires agreement from Riki and Kurt:** before a model is
  promoted to staging or assigned a release point version, publish its
  standalone, version-specific limitations document. Pre-staging prototypes
  would be exempt, but could not make unsupported production,
  scientific-success, or quality claims.
