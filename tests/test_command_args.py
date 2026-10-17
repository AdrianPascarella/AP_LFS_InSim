"""Command arguments of your own type (`Annotated[T, Arg(...)]`), and numbers that are numbers.

Asked from lfs-ai-control (its W5.1): "!ai follow me max 10", where a speed is a number or "max".
And a float argument took "nan", "inf" and "1e999", which float() reads but no word means.
"""

import asyncio
import math
from collections.abc import Awaitable, Callable
from typing import Annotated

import pytest

from lfs_insim import Arg, Command, Commands, InSim
from lfs_insim.packets import IS_MSO, IS_MTC, MSO
from lfs_insim.testing import FakeLFS


def typed(text: str, *, ucid: int = 3) -> IS_MSO:
    name = "^1Bob : "
    return IS_MSO(UCID=ucid, UserType=MSO.PREFIX, TextStart=len(name), Msg=name + text)


def run(test: Callable[[FakeLFS], Awaitable[None]], insim: InSim) -> None:
    async def main() -> None:
        async with FakeLFS() as fake:
            insim.port = fake.port
            async with insim:
                await fake.wait_connected()
                await _until(lambda: insim.connected)
                await test(fake)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


async def replies(lfs: FakeLFS, count: int) -> list[str]:
    """The next `count` IS_MTC texts that the program sends."""
    return [(await lfs.wait_for(IS_MTC)).Text for _ in range(count)]


def _kmh(word: str) -> float:
    """A speed in km/h, or "max"."""
    if word.lower() == "max":
        return math.inf
    value = float(word)
    if not math.isfinite(value):
        raise ValueError(word)
    return value


Kmh = Annotated[float, Arg(_kmh, "a number or max")]


def test_an_argument_of_your_own_type_is_read_by_its_arg() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    got: list[tuple[object, ...]] = []

    @commands.on_command("follow")
    def follow(command: Command, who: str, kmh: Kmh = 80.0, gap: float = 10.0) -> None:
        """Follow a car."""
        got.append((who, kmh, gap))

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!follow me max 10"), typed("!follow Bob 50"), typed("!follow Ann"))
        await _until(lambda: len(got) == 3)
        assert got == [("me", math.inf, 10.0), ("Bob", 50.0, 10.0), ("Ann", 80.0, 10.0)]
        await lfs.send(typed("!follow me fast"), typed("!follow ?"))
        assert await replies(lfs, 2) == [
            "!follow: kmh must be a number or max, not 'fast'. Use: !follow <who> [kmh] [gap]",
            "!follow <who> [kmh] [gap]: Follow a car.",
        ]

    run(test, insim)


def test_a_rest_parameter_may_have_an_arg_too() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    got: list[tuple[float, ...]] = []

    @commands.on_command("speeds")
    def speeds(command: Command, *kmh: Kmh) -> None:
        got.append(kmh)

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!speeds 30 MAX 60"))
        await _until(lambda: len(got) == 1)
        assert got == [(30.0, math.inf, 60.0)]

    run(test, insim)


@pytest.mark.parametrize("word", ["nan", "inf", "-inf", "infinity", "1e999"])
def test_a_float_argument_is_never_infinite_or_nan(word: str) -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    called: list[float] = []

    @commands.on_command("ratio")
    def ratio(command: Command, value: float) -> None:
        called.append(value)

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed(f"!ratio {word}"), typed("!ratio -2.5e3"))
        assert await replies(lfs, 1) == [
            f"!ratio: value must be a number, not '{word}'. Use: !ratio <value>"
        ]
        await _until(lambda: len(called) == 1)
        assert called == [-2500.0]

    run(test, insim)


def test_annotated_without_an_arg_is_its_type() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    got: list[int] = []

    @commands.on_command("laps")
    def laps(command: Command, count: Annotated[int, "how many"]) -> None:
        got.append(count)

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!laps x"), typed("!laps 3"))
        assert await replies(lfs, 1) == [
            "!laps: count must be a whole number, not 'x'. Use: !laps <count>"
        ]
        await _until(lambda: got == [3])

    run(test, insim)


def test_other_types_still_fail_when_registered() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    with pytest.raises(TypeError, match=r"go: at is a complex; .*Annotated\[T, Arg\(\.\.\.\)\]"):

        @commands.on_command("go")
        def go(command: Command, at: complex) -> None: ...

    with pytest.raises(TypeError, match="go: at is a complex"):

        @commands.on_command("go")
        def go2(command: Command, at: Annotated[complex, "no Arg"]) -> None: ...
