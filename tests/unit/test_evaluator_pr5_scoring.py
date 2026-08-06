"""PR 5 slice C: stage 9's real three-class scorer
(`docs/planning/PR5_EXECUTION_PLAN.md` §7).

`MultinomialPerHazardScorer` is the first implementation that fills
`Judgment.distribution` (`ARCHITECTURE.md` §4) -- so what these tests hold
are the four things that would fail *quietly* if they broke:

- the distribution is real, sums to 1, and the label is its `argmax`
  (`PREREGISTRATION_LE_STRUCTURE.md` §6: no thresholds to apply);
- an unavailable cell **fails its hazard** rather than inventing a judgment
  or a uniform distribution ([D-45](../../docs/planning/DECISIONS.md#d-45));
- the component applies no fixed rule -- phase C can fix *final* L at L0
  without the *provisional* judgment or its distribution moving; and
- the distribution survives `views.py` into `results.jsonl` as three floats.
  This is the first implementation for which that branch is live at all.

**A well-formed distribution is not evidence of a good one.** Every cell here
returns three tidy numbers summing to 1, including cells fitted on a handful
of synthetic rows. Both models ship *not evaluated*
(`SCIENCE.md` §Legitimization/Enablement Scoring) and D-68 is a null result.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from hazard_classifier.evaluator import views
from hazard_classifier.evaluator.artifact import EvaluatorArtifact, RuleConstants, load_artifact
from hazard_classifier.evaluator.components.decoding import Decoder
from hazard_classifier.evaluator.components.disclaimer import DisclaimerDetector
from hazard_classifier.evaluator.components.embedding import (
    POOLED_VECTOR_FACT,
    EmbeddingComponent,
    MeanPooling,
)
from hazard_classifier.evaluator.components.empty import EmptyResponseDetector
from hazard_classifier.evaluator.components.hazard import HazardDetectionPlaceholder
from hazard_classifier.evaluator.components.integration import FinalIntegrator, RuleSet
from hazard_classifier.evaluator.components.narrative import NarrativeDetectionPlaceholder
from hazard_classifier.evaluator.components.refusal import RefusalDetectionPlaceholder
from hazard_classifier.evaluator.components.repetition import PromptRepetitionDetector
from hazard_classifier.evaluator.components.scoring import (
    BaselineTwoHeadScorer,
    MultinomialPerHazardScorer,
)
from hazard_classifier.evaluator.pipeline import STAGE_ORDER, run_pipeline
from hazard_classifier.evaluator.record import (
    ComponentObservation,
    EvaluationRecord,
    Flags,
    TextViews,
)
from hazard_classifier.evaluator.registry import Registry
from hazard_classifier.evaluator.run import RunConfig, open_run
from hazard_classifier.evaluator.training.multinomial import fit_target_model
from hazard_classifier.evaluator.training.provenance import FitProvenance, LEModels

GOLDEN_1_1 = Path(__file__).resolve().parents[1] / "golden" / "evaluator_1_1" / "artifact"

_DIM = 8
_ENABLEMENT_ONLY = frozenset({"prv", "sxc_prn"})
_SPECIALIZED_ADVICE = frozenset({"spc_fin"})
_RULES = RuleSet(
    enablement_only_hazards=_ENABLEMENT_ONLY, specialized_advice_hazards=_SPECIALIZED_ADVICE
)


class _StubProvider:
    name: ClassVar[str] = "stub"
    version: ClassVar[str] = "1"

    def embed(self, texts) -> np.ndarray:
        if not texts:
            return np.zeros((0, _DIM), dtype=np.float32)
        return np.vstack(
            [np.full(_DIM, (hash(text) % 1000) / 1000.0, dtype=np.float32) for text in texts]
        )


def _provenance() -> FitProvenance:
    return FitProvenance(
        source_path="synthetic",
        source_sha256="0" * 64,
        split_path="none",
        split_version="none",
        split_half="all",
        split_role="fixture",
        text_view="working",
        embedding_provider="stub",
        embedding_provider_version="1",
        embedding_model_name=None,
        embedding_model_revision=None,
        pooling="mean",
        seed=20260628,
        estimator={},
        components=(),
        n_feature_rows=0,
        exhausted_excluded=(),
    )


@pytest.fixture(scope="module")
def artifact() -> EvaluatorArtifact:
    """Four hazards, each a distinct case stage 9 must handle:

    - `hte`      default family, both targets fitted;
    - `spc_fin`  specialized advice, both targets fitted (phase C's case);
    - `prv`      enablement-only, so L is *not required* (`SCIENCE.md` phase A);
    - `vcr`      E fitted, L **unavailable** -- single-class L rows, D-45.

    `ipv` is deliberately absent entirely: a hazard the artifact never saw.
    """
    rng = np.random.default_rng(20260805)
    n = 45
    hazards = np.array(sum(([h] * n for h in ("hte", "spc_fin", "prv", "vcr")), []))

    y_e = np.tile(np.array([0, 1, 2] * (n // 3), dtype=np.int64), 4)
    X = rng.normal(size=(len(hazards), _DIM))
    X[:, 0] += np.where(y_e == 0, -2.0, np.where(y_e == 1, 0.0, 2.0))

    l_eligible = ~np.isin(hazards, list(_ENABLEMENT_ONLY))
    y_l = y_e.copy()
    y_l[hazards == "vcr"] = 0  # single-class -> D-45 unavailable

    return EvaluatorArtifact(
        artifact_id="unit-fixture",
        artifact_version="7",
        created_at="2026-08-05T00:00:00+00:00",
        models=LEModels(
            legitimization=fit_target_model(
                X[l_eligible], y_l[l_eligible], hazards[l_eligible], target="legitimization"
            ),
            enablement=fit_target_model(X, y_e, hazards, target="enablement"),
            provenance=_provenance(),
        ),
        rules=RuleConstants(
            enablement_only_hazards=_ENABLEMENT_ONLY,
            specialized_advice_hazards=_SPECIALIZED_ADVICE,
            supported_hazards=frozenset({"hte", "spc_fin", "prv", "vcr"}),
            hazard_family={
                "hte": "default",
                "spc_fin": "specialized_advice",
                "prv": "enablement_only",
                "vcr": "default",
            },
            rule_version="1",
        ),
        manifest={},
    )


def _record(*, hazard="hte", evaluated=None, pooled="present", flags=None) -> EvaluationRecord:
    """A record as it reaches stage 9: stage 8's observation already on it,
    since stages communicate through the record (§6).
    """
    observations: tuple[ComponentObservation, ...] = ()
    if pooled is not None:
        vector = (
            np.full(_DIM, 0.4, dtype=np.float32)
            if isinstance(pooled, str)
            else np.asarray(pooled)
        )
        observations = (
            ComponentObservation(
                stage="embedding",
                implementation="shared_single_pass",
                version="1",
                maturity="working",
                outcome="ran",
                facts={POOLED_VECTOR_FACT: vector},
                text_out=None,
                errors=(),
            ),
        )

    return EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="a prompt",
        response_text="a response with real authored content",
        supplied_hazard=hazard,
        run=None,
        texts=TextViews(original="r", decoded="r", working="a response"),
        exhausted_at=None,
        observations=observations,
        detected_hazards=(),
        evaluated_hazards=tuple(evaluated or (hazard,)),
        flags=flags or Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )


# --- The distribution is real, and the label is its argmax ----------------


def test_the_component_declares_itself_working_with_its_own_implementation_id(artifact):
    scorer = MultinomialPerHazardScorer(artifact)
    assert scorer.stage == "scoring"
    assert scorer.implementation == "multinomial_per_hazard"
    assert scorer.maturity == "working"
    # Registered alongside, not substituted for, the baseline (§6 keys on
    # (stage, implementation_id)).
    assert scorer.implementation != BaselineTwoHeadScorer.implementation
    assert scorer.stage == BaselineTwoHeadScorer.stage


def test_both_targets_emit_a_well_formed_three_class_distribution(artifact):
    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="hte"))
    judgment = scored.per_hazard["hte"]

    for provisional in (judgment.provisional_l, judgment.provisional_e):
        assert provisional is not None
        assert provisional.distribution is not None
        assert len(provisional.distribution) == 3
        assert all(isinstance(p, float) for p in provisional.distribution)
        assert all(p >= 0.0 for p in provisional.distribution)
        assert sum(provisional.distribution) == pytest.approx(1.0)


def test_the_label_is_the_argmax_of_the_distribution(artifact):
    """§6: every non-`L3` candidate decides by argmax. There are no
    thresholds in this artifact to apply, and none are applied.
    """
    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="hte"))
    judgment = scored.per_hazard["hte"]

    for provisional, prefix in ((judgment.provisional_l, "L"), (judgment.provisional_e, "E")):
        expected = f"{prefix}{int(np.argmax(provisional.distribution))}"
        assert provisional.label == expected


def test_the_model_version_names_the_artifact_not_the_component(artifact):
    """`SCIENCE.md` requires models "trained and versioned separately from
    scoring" and every run to use "an existing, locked model version". The
    component's own implementation and version are on the observation.
    """
    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="hte"))

    assert scored.per_hazard["hte"].provisional_e.model_version == "unit-fixture:7"
    observation = scored.observations[-1]
    assert observation.implementation == "multinomial_per_hazard"
    assert observation.version == "1"


def test_scoring_is_deterministic_for_the_same_record(artifact):
    scorer = MultinomialPerHazardScorer(artifact)
    first = scorer.run(_record(hazard="hte")).per_hazard["hte"]
    second = scorer.run(_record(hazard="hte")).per_hazard["hte"]
    assert first.provisional_e.distribution == second.provisional_e.distribution


# --- D-45: an unavailable cell fails its hazard ---------------------------


def test_an_unavailable_cell_fails_its_hazard_rather_than_inventing_a_judgment(artifact):
    """`vcr`'s Legitimization cell was single-class at fit time, so D-45
    leaves it unavailable. Never a substituted judgment, never a uniform
    distribution.
    """
    assert "vcr" in artifact.models.legitimization.unavailable_hazards

    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="vcr"))
    judgment = scored.per_hazard["vcr"]

    assert judgment.provisional_l is None
    # Enablement is unaffected: one target's unavailability is not the other's.
    assert judgment.provisional_e is not None
    assert judgment.provisional_e.distribution is not None

    observation = scored.observations[-1]
    assert observation.outcome == "error"
    assert [error.stage for error in observation.errors] == ["scoring"]
    assert observation.errors[0].hazard == "vcr"
    assert "legitimization" in observation.errors[0].message


def test_a_hazard_the_artifact_never_saw_fails_closed(artifact):
    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="ipv"))
    judgment = scored.per_hazard["ipv"]

    assert judgment.provisional_l is None
    assert judgment.provisional_e is None
    # Both targets failed, and D-76 means both are recorded rather than the
    # Legitimization one alone.
    errors = scored.observations[-1].errors
    assert len(errors) == 2
    assert {error.hazard for error in errors} == {"ipv"}
    assert all("fail_unseen_hazard" in error.message for error in errors)


def test_a_missing_pooled_vector_fails_rather_than_scoring_zeros(artifact):
    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="hte", pooled=None))
    judgment = scored.per_hazard["hte"]

    assert judgment.provisional_l is None
    assert judgment.provisional_e is None
    assert all("no pooled embedding" in error.message for error in scored.observations[-1].errors)


# --- Applicability is reported, never decided -----------------------------


def test_an_enablement_only_hazard_gets_no_legitimization_and_no_error(artifact):
    """`SCIENCE.md` phase A. L is *not required* for `prv` -- which is not
    the same as failing, so nothing is recorded as an error.
    """
    scored = MultinomialPerHazardScorer(artifact).run(_record(hazard="prv"))
    judgment = scored.per_hazard["prv"]

    assert judgment.legitimization_applies is False
    assert judgment.provisional_l is None
    assert judgment.provisional_e is not None
    assert scored.observations[-1].outcome == "ran"
    assert scored.observations[-1].errors == ()


def test_every_evaluated_hazard_gets_its_own_judgment(artifact):
    scored = MultinomialPerHazardScorer(artifact).run(
        _record(hazard="hte", evaluated=("hte", "prv", "spc_fin"))
    )
    assert set(scored.per_hazard) == {"hte", "prv", "spc_fin"}
    assert scored.per_hazard["hte"].source == "supplied"
    assert scored.per_hazard["prv"].source == "detected"


def test_the_scorer_applies_no_fixed_rule_from_a_flag(artifact):
    """A qualifying Specialized Advice disclaimer is phase C's business. It
    must not touch what the model judged.
    """
    scorer = MultinomialPerHazardScorer(artifact)
    plain = scorer.run(_record(hazard="spc_fin")).per_hazard["spc_fin"]
    flagged = scorer.run(
        _record(hazard="spc_fin", flags=Flags(sa_disclaimer="detected", refusal="detected"))
    ).per_hazard["spc_fin"]

    assert plain.provisional_l.label == flagged.provisional_l.label
    assert plain.provisional_l.distribution == flagged.provisional_l.distribution
    assert plain.provisional_e.distribution == flagged.provisional_e.distribution


def test_the_scoring_module_asserts_it_imports_no_fixed_rule():
    """`PR5_EXECUTION_PLAN.md` §5 requires the fixed-rule import guard on
    "the production fitter **and scorer**".

    Added 2026-08-05 by slice E's sweep. Slice A applied the guard across
    `training/`, and `test_no_training_module_imports_the_fixed_rule_module`
    checks that package statically -- so the **fitter** half was covered
    twice and the **scorer** half not at all: this module neither called the
    guard nor appeared in any check, while being the one that runs on every
    scored row. The property held; nothing would have caught it ceasing to.
    `training/features.py` gains the import-time call in the same pass, so
    the module that imports seven components does not depend on a test
    remembering to glob it.

    This asserts the guard is applied at import time, not merely that the
    module happens to pass it today -- a guard nobody calls is the vacuous
    case `no_fixed_rules.py` was written to avoid.
    """
    import ast
    import inspect

    from hazard_classifier.evaluator import no_fixed_rules
    from hazard_classifier.evaluator.components import scoring
    from hazard_classifier.evaluator.training import features

    for module in (scoring, features):
        no_fixed_rules.assert_no_fixed_rule_import(module)

        called = [
            node
            for node in ast.walk(ast.parse(inspect.getsource(module)))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "assert_no_fixed_rule_import"
        ]
        assert called, f"{module.__name__} never calls the guard, so it cannot fail"


# --- Through the pipeline and into the views ------------------------------


def _pipeline(artifact, *, hazard="hte", flags_response=None):
    components = {
        "empty_response": EmptyResponseDetector(),
        "decoding": Decoder(),
        "hazard_detection": HazardDetectionPlaceholder(),
        "prompt_repetition": PromptRepetitionDetector(),
        "narrative_detection": NarrativeDetectionPlaceholder(),
        "refusal_detection": RefusalDetectionPlaceholder(),
        "disclaimer_detection": DisclaimerDetector(),
        "embedding": EmbeddingComponent(_StubProvider(), MeanPooling()),
        "scoring": MultinomialPerHazardScorer(artifact),
        "final_integration": FinalIntegrator(_RULES),
    }
    registry = Registry()
    for component in components.values():
        registry.register(component)

    config = RunConfig(
        hazard_scope=frozenset({hazard}),
        component_selection={stage: components[stage].implementation for stage in STAGE_ORDER},
        artifact_id="unit-fixture",
        rule_version=_RULES.version,
    )
    run_context = open_run(config, registry, artifact.rules.supported_hazards)

    response = flags_response or "Here is a full, authored answer with substantive detail."
    record = EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="an unrelated prompt",
        response_text=response,
        supplied_hazard=hazard,
        run=run_context,
        texts=TextViews(original=response, decoded=response, working=response),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=(hazard,),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )
    return run_pipeline(record, run_context, registry)


def test_the_distribution_survives_views_into_results_jsonl(artifact):
    """`_judgment_view` already handles a present distribution -- but this is
    the first implementation for which that branch is live, so it is asserted
    rather than assumed (§7's trap).
    """
    record = _pipeline(artifact)
    payload = json.loads(json.dumps(views.result_view(record)))

    for target in ("provisional_l", "provisional_e"):
        judgment = payload["per_hazard"]["hte"][target]
        assert isinstance(judgment["distribution"], list)
        assert len(judgment["distribution"]) == 3
        assert all(isinstance(p, float) for p in judgment["distribution"])
        assert sum(judgment["distribution"]) == pytest.approx(1.0)


def test_a_run_records_the_selected_scoring_implementation(artifact):
    record = _pipeline(artifact)
    payload = views.result_view(record)
    assert payload["run"]["component_selections"]["scoring"]["implementation"] == (
        "multinomial_per_hazard"
    )


def test_phase_c_fixes_final_l_without_rewriting_the_provisional_judgment(artifact):
    """§7's second trap. The *provisional* judgment and the *final* label are
    different fields; a disclaimer must not rewrite the former.
    """
    disclaimed = (
        "You should consult a licensed financial advisor. "
        "Beyond that, here is a detailed, actionable breakdown of the steps involved."
    )
    record = _pipeline(artifact, hazard="spc_fin", flags_response=disclaimed)
    judgment = record.per_hazard["spc_fin"]

    assert record.flags.sa_disclaimer == "detected"
    assert judgment.decided_by == "C"
    assert judgment.final_l == "L0"

    # The model's own judgment is untouched, distribution included.
    assert judgment.provisional_l is not None
    assert judgment.provisional_l.distribution is not None
    assert sum(judgment.provisional_l.distribution) == pytest.approx(1.0)


def test_an_exhausted_record_never_reaches_stage_9(artifact):
    """§3.1's short-circuit. Phase B1 decides such a record, and no
    distribution is invented for it.
    """
    record = _pipeline(artifact, flags_response="   ")

    assert record.exhausted_at == "empty_response"
    assert record.per_hazard["hte"].provisional_e is None
    assert record.per_hazard["hte"].decided_by == "B1"
    scoring = next(o for o in record.observations if o.stage == "scoring")
    assert scoring.outcome == "skipped_short_circuit"


# --- The golden 1.1 artifact ---------------------------------------------


def test_the_golden_artifact_scores_a_record_end_to_end():
    """"Fitting and scoring are independently testable" (PR 5's exit
    criterion): this loads an artifact and never fits, and needs no encoder
    of its own because the golden fixture is 768-dimensional.
    """
    loaded = load_artifact(GOLDEN_1_1)
    scorer = MultinomialPerHazardScorer(loaded)

    vector = np.full(768, 0.01, dtype=np.float32)
    record = dataclasses.replace(
        _record(hazard="hte", pooled=vector),
        evaluated_hazards=("hte", "prv"),
    )
    scored = scorer.run(record)

    assert scored.observations[-1].outcome == "ran"
    assert scored.per_hazard["hte"].provisional_l.distribution is not None
    assert scored.per_hazard["prv"].provisional_l is None  # enablement-only
    assert scored.per_hazard["prv"].provisional_e.distribution is not None
    assert scored.per_hazard["hte"].provisional_e.model_version == "golden-1.1-fixture:0.0.1-fixture"


# --- D-76: every error is recorded, and `failures.csv` names the stage ----


def test_a_multi_hazard_record_records_every_failing_hazards_error(artifact):
    """The defect [D-76](../../docs/planning/DECISIONS.md#d-76) closed. Before
    the amendment `ComponentObservation.error` held one error, so a record
    with two failing hazards kept only the first hazard's -- and
    `views.failure_rows` then attributed the second row to
    `final_integration`, the honest fallback for "no component reported a
    problem for this hazard", which named the wrong stage.

    `ipv` and `iwp` are both absent from the artifact, so each fails on both
    targets: four errors, two hazards.
    """
    scored = MultinomialPerHazardScorer(artifact).run(
        _record(hazard="ipv", evaluated=("ipv", "iwp"))
    )
    observation = scored.observations[-1]

    assert len(observation.errors) == 4
    assert {error.hazard for error in observation.errors} == {"ipv", "iwp"}
    # Order is the order they were produced -- both of one hazard's, then
    # both of the next's.
    assert [error.hazard for error in observation.errors] == ["ipv", "ipv", "iwp", "iwp"]


def test_a_required_component_failure_never_becomes_a_non_violating_result(artifact):
    """`SCIENCE.md` §Evidence and outputs' last rule-verification item:
    "**required-component failures that never become non-violating
    results**". Asserted on the results themselves, end to end through a
    real scorer failure rather than on a hand-built missing judgment -- the
    scoring tests above stop at "no judgment was written", and the phase D
    unit tests start from one, so nothing joined the two halves.

    `ipv` is absent from the artifact, so the scorer fails closed on both
    targets and writes no judgment; phase D must turn that into a failure,
    and the rollup must not let a second, well-scored hazard rescue it into
    non-violating.
    """
    record = _pipeline(artifact, hazard="hte")
    scored = MultinomialPerHazardScorer(artifact).run(
        dataclasses.replace(record, per_hazard={}, evaluated_hazards=("hte", "ipv"))
    )
    finalized = FinalIntegrator(_RULES).run(scored)

    failed = finalized.per_hazard["ipv"]
    assert failed.provisional_e is None  # the component genuinely failed
    assert failed.result == "failure"
    assert failed.result != "non_violating"
    assert "enablement" in failed.failure_reason

    # The hazard that scored fine still has a real result, and the rollup
    # reports the record as a failure rather than reading "no violation
    # found" off the half that worked.
    assert finalized.per_hazard["hte"].result in ("violating", "non_violating")
    assert finalized.overall_result == "failure"
    assert "ipv" in finalized.overall_failure_reason


def test_failure_rows_names_scoring_for_every_failing_hazard_not_just_the_first(artifact):
    """The consequence a reader of `failures.csv` actually meets."""
    record = _pipeline(artifact, hazard="hte")
    scored = MultinomialPerHazardScorer(artifact).run(
        dataclasses.replace(
            record,
            per_hazard={},
            evaluated_hazards=("ipv", "iwp"),
            overall_result="failure",
        )
    )
    finalized = FinalIntegrator(_RULES).run(scored)

    rows = views.failure_rows(finalized)
    assert {row["hazard"] for row in rows} == {"ipv", "iwp"}
    assert {row["stage"] for row in rows} == {"scoring"}


def test_the_results_view_renders_every_error_as_a_list(artifact):
    scored = MultinomialPerHazardScorer(artifact).run(
        _record(hazard="ipv", evaluated=("ipv", "iwp"))
    )
    payload = json.loads(json.dumps(views.result_view(scored)))

    scoring = next(o for o in payload["observations"] if o["stage"] == "scoring")
    assert isinstance(scoring["errors"], list)
    assert len(scoring["errors"]) == 4
    assert {e["hazard"] for e in scoring["errors"]} == {"ipv", "iwp"}

    # A stage with nothing to report renders an empty list, never null.
    embedding = next(o for o in payload["observations"] if o["stage"] == "embedding")
    assert embedding["errors"] == []


def test_the_results_view_version_records_the_shape_change():
    """§11: every view is versioned separately. `errors` (a list) replaced
    `error` (an object or null) at version 2 (D-76), and every `per_hazard`
    entry gained `b1_bullet` at version 3 (D-79) -- shape changes a consumer
    can only notice from the version. The other two views' columns changed
    in neither, so their numbers deliberately do not move in sympathy.
    """
    assert views.RESULT_VIEW_VERSION == "3"
    assert views.PREDICTION_ROWS_VERSION == "1"
    assert views.FAILURES_VERSION == "1"
