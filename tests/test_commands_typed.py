"""Commands with typed arguments, help, groups and permissions (W8.2), against the fake LFS."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest
from fake_lfs import FakeLFS

from lfs_insim import Command, InSim
from lfs_insim.packets import IS_MSO, IS_MTC, IS_NCN, IS_TINY, MSO, TINY


def typed(text: str, *, ucid: int = 3) -> IS_MSO:
    name = "^1Bob : "
    return IS_MSO(UCID=ucid, UserType=MSO.PREFIX, TextStart=len(name), Msg=name + text)


def run(
    test: Callable[[FakeLFS], Awaitable[None]], insim: InSim, lfs: FakeLFS | None = None
) -> None:
    async def main() -> None:
        async with lfs or FakeLFS() as fake:
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


# Typed arguments


def test_arguments_are_converted_to_the_annotated_types() -> None:
    insim = InSim(prefix="!")
    got: list[tuple[object, ...]] = []

    @insim.on_command("speed")
    def speed(command: Command, kmh: int, ratio: float, who: str = "all") -> None:
        got.append((command.name, kmh, ratio, who))

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!speed 80 0.5"), typed("!speed 90 1 Bob"))
        await _until(lambda: len(got) == 2)
        assert got == [("speed", 80, 0.5, "all"), ("speed", 90, 1.0, "Bob")]

    run(test, insim)


def test_a_rest_parameter_takes_the_remaining_words() -> None:
    insim = InSim(prefix="!")
    got: list[tuple[object, ...]] = []

    @insim.on_command("tell")
    async def tell(command: Command, who: str, *words: str) -> None:
        got.append((who, words))

    @insim.on_command("sum")
    def total(command: Command, *numbers: int) -> None:
        got.append((sum(numbers),))

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!tell Bob hello there"), typed("!tell Ann"), typed("!sum 1 2 3"))
        await _until(lambda: len(got) == 3)
        # tell is async (a task), so sum may come first
        expected = [("Bob", ("hello", "there")), ("Ann", ()), (6,)]
        assert sorted(got, key=repr) == sorted(expected, key=repr)

    run(test, insim)


def test_bad_arguments_get_the_usage_and_the_function_is_not_called() -> None:
    insim = InSim(prefix="!")
    called: list[int] = []

    @insim.on_command("speed")
    def speed(command: Command, kmh: int, who: str = "all") -> None:
        """Set the speed limit.

        More details that the chat does not show.
        """
        called.append(kmh)

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!speed abc", ucid=4))
        packet = await lfs.wait_for(IS_MTC)
        assert packet.UCID == 4  # only who typed it
        use = "Use: !speed <kmh> [who]"
        assert packet.Text == f"!speed: kmh must be a whole number, not 'abc'. {use}"
        await lfs.send(typed("!speed"), typed("!speed 1 Bob extra"), typed("!speed ?"))
        assert await replies(lfs, 3) == [
            "!speed: kmh is missing. Use: !speed <kmh> [who]",
            "!speed: too many words. Use: !speed <kmh> [who]",
            "!speed <kmh> [who]: Set the speed limit.",
        ]
        assert called == []

    run(test, insim)


def test_a_float_argument_says_number() -> None:
    insim = InSim(prefix="!")
    insim.on_command("ratio")(lambda command, value: None)

    @insim.on_command("scale")
    def scale(command: Command, value: float, *rest: int) -> None: ...

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!scale x"), typed("!scale 1 2 y"), typed("!ratio ?"))
        assert await replies(lfs, 3) == [
            "!scale: value must be a number, not 'x'. Use: !scale <value> [rest...]",
            "!scale: rest must be a whole number, not 'y'. Use: !scale <value> [rest...]",
            "!ratio <value>",  # no docstring, no annotation: a str
        ]

    run(test, insim)


def test_a_function_with_only_the_command_works_as_before() -> None:
    insim = InSim(prefix="!")
    got: list[tuple[str, ...]] = []

    @insim.on_command("kick")
    def kick(command: Command) -> None:
        got.append(command.args)

    insim.on_command("log")(print)  # builtins too

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!kick Bob now please"), typed("!log anything"))
        await _until(lambda: got)
        assert got == [("Bob", "now", "please")]  # any words, unchecked

    run(test, insim)


def test_unsupported_signatures_fail_when_registered() -> None:
    insim = InSim(prefix="!")
    with pytest.raises(TypeError, match="speed: kmh is a list; command arguments are str, int"):

        @insim.on_command("speed")
        def speed(command: Command, kmh: list[int]) -> None: ...

    with pytest.raises(TypeError, match="needs a first parameter for the Command"):
        insim.on_command("empty")(lambda: None)
    with pytest.raises(TypeError, match="go: who must have a default"):

        @insim.on_command("go")
        def go(command: Command, *, who: str) -> None: ...


# Groups


def test_a_group_has_subcommands_and_lists_them() -> None:
    insim = InSim(prefix="!")
    aic = insim.command_group("aic")
    got: list[tuple[str, int]] = []

    @aic.on_command("start")
    def start(command: Command, plid: int) -> None:
        """Start driving a car."""
        got.append((command.name, plid))

    @aic.on_command("stop")
    def stop(command: Command) -> None:
        got.append((command.name, 0))

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!AIC Start 3"), typed("!aic stop"))
        await _until(lambda: len(got) == 2)
        assert got == [("aic start", 3), ("aic stop", 0)]
        await lfs.send(typed("!aic"), typed("!aic jump"), typed("!aic start ?"))
        assert await replies(lfs, 7) == [
            "!aic commands:",
            "!aic start <plid>: Start driving a car.",
            "!aic stop",
            "!aic has no command 'jump'. Its commands:",
            "!aic start <plid>: Start driving a car.",
            "!aic stop",
            "!aic start <plid>: Start driving a car.",
        ]

    run(test, insim)


def test_group_names_are_checked() -> None:
    insim = InSim(prefix="!")
    insim.on_command("aic")(print)
    with pytest.raises(ValueError, match="already"):
        insim.command_group("AIC")
    group = insim.command_group("ai")
    group.on_command("start")(print)
    with pytest.raises(ValueError, match="already"):
        group.on_command("start")
    with pytest.raises(ValueError, match="already"):
        insim.on_command("ai")
    with pytest.raises(ValueError, match="need a prefix"):
        InSim().command_group("aic")


# Permissions


def test_admin_commands_are_for_lfs_admins_and_the_host() -> None:
    lfs = FakeLFS()
    lfs.replies[TINY.NCN] = [
        IS_NCN(UCID=0, UName="", PName="host"),
        IS_NCN(UCID=3, UName="bob", PName="Bob", Admin=1),
        IS_NCN(UCID=4, UName="ann", PName="Ann", Admin=0),
    ]
    insim = InSim(prefix="!")
    kicked: list[tuple[int, str]] = []

    @insim.on_command("kick", admin=True)
    def kick(command: Command, name: str) -> None:
        kicked.append((command.ucid, name))

    async def test(lfs: FakeLFS) -> None:
        await lfs.wait_for(IS_TINY)  # the Roster asks for the connections (TINY_NCN)
        await asyncio.sleep(0.1)  # the answers are in
        await lfs.send(typed("!kick X", ucid=4), typed("!kick Y", ucid=3), typed("!kick Z", ucid=0))
        packet = await lfs.wait_for(IS_MTC)
        assert (packet.UCID, packet.Text) == (4, "!kick is only for admins")
        await _until(lambda: len(kicked) == 2)
        assert kicked == [(3, "Y"), (0, "Z")]
        await lfs.send(typed("!kick ?", ucid=4), typed("!kick W", ucid=9))  # 9: unknown
        assert await replies(lfs, 2) == ["!kick is only for admins"] * 2

    run(test, insim, lfs)


def test_allow_decides_who_may_use_a_command() -> None:
    insim = InSim(prefix="!")
    trusted = {5}
    got: list[int] = []

    @insim.on_command("boost", allow=lambda command: command.ucid in trusted)
    def boost(command: Command) -> None:
        got.append(command.ucid)

    group = insim.command_group("race", allow=lambda command: command.ucid != 6)

    @group.on_command("end", allow=lambda command: command.ucid != 7)
    def end(command: Command) -> None:
        got.append(command.ucid * 10)

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!boost", ucid=5), typed("!boost", ucid=4))
        packet = await lfs.wait_for(IS_MTC)
        assert (packet.UCID, packet.Text) == (4, "You may not use !boost")
        await lfs.send(typed("!race end", ucid=6), typed("!race end", ucid=7))
        assert await replies(lfs, 2) == ["You may not use !race end"] * 2
        await lfs.send(typed("!race end", ucid=8))
        await _until(lambda: len(got) == 2)
        assert got == [5, 80]

    run(test, insim)
