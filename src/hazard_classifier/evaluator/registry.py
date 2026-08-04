"""The component registry (`docs/ARCHITECTURE.md` §6): maps
`(stage, implementation_id) -> Component`. Selection is by configuration --
`run.open_run` resolves a `RunConfig`'s stage->implementation-id choices
through a `Registry` instance, never by a component importing another.
"""

from __future__ import annotations

from .contract import Component


class UnregisteredComponentError(KeyError):
    """Raised by `Registry.get` for a `(stage, implementation)` pair with no
    registered `Component`. Subclasses `KeyError` (the natural fit for a
    missing-mapping-entry lookup) rather than introducing a new exception
    hierarchy for what is, structurally, exactly that.
    """

    def __init__(self, stage: str, implementation: str) -> None:
        self.stage = stage
        self.implementation = implementation
        super().__init__(
            f"No component registered for stage={stage!r}, implementation={implementation!r}"
        )


class Registry:
    """`(stage, implementation_id) -> Component`, with registration and
    lookup. Deliberately a plain instantiable class, not a module-level
    singleton: `run.open_run` takes a `Registry` as an explicit argument, so
    a caller (a test, or a run with a restricted implementation set) can
    build a scoped registry rather than reaching into shared global state.
    """

    def __init__(self) -> None:
        self._components: dict[tuple[str, str], Component] = {}

    def register(self, component: Component) -> None:
        """Register `component` under its own declared `(stage,
        implementation)`. A second registration under the same key replaces
        the first -- no distinct "already registered" error, since nothing
        in `ARCHITECTURE.md` requires one and a test double replacing a
        production component under the same key is a normal use.
        """
        self._components[(component.stage, component.implementation)] = component

    def get(self, stage: str, implementation: str) -> Component:
        """Look up a registered component, or raise
        `UnregisteredComponentError` naming both the stage and the
        implementation id that weren't found -- this is what makes
        `run.open_run`'s registry-validation rejection message readable
        (`ARCHITECTURE.md` §2: "names the offending value and the reason").
        """
        try:
            return self._components[(stage, implementation)]
        except KeyError as exc:
            raise UnregisteredComponentError(stage, implementation) from exc
