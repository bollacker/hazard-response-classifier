"""Tests for `hazard_classifier/evaluator/profile.py`: the run profile and
artifact resolution (slice B, `docs/planning/PR7_EXECUTION_PLAN.md` §5).
"""

from __future__ import annotations

import ast
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


def test_resolve_artifact_loads_the_baseline_format() -> None:
    classifier = profile.resolve_artifact(GOLDEN_ARTIFACT)

    assert classifier.trained_hazards  # a real, non-empty artifact loaded


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
