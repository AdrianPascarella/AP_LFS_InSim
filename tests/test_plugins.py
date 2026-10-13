"""Plugins (W10): `insim.use(Type, **options)` gives one instance of each type per connection.

A plugin is a class that takes the InSim (and its own options). Roster is one; the commands use it
too, so they and the program share a single Roster, which asks LFS for everyone once (P10).
"""

import asyncio
from collections.abc import Callable

import pytest
from fake_lfs import FakeLFS

from lfs_insim import Command, InSim
from lfs_insim.packets import IS_ISM, IS_NCN, IS_TINY, TINY
from lfs_insim.state import Roster


class Camera:
    """A plugin with options, as an application in another project would write it."""

    def __init__(self, insim: InSim, *, speed: int = 1) -> None:
        self.insim = insim
        self.speed = speed
        self.roster = insim.use(Roster)


def test_use_gives_one_instance_of_each_type() -> None:
    insim = InSim()
    roster = insim.use(Roster)
    assert isinstance(roster, Roster)
    assert insim.use(Roster) is roster


def test_use_passes_the_insim_and_the_options() -> None:
    insim = InSim()
    camera = insim.use(Camera, speed=2)
    assert camera.insim is insim
    assert camera.speed == 2
    assert camera.roster is insim.use(Roster)  # a plugin shares what it uses


def test_use_again_without_options_or_with_the_same_ones_gives_the_same() -> None:
    insim = InSim()
    camera = insim.use(Camera, speed=2)
    assert insim.use(Camera) is camera
    assert insim.use(Camera, speed=2) is camera


def test_use_again_with_other_options_is_an_error() -> None:
    insim = InSim()
    insim.use(Camera, speed=2)
    with pytest.raises(ValueError, match="Camera"):
        insim.use(Camera, speed=3)


def test_a_roster_made_directly_is_the_one_use_gives() -> None:
    insim = InSim()
    roster = Roster(insim)
    assert insim.use(Roster) is roster


def test_a_second_roster_for_the_same_connection_is_an_error() -> None:
    insim = InSim()
    Roster(insim)
    with pytest.raises(ValueError, match=r"insim\.use\(Roster\)"):
        Roster(insim)


def test_each_connection_has_its_own() -> None:
    first, second = InSim(), InSim()
    assert first.use(Roster) is not second.use(Roster)


def test_a_function_is_a_plugin_too() -> None:
    calls: list[tuple[InSim, int]] = []

    def camera(insim: InSim, *, speed: int = 1) -> Roster:
        calls.append((insim, speed))
        return insim.use(Roster)

    insim = InSim()
    roster = insim.use(camera, speed=2)
    assert roster is insim.use(Roster)  # what the function gives, with its type
    assert insim.use(camera) is roster
    assert calls == [(insim, 2)]  # called once
    with pytest.raises(ValueError, match="camera"):
        insim.use(camera, speed=3)


def test_a_function_that_gives_nothing_is_used_once() -> None:
    calls: list[InSim] = []

    def logger(insim: InSim) -> None:
        calls.append(insim)

    insim = InSim()
    insim.use(logger)
    insim.use(logger)
    assert calls == [insim]


def test_commands_and_your_own_roster_ask_lfs_once() -> None:
    """P10: the commands made a Roster of their own, so LFS was asked for everyone twice."""

    async def main() -> None:
        async with FakeLFS() as lfs:
            lfs.replies[TINY.ISM] = [IS_ISM(Host=1, HName="mine")]
            lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, PName="Me", Total=1)]
            insim = InSim(port=lfs.port, prefix="!")
            roster = Roster(insim)

            @insim.on_command("who")
            def who(command: Command) -> None:
                pass

            async with insim:
                await lfs.wait_connected()
                await _until(lambda: 0 in roster.connections)
                await asyncio.sleep(0.2)  # time for a second roster's questions
                for sub in (TINY.ISM, TINY.NCN, TINY.NPL):
                    asked = [p for p in lfs.received if isinstance(p, IS_TINY) and p.SubT == sub]
                    assert len(asked) == 1, sub

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)
