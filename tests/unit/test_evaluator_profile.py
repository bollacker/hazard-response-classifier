"""Tests for `hazard_classifier/evaluator/profile.py`: the run profile and
artifact resolution (slice B, `docs/planning/PR7_EXECUTION_PLAN.md` §5).
"""

from __future__ import annotations

import ast
import re
import json
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from hazard_classifier.embed import EMBEDDING_DIM
from hazard_classifier.evaluator import input_schema, pipeline, profile, views
from hazard_classifier.evaluator.components.integration import RuleSet
from hazard_classifier.evaluator.run import RunRejectedError

GOLDEN_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "baseline" / "artifact"

_EVALUATOR_PACKAGE_DIR = Path(profile.__file__).resolve().parent


class _CapturingProvider:
    """Records every text list passed to `embed`, matching this project's
    established pattern (`test_evaluator_pr4_text_view.py`,
    `test_evaluator_real_bge.py`) for asserting on *which text the encoder
    actually saw*, without touching the network. Returns `EMBEDDING_DIM`-wide
    vectors so the golden artifact's frozen heads (fitted on real,
    768-dimensional BGE vectors) can score them without a shape mismatch --
    their content is irrelevant to this file's assertions, only their shape.
    """

    name: ClassVar[str] = "capturing"
    version: ClassVar[str] = "1"

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts) -> np.ndarray:
        self.calls.append(list(texts))
        return np.zeros((len(list(texts)), EMBEDDING_DIM), dtype=np.float32)


class _StubPooling:
    name: ClassVar[str] = "stub"

    def pool(self, vectors: np.ndarray) -> np.ndarray:
        return (
            np.zeros(EMBEDDING_DIM, dtype=np.float32)
            if vectors.shape[0] == 0
            else vectors.mean(axis=0)
        )


# --- The registry-import boundary (§5: "the only PR 7 file that imports
# `components/*`") -------------------------------------------------------


def _modules_under_test() -> list[Path]:
    """Every `.py` file directly in `evaluator/` -- not `components/`, which
    is expected and required to define components -- excluding `profile.py`
    itself, the one file allowed to import them.
    """
    return [
        path
        for path in _EVALUATOR_PACKAGE_DIR.glob("*.py")
        if path.name not in {"profile.py"}
    ]


def _imports_components(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "components" in module.split("."):
                return True
            if module == "" and any(alias.name == "components" for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "components" in alias.name.split("."):
                    return True
    return False


@pytest.mark.parametrize("path", _modules_under_test(), ids=lambda p: p.name)
def test_only_profile_py_imports_components(path: Path) -> None:
    """`PR7_EXECUTION_PLAN.md` §5: `build_registry` in `profile.py` is "the
    only PR 7 file that imports `components/*`" -- checked by parsing every
    other module's own source, the way
    `experiments/candidates.py::_assert_no_fixed_rule_import` makes its
    constraint a real assertion rather than a comment.
    """
    assert not _imports_components(path), f"{path.name} must not import evaluator.components"


def test_profile_py_does_import_components() -> None:
    """The other half of the same claim: the exemption is real, not vacuous
    (i.e. this test would catch the check above being trivially true because
    nothing imports `components` at all).
    """
    assert _imports_components(_EVALUATOR_PACKAGE_DIR / "profile.py")


# --- RunProfile / load_profile -------------------------------------------


def test_run_profile_defaults() -> None:
    run_profile = profile.RunProfile(artifact_id="some/dir")

    assert run_profile.artifact_id == "some/dir"
    assert run_profile.hazard_scope is None
    assert run_profile.component_selection is None
    assert run_profile.text_view == "working"


def test_run_profile_coerces_hazard_scope_to_a_frozenset() -> None:
    run_profile = profile.RunProfile(artifact_id="d", hazard_scope=["hte", "prv"])

    assert run_profile.hazard_scope == frozenset({"hte", "prv"})


def test_load_profile_reads_every_field(tmp_path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "artifact_id": str(GOLDEN_ARTIFACT),
                "hazard_scope": ["hte"],
                "component_selection": {"decoding": "baseline_best_readable_view"},
                "text_view": "disclaimer_stripped",
            }
        )
    )

    run_profile = profile.load_profile(path)

    assert run_profile.artifact_id == str(GOLDEN_ARTIFACT)
    assert run_profile.hazard_scope == frozenset({"hte"})
    assert run_profile.component_selection == {"decoding": "baseline_best_readable_view"}
    assert run_profile.text_view == "disclaimer_stripped"


def test_load_profile_defaults_missing_optional_fields(tmp_path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"artifact_id": str(GOLDEN_ARTIFACT)}))

    run_profile = profile.load_profile(path)

    assert run_profile.hazard_scope is None
    assert run_profile.component_selection is None
    assert run_profile.text_view == "working"


def test_load_profile_rejects_a_missing_artifact_id(tmp_path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"text_view": "working"}))

    with pytest.raises(profile.ProfileError, match="artifact_id"):
        profile.load_profile(path)


# --- resolve_artifact -----------------------------------------------------
#
# `test_resolve_artifact_loads_the_baseline_format` used to be defined here
# *and* in the artifact-format dispatch section below, where PR 5 slice C
# added the second one. Two `def`s of one name in one module means the
# second silently replaces the first, so this one never ran -- found by
# PR 6 slice C while checking §6's "artifact round trips" row. The
# surviving definition is the stronger of the two and has absorbed this
# one's assertion; see the dispatch section.


# --- build_registry --------------------------------------------------------


def test_build_registry_registers_every_pipeline_stage() -> None:
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)

    built = profile.build_registry(classifier, provider=_CapturingProvider(), pooling=_StubPooling())

    assert set(built.component_selection) == set(pipeline.STAGE_ORDER)
    for stage, implementation in built.component_selection.items():
        # Every default selection must actually resolve through the
        # registry it was built alongside.
        component = built.registry.get(stage, implementation)
        assert component.stage == stage


def test_build_registry_rule_version_comes_from_the_constructed_ruleset() -> None:
    """§5's trap: `rule_version` must never be a literal typed independently
    of the `RuleSet` actually used.
    """
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)

    built = profile.build_registry(classifier, provider=_CapturingProvider(), pooling=_StubPooling())

    expected = RuleSet(
        enablement_only_hazards=classifier.enablement_only_hazards,
        specialized_advice_hazards=classifier.specialized_advice_hazards,
    )
    assert built.rule_version == expected.version


def test_build_registry_passes_text_view_to_the_embedding_component_only() -> None:
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)

    built = profile.build_registry(
        classifier,
        text_view="disclaimer_stripped",
        provider=_CapturingProvider(),
        pooling=_StubPooling(),
    )

    embedding_component = built.registry.get("embedding", built.component_selection["embedding"])
    assert embedding_component.text_view == "disclaimer_stripped"


def test_build_registry_defaults_to_the_real_bge_provider_and_mean_pooling() -> None:
    """Constructing the real provider must not itself touch the network --
    only calling `.embed()` does (`BgeEmbeddingProvider`'s own docstring) --
    so this is safe to assert without a network-marked test.
    """
    from hazard_classifier.evaluator.components.embedding import BgeEmbeddingProvider, MeanPooling

    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    built = profile.build_registry(classifier)

    embedding_component = built.registry.get("embedding", built.component_selection["embedding"])
    assert isinstance(embedding_component.provider, BgeEmbeddingProvider)
    assert isinstance(embedding_component.pooling, MeanPooling)


# --- resolve ---------------------------------------------------------------


def test_resolve_defaults_hazard_scope_to_the_artifacts_trained_hazards() -> None:
    """D-57, resolved in the profile layer: an unspecified `hazard_scope`
    becomes the artifact's frozen supported set.
    """
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))

    resolved = profile.resolve(run_profile, provider=_CapturingProvider(), pooling=_StubPooling())

    assert resolved.run_context.hazard_scope == frozenset(classifier.trained_hazards)


def test_resolve_honors_an_explicit_narrower_hazard_scope() -> None:
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    narrower = frozenset({next(iter(classifier.trained_hazards))})
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT), hazard_scope=narrower)

    resolved = profile.resolve(run_profile, provider=_CapturingProvider(), pooling=_StubPooling())

    assert resolved.run_context.hazard_scope == narrower


def test_resolve_rejects_a_hazard_scope_wider_than_the_artifact_supports() -> None:
    """The exit criterion, literally: "a scope wider than the artifact
    supports is rejected by `open_run` with a message naming the hazards."
    """
    run_profile = profile.RunProfile(
        artifact_id=str(GOLDEN_ARTIFACT),
        hazard_scope=frozenset({"not_a_real_hazard"}),
    )

    with pytest.raises(RunRejectedError, match="not_a_real_hazard"):
        profile.resolve(run_profile, provider=_CapturingProvider(), pooling=_StubPooling())


def test_resolve_component_selection_override_replaces_only_the_named_stage() -> None:
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)
    default_built = profile.build_registry(classifier, provider=_CapturingProvider(), pooling=_StubPooling())
    other_stage = next(s for s in pipeline.STAGE_ORDER if s != "decoding")

    run_profile = profile.RunProfile(
        artifact_id=str(GOLDEN_ARTIFACT),
        component_selection={"decoding": default_built.component_selection["decoding"]},
    )
    resolved = profile.resolve(run_profile, provider=_CapturingProvider(), pooling=_StubPooling())

    assert (
        resolved.run_context.component_selections["decoding"].implementation
        == default_built.component_selection["decoding"]
    )
    assert (
        resolved.run_context.component_selections[other_stage].implementation
        == default_built.component_selection[other_stage]
    )


def test_resolve_produces_a_run_context_that_scores_a_full_pipeline_run() -> None:
    """Slice B's exit criterion: "a profile file plus an artifact directory
    produce a valid `RunContext`" -- proven by actually running the pipeline
    it resolves, not only by inspecting the `RunContext` in isolation.
    """
    row = input_schema.InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="How should I store household chemicals?",
        response_text="Store bleach and ammonia separately; mixing them creates a toxic gas.",
        supplied_hazard="hte",
    )
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT))
    resolved = profile.resolve(run_profile, provider=_CapturingProvider(), pooling=_StubPooling())

    record = input_schema.build_record(row, resolved.run_context)
    result = pipeline.run_pipeline(record, resolved.run_context, resolved.registry)

    assert tuple(o.stage for o in result.observations) == pipeline.STAGE_ORDER
    assert result.overall_result in ("violating", "non_violating")


# --- D-74's conditional deliverable: the profile's text_view field, exercised
# end to end, not just as a constructor argument -----------------------------


def test_profile_text_view_flows_to_the_embedded_text_and_into_results_jsonl() -> None:
    """D-74's own condition for shipping the field at all: "one end-to-end
    run with `text_view: 'disclaimer_stripped'`, asserting the stage-8
    observation records that view in `results.jsonl` and that the embedded
    text is the stripped one." Exercised through `profile.resolve`, not
    directly against `EmbeddingComponent` -- `test_evaluator_pr4_text_view.py`
    already covers the component in isolation; this is the profile-level
    seam D-74 actually decided.
    """
    disclaimer_wording = "consult a qualified professional"
    response = f"You should {disclaimer_wording} before making any decisions about this."
    row = input_schema.InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="What should I do here?",
        response_text=response,
        supplied_hazard="hte",
    )
    run_profile = profile.RunProfile(artifact_id=str(GOLDEN_ARTIFACT), text_view="disclaimer_stripped")
    provider = _CapturingProvider()
    resolved = profile.resolve(run_profile, provider=provider, pooling=_StubPooling())

    record = input_schema.build_record(row, resolved.run_context)
    result = pipeline.run_pipeline(record, resolved.run_context, resolved.registry)

    assert result.flags.sa_disclaimer == "detected"
    stripped_view = result.texts.named["disclaimer_stripped"]
    assert disclaimer_wording not in stripped_view
    assert result.texts.working == response  # D-55: working is left intact

    # The encoder actually received the stripped view, not `working`.
    assert provider.calls == [[stripped_view]]

    # And `results.jsonl` (views.result_view) names the view that was used.
    rendered = views.result_view(result)
    embedding_observation = next(o for o in rendered["observations"] if o["stage"] == "embedding")
    assert embedding_observation["facts"]["text_view"] == "disclaimer_stripped"
    json.dumps(rendered)  # the view stays JSON-serializable


# --- Artifact-format dispatch (PR 5 slice C, `PR5_EXECUTION_PLAN.md` §7) ---

GOLDEN_1_1_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "evaluator_1_1" / "artifact"

ARCHITECTURE_MD = Path(profile.__file__).resolve().parents[3] / "docs" / "ARCHITECTURE.md"


def _section_7_maturities() -> list[tuple[int, str, str]]:
    """Parse `ARCHITECTURE.md` §7's component-inventory table into
    `(row number, stage name, maturity)`. The table's rows are numbered in
    pipeline order, so row *n* is `STAGE_ORDER[n - 1]`.
    """
    lines = ARCHITECTURE_MD.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("## 7. Component inventory"))
    rows = []
    for line in lines[start : start + 20]:
        match = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\*{0,2}(\w+)\*{0,2}\s*\|", line)
        if match:
            rows.append((int(match.group(1)), match.group(2), match.group(3)))
    return rows


def test_architecture_section_7_matches_every_components_real_maturity() -> None:
    """**`ARCHITECTURE.md` §7's table is not documentation, it is the source
    D-47's limitations inventory is generated from** — "every component §7
    marks `partial` or `placeholder` belongs in the inventory"
    ([D-47](../../docs/planning/DECISIONS.md#d-47)'s 2026-08-04 correction).
    Nothing checked it against the code, and **six consecutive verification
    sweeps found that inventory stale**, in both directions. A prose table
    maintained by hand is exactly the shape that goes stale silently.

    So this joins the two: §7's rows, in pipeline order, against the
    `maturity` every registered component actually declares. A component whose
    maturity changes without §7 moving with it now fails here rather than in
    the next sweep -- or, worse, in a limitations document that under- or
    over-states what shipped.

    **Built against the 1.1 artifact deliberately.** Stage 9's implementation
    follows the artifact, and §7 row 9 describes what *a 1.1 artifact runs*
    (`multinomial_per_hazard`, `working`). PR 1's `baseline_two_head` stays
    registered and stays `partial`, but it is not the shipped release's
    scorer, which is why the row says `working` and why resolving a baseline
    artifact here would compare against the wrong implementation.
    """
    from hazard_classifier.evaluator.artifact import load_artifact

    rows = _section_7_maturities()
    assert [row[0] for row in rows] == list(range(1, len(pipeline.STAGE_ORDER) + 1)), (
        "§7's table must carry one numbered row per pipeline stage, in order"
    )

    built = profile.build_registry(
        load_artifact(GOLDEN_1_1_ARTIFACT), provider=_CapturingProvider(), pooling=_StubPooling()
    )

    documented = {}
    actual = {}
    for (number, name, maturity), stage in zip(rows, pipeline.STAGE_ORDER):
        component = built.registry.get(stage, built.component_selection[stage])
        documented[f"{number} {name}"] = maturity
        actual[f"{number} {name}"] = component.maturity

    assert actual == documented

    # And the generated inventory is what the specifications claim it is:
    # three placeholders and three partials, six items in all
    # (`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6, `README.md`). Asserted on the
    # generated set, never on a copied list -- that is the whole point.
    inventory = {name: m for name, m in documented.items() if m in ("partial", "placeholder")}
    assert sorted(inventory.values()) == ["partial"] * 3 + ["placeholder"] * 3
    assert len(inventory) == 6


def test_resolve_artifact_loads_the_baseline_format() -> None:
    """`resolve_artifact` is the one place either format is loaded, so the
    baseline's round trip through it is as load-bearing as the 1.1 one.

    The `trained_hazards` assertion is carried over from a second, earlier
    definition of this same test name further up this file, which the
    duplicate name meant had never run (PR 6 slice C).
    """
    from hazard_classifier.model import HazardResponseClassifier

    loaded = profile.resolve_artifact(GOLDEN_ARTIFACT)

    assert isinstance(loaded, HazardResponseClassifier)
    assert loaded.trained_hazards  # a real, non-empty artifact, not an empty shell


def test_the_baseline_format_round_trips_as_behavior_through_the_evaluator(tmp_path) -> None:
    """`SCIENCE.md` §Evidence and outputs requires verification of **artifact
    round trips**, and `resolve_artifact` loads *both* formats -- so the
    baseline's round trip is as load-bearing as the 1.1 one PR 5 slice B
    covered.

    What was already covered: `model.save`/`load` bit-identical at the head
    level (`test_model_artifact.py`), and `resolve_artifact` dispatching to
    the baseline format (above). What was not, and is the shape PR 5 slice B
    used for the 1.1 format, is the round trip **as behavior**: save, resolve
    the saved copy, and run the whole evaluator on it, asserting the results
    a consumer actually reads are identical.

    Compared on the rendered `results.jsonl` view rather than on the record,
    because the view is what leaves the process -- a field that survived the
    reload but not the flattening would still be a broken round trip.
    """
    from hazard_classifier.model import save

    original = profile.resolve_artifact(GOLDEN_ARTIFACT)
    save(original, tmp_path)
    reloaded = profile.resolve_artifact(tmp_path)

    row = input_schema.InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="How should I store household chemicals?",
        response_text="Store bleach and ammonia separately; mixing them creates a toxic gas.",
        supplied_hazard="hte",
    )

    def _rendered(artifact_path: Path) -> dict:
        resolved = profile.resolve(
            profile.RunProfile(artifact_id=str(artifact_path)),
            provider=_CapturingProvider(),
            pooling=_StubPooling(),
        )
        record = input_schema.build_record(row, resolved.run_context)
        result = pipeline.run_pipeline(record, resolved.run_context, resolved.registry)
        view = views.result_view(result)
        # The artifact id is the one thing that legitimately differs: it is
        # the path each was loaded from.
        view["run"] = {k: v for k, v in view["run"].items() if k != "artifact_id"}
        return view

    assert reloaded.trained_hazards == original.trained_hazards
    assert json.dumps(_rendered(tmp_path)) == json.dumps(_rendered(GOLDEN_ARTIFACT))


def test_resolve_artifact_loads_the_1_1_format() -> None:
    """Dispatch is on the 1.1 manifest's declared `format`, which the
    baseline manifest does not have -- a marker, not a guess at directory
    contents.
    """
    from hazard_classifier.evaluator.artifact import EvaluatorArtifact

    loaded = profile.resolve_artifact(GOLDEN_1_1_ARTIFACT)
    assert isinstance(loaded, EvaluatorArtifact)
    assert loaded.artifact_id == "golden-1.1-fixture"


def test_stage_9s_implementation_follows_the_artifact() -> None:
    """§7: the 1.1 scorer is *registered*, not substituted -- both remain
    distinct `(stage, implementation_id)` entries -- but only the one whose
    model the artifact actually carries can score, so `build_registry`
    selects it from the artifact rather than from a flag.
    """
    baseline = profile.build_registry(
        profile.resolve_artifact(GOLDEN_ARTIFACT),
        provider=_CapturingProvider(),
        pooling=_StubPooling(),
    )
    assert baseline.component_selection["scoring"] == "baseline_two_head"

    evaluator = profile.build_registry(
        profile.resolve_artifact(GOLDEN_1_1_ARTIFACT),
        provider=_CapturingProvider(),
        pooling=_StubPooling(),
    )
    assert evaluator.component_selection["scoring"] == "multinomial_per_hazard"


def test_the_1_1_scorer_reads_hazard_families_from_the_artifact() -> None:
    """D-23: the frozen `rules.json`, never installed config."""
    built = profile.build_registry(
        profile.resolve_artifact(GOLDEN_1_1_ARTIFACT),
        provider=_CapturingProvider(),
        pooling=_StubPooling(),
    )
    integrator = built.registry.get(
        "final_integration", built.component_selection["final_integration"]
    )
    assert "prv" in integrator.rules.enablement_only_hazards
    assert "spc_hlt" in integrator.rules.specialized_advice_hazards


def test_hazard_scope_defaults_to_the_1_1_artifacts_supported_set() -> None:
    """D-57, on the 1.1 format: the default scope is `rules.json`'s supported
    set, which slice B derives from the fitted cells.
    """
    resolved = profile.resolve(
        profile.RunProfile(artifact_id=str(GOLDEN_1_1_ARTIFACT)),
        provider=_CapturingProvider(),
        pooling=_StubPooling(),
    )
    assert resolved.run_context.hazard_scope == frozenset({"hte", "prv"})
    assert resolved.run_context.component_selections["scoring"].implementation == (
        "multinomial_per_hazard"
    )


def test_a_scope_wider_than_the_1_1_artifact_supports_is_rejected() -> None:
    with pytest.raises(RunRejectedError) as excinfo:
        profile.resolve(
            profile.RunProfile(
                artifact_id=str(GOLDEN_1_1_ARTIFACT), hazard_scope=frozenset({"hte", "vcr"})
            ),
            provider=_CapturingProvider(),
            pooling=_StubPooling(),
        )
    assert "vcr" in str(excinfo.value)


def test_a_1_1_run_produces_a_three_class_distribution_end_to_end() -> None:
    """The seam §7 exists to close: a profile, an artifact, and a record in;
    a real distribution out, carried into `results.jsonl`.
    """
    row = input_schema.InputRow(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="What should I know here?",
        response_text="Here is a full, authored answer with substantive detail.",
        supplied_hazard="hte",
    )
    resolved = profile.resolve(
        profile.RunProfile(artifact_id=str(GOLDEN_1_1_ARTIFACT)),
        provider=_CapturingProvider(),
        pooling=_StubPooling(),
    )
    record = input_schema.build_record(row, resolved.run_context)
    result = pipeline.run_pipeline(record, resolved.run_context, resolved.registry)

    rendered = views.result_view(result)
    judgment = rendered["per_hazard"]["hte"]["provisional_e"]
    assert len(judgment["distribution"]) == 3
    assert judgment["model_version"] == "golden-1.1-fixture:0.0.1-fixture"
    json.dumps(rendered)
