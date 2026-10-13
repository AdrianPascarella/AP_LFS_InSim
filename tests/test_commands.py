"""Chat commands (W4.5): @commands.on_command("hello") for "!hello", against the fake LFS."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

import pytest

from lfs_insim import Command, Commands, InSim
from lfs_insim.packets import IS_MSO, IS_MTC, MSO
from lfs_insim.testing import FakeLFS


def typed(text: str, *, ucid: int = 3, plid: int = 0, user_type: int = MSO.PREFIX) -> IS_MSO:
    name = "^1Bob : "
    return IS_MSO(UCID=ucid, PLID=plid, UserType=user_type, TextStart=len(name), Msg=name + text)


def run(test: Callable[[FakeLFS, InSim], Awaitable[None]], insim: InSim) -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim.port = lfs.port
            async with insim:
                await lfs.wait_connected()
                await _until(lambda: insim.connected)
                await test(lfs, insim)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def test_a_command_reaches_its_function() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    received: list[Command] = []

    @commands.on_command("hello")
    def hello(command: Command) -> None:
        received.append(command)

    async def test(lfs: FakeLFS, insim: InSim) -> None:
        await lfs.send(typed("!hello", ucid=3, plid=5))
        await _until(lambda: received)
        command = received[0]
        assert (command.name, command.args, command.ucid, command.plid) == ("hello", (), 3, 5)
        assert command.packet.text == "!hello"

    run(test, insim)


def test_arguments_are_split_and_the_name_ignores_case() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    received: list[Command] = []
    commands.on_command("kick")(received.append)

    async def test(lfs: FakeLFS, insim: InSim) -> None:
        await lfs.send(typed("!KICK  Bob   now"))
        await _until(lambda: received)
        assert (received[0].name, received[0].args) == ("kick", ("Bob", "now"))

    run(test, insim)


def test_reply_answers_only_who_typed_it() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)

    @commands.on_command("hello")
    def hello(command: Command) -> None:
        command.reply("Hello, Bob")

    async def test(lfs: FakeLFS, insim: InSim) -> None:
        await lfs.send(typed("!hello", ucid=7))
        packet = await lfs.wait_for(IS_MTC)
        assert (packet.UCID, packet.Text) == (7, "Hello, Bob")

    run(test, insim)


def test_async_commands_can_wait() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    done: list[str] = []

    @commands.on_command("slow")
    async def slow(command: Command) -> None:
        await asyncio.sleep(0.01)
        done.append(command.args[0])

    async def test(lfs: FakeLFS, insim: InSim) -> None:
        await lfs.send(typed("!slow one"))
        await _until(lambda: done == ["one"])

    run(test, insim)


def test_what_is_not_a_known_command_is_left_alone(caplog: pytest.LogCaptureFixture) -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    received: list[Command] = []
    messages: list[IS_MSO] = []
    commands.on_command("hello")(received.append)
    insim.on(IS_MSO)(messages.append)

    async def test(lfs: FakeLFS, insim: InSim) -> None:
        await lfs.send(
            typed("!unknown"),  # perhaps another program's command
            typed("hello", user_type=MSO.USER),  # no prefix
            typed("?hello", user_type=MSO.USER),  # another program's prefix
            typed("!", user_type=MSO.PREFIX),  # only the prefix
            IS_MSO(UserType=MSO.SYSTEM, Msg="!hello"),  # LFS's own message
            typed("!hello"),
        )
        await _until(lambda: len(messages) == 6)
        assert len(received) == 1  # the IS_MSO handlers still get them all

    with caplog.at_level(logging.WARNING, logger="lfs_insim"):
        run(test, insim)
    assert not caplog.records


def test_a_failing_command_is_logged_and_others_still_work(
    caplog: pytest.LogCaptureFixture,
) -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    received: list[Command] = []

    @commands.on_command("broken")
    def broken(command: Command) -> None:
        raise RuntimeError("bug in a command")

    commands.on_command("hello")(received.append)

    async def test(lfs: FakeLFS, insim: InSim) -> None:
        await lfs.send(typed("!broken"), typed("!hello"))
        await _until(lambda: received)

    run(test, insim)
    assert "bug in a command" in caplog.text


def test_commands_need_a_prefix_and_a_good_name() -> None:
    with pytest.raises(ValueError, match="need a prefix"):
        InSim().use(Commands).on_command("hello")
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    commands.on_command("hello")(print)
    with pytest.raises(ValueError, match="already"):
        commands.on_command("HELLO")
    for name in ("", "two words", "!hello"):
        with pytest.raises(ValueError, match="name"):
            commands.on_command(name)
