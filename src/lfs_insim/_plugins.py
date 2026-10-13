"""Plugins: one instance of each type per InSim, made by `insim.use(Type, **options)` (W10)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from lfs_insim._connection import InSim

T = TypeVar("T")

CLICK_IDS = 240
"""Buttons an InSim may show at once: ClickID 0 to 239 (InSim.txt, BUTTONS)."""


class Plugin:
    """Base for a plugin written as a class: it takes the InSim, and its own options by name.

        class Camera(Plugin):
            def __init__(self, insim: InSim, *, speed: int = 1) -> None:
                super().__init__(insim)
                self.roster = insim.use(Roster)  # shared with every other plugin

        camera = insim.use(Camera, speed=2)

    There is one of each type per InSim: `insim.use(Camera)` gives it, and making a second one
    directly raises ValueError. A plugin may also be a function that takes the InSim; a class
    is worth it for inheritance, options or state kept as attributes.
    """

    def __init__(self, insim: InSim) -> None:
        insim._plugins.adopt(self)


class Plugins:
    """The plugins of one InSim (classes or functions), with the options each was made with."""

    def __init__(self, insim: Any) -> None:
        self._insim = insim
        self._made: dict[Callable[..., Any], tuple[object, dict[str, Any]]] = {}
        self._next_click_id = 0

    def use(self, plugin: Callable[..., T], options: dict[str, Any]) -> T:
        if plugin in self._made:
            instance, made_with = self._made[plugin]
            if options and options != made_with:
                raise ValueError(
                    f"{_name(plugin)} is already in use with {made_with}, not {options}"
                )
            return instance  # type: ignore[return-value]  # stored under the plugin that made it
        instance = plugin(self._insim, **options)
        self._made[plugin] = (instance, options)
        return instance

    def reserve_click_ids(self, count: int) -> range:
        if count < 1:
            raise ValueError(f"count must be 1 or more, not {count}")
        start = self._next_click_id
        if start + count > CLICK_IDS:
            raise ValueError(
                f"{count} more ClickIDs do not fit: {start} of the {CLICK_IDS} are reserved"
            )
        self._next_click_id = start + count
        return range(start, start + count)

    def adopt(self, instance: object) -> None:
        """For a plugin made directly (`Roster(insim)`): it becomes the one `use()` gives."""
        plugin = type(instance)
        if plugin in self._made:
            raise ValueError(
                f"this InSim already has a {plugin.__name__}: use insim.use({plugin.__name__})"
            )
        self._made[plugin] = (instance, {})


def _name(plugin: Callable[..., Any]) -> str:
    return getattr(plugin, "__qualname__", repr(plugin))
