"""The fixed-rule import guard, carried from the comparison harness into
production (`docs/planning/PR5_EXECUTION_PLAN.md` §5).

`SCIENCE.md`'s fixed rules -- applicability (phase A), the terminal states
(phase B), the disclaimer modifier (phase C), the missing-judgment failure
(phase D), the L/E-to-result tables, and the rollup -- live in **final
integration only** (`ARCHITECTURE.md` §9;
`PREREGISTRATION_LE_STRUCTURE.md` §2.1: "No candidate applies a fixed rule
from `SCIENCE.md`"). A model that fits or scores L/E must never apply one:
it reports what the response means and supplies, and stops there.

`experiments/candidates.py::_assert_no_fixed_rule_import` made that
constraint checkable *by running the code* rather than by trusting a
docstring, and it was the mechanism the whole structure comparison rested
on. This module is that mechanism in production, so the property survives
the move out of `experiments/` -- which is a copy rather than an import
because production code must not depend on the comparison harness
(`PR5_EXECUTION_PLAN.md` §2).

**One deliberate difference from the `experiments/` original: relative
imports are resolved.** The harness lived in a flat module that only ever
wrote absolute imports, so its check inspected `ast.ImportFrom.module`
verbatim. Inside this package `from ..components.integration import RuleSet`
is the *natural* way to write the forbidden import, and it carries
`module="components.integration"`, `level=2` -- invisible to a verbatim
comparison. Resolving the level against the module's own package is what
keeps the guard from being silently vacuous here.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
from types import ModuleType

__all__ = ["FORBIDDEN_FIXED_RULE_IMPORTS", "FixedRuleImportError", "assert_no_fixed_rule_import"]

# The module that carries `SCIENCE.md`'s fixed rules. Named as a string on
# purpose: this module must not import it either.
FORBIDDEN_FIXED_RULE_IMPORTS = frozenset(
    {
        "hazard_classifier.evaluator.components.integration",
    }
)


class FixedRuleImportError(AssertionError):
    """A module that fits or scores an L/E model imports a module carrying
    `SCIENCE.md`'s fixed rules. Raised at import time, so the violation is a
    hard failure at the moment it is introduced rather than a behavior
    difference discovered later in an output.
    """


def _imported_module_names(node: ast.AST, package: str | None) -> set[str]:
    """Every absolute module name `node` imports, or an empty set if `node`
    is not an import. Relative imports are resolved against `package`.
    """
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}

    if not isinstance(node, ast.ImportFrom):
        return set()

    base = node.module or ""
    if node.level:
        if not package:
            # A relative import in a module with no package is unresolvable
            # and also unimportable; nothing to check.
            return set()
        try:
            base = importlib.util.resolve_name("." * node.level + base, package)
        except (ImportError, ValueError):
            return set()
    if not base:
        return set()
    # `from x import y` can import either the attribute `y` of module `x` or
    # the submodule `x.y`; both spellings are checked, since only one of them
    # is distinguishable without importing.
    return {base} | {f"{base}.{alias.name}" for alias in node.names}


def assert_no_fixed_rule_import(module: ModuleType) -> None:
    """Parse `module`'s own source and raise `FixedRuleImportError` if it
    imports anything in `FORBIDDEN_FIXED_RULE_IMPORTS`.

    Any module that fits or scores an L/E model should call this on itself
    at import time -- `assert_no_fixed_rule_import(sys.modules[__name__])`
    at the bottom of the file -- so the pre-registration §2.1 constraint is
    enforced by running the code.
    """
    source = inspect.getsource(module)
    tree = ast.parse(source, filename=getattr(module, "__file__", "<module>"))
    package = getattr(module, "__package__", None)

    for node in ast.walk(tree):
        hit = _imported_module_names(node, package) & FORBIDDEN_FIXED_RULE_IMPORTS
        if hit:
            raise FixedRuleImportError(
                f"{module.__name__} imports {sorted(hit)}, which carries SCIENCE.md's "
                "fixed rules (applicability, terminal states, the disclaimer modifier, "
                "the L/E-to-result tables, the rollup). An L/E model must not apply "
                "those -- they belong to final integration only "
                "(ARCHITECTURE.md §9; PREREGISTRATION_LE_STRUCTURE.md §2.1)."
            )
