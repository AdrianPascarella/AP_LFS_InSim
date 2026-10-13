"""Plugins: one instance of each type per InSim, made by `insim.use(Type, **options)` (W10)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from lfs_insim._connection import InSim

T = TypeVar("T")


class Plugin:
    """Base for a plugin: a class that takes the InSim, and its own options by name.

        class Camera(Plugin):
            def __init__(self, insim: InSim, *, speed: int = 1) -> None:
                super().__init__(insim)
                self.roster = insim.use(Roster)  # shared with every other plugin

        camera = insim.use(Camera, speed=2)

    There is one of each type per InSim: `insim.use(Camera)` gives it, and making a second one
    directly raises ValueError.
    """

    def __init__(self, insim: InSim) -> None:
        insim._plugins.adopt(self)


class Plugins:
    """The plugins of one InSim, by type, with the options each was made with."""

    def __init__(self, insim: Any) -> None:
        self._insim = insim
        self._made: dict[type, tuple[object, dict[str, Any]]] = {}

    def use(self, plugin: type[T], options: dict[str, Any]) -> T:
        if plugin in self._made:
            instance, made_with = self._made[plugin]
            if options and options != made_with:
                raise ValueError(
                    f"{plugin.__name__} is already in use with {made_with}, not {options}"
                )
            return instance  # type: ignore[return-value]  # stored under its own type
        instance = plugin(self._insim, **options)  # type: ignore[call-arg]
        self._made[plugin] = (instance, options)
        return instance

    def adopt(self, instance: object) -> None:
        """For a plugin made directly (`Roster(insim)`): it becomes the one `use()` gives."""
        plugin = type(instance)
        if plugin in self._made:
            raise ValueError(
                f"this InSim already has a {plugin.__name__}: use insim.use({plugin.__name__})"
            )
        self._made[plugin] = (instance, {})
