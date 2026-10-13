"""A prefix of their own for a command or a group (W9.7), against the fake LFS."""

import asyncio

import pytest
from test_commands_typed import _until, replies, run, typed

from lfs_insim import Command, Commands, InSim
from lfs_insim.testing import FakeLFS


def test_a_command_may_have_its_own_prefix() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    got: list[str] = []

    @commands.on_command("who", prefix=".")
    def dot_who(command: Command) -> None:
        got.append("." + command.name)

    @commands.on_command("who")
    def bang_who(command: Command) -> None:
        got.append("!" + command.name)

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed(".who"), typed("!who"), typed("?who"))
        await _until(lambda: len(got) == 2)
        await asyncio.sleep(0.05)
        assert got == [".who", "!who"]

    run(test, insim)


def test_a_group_has_one_prefix_for_all_its_commands() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    aic = commands.command_group("aic", prefix=".")
    got: list[str] = []

    @aic.on_command("start")
    def start(command: Command, plid: int) -> None:
        """Start driving a car."""
        got.append(f"{command.name} {plid}")

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!aic start 3"), typed(".aic start 4"))
        await _until(lambda: got)
        await lfs.send(typed(".aic"), typed(".aic start x"))
        assert await replies(lfs, 3) == [
            ".aic commands:",
            ".aic start <plid>: Start driving a car.",
            ".aic start: plid must be a whole number, not 'x'. Use: .aic start <plid>",
        ]
        assert got == ["aic start 4"]

    run(test, insim)


def test_the_answers_show_the_command_s_own_prefix() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands)

    @commands.on_command("kick", prefix=".")
    def kick(command: Command, name: str) -> None:
        """Kick someone."""

    @commands.on_command("boost", prefix=".", allow=lambda command: False)
    def boost(command: Command) -> None: ...

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed(".kick ?"), typed(".kick"), typed(".boost"))
        assert await replies(lfs, 1) == [".kick <name>: Kick someone."]
        assert await replies(lfs, 1) == [".kick: name is missing. Use: .kick <name>"]
        assert await replies(lfs, 1) == ["You may not use .boost"]

    run(test, insim)


def test_without_a_prefix_in_insim_each_command_brings_its_own() -> None:
    insim = InSim()
    commands = insim.use(Commands)
    got: list[str] = []
    commands.on_command("who", prefix="!")(lambda command: got.append(command.name))

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!who"))
        await _until(lambda: got)

    run(test, insim)


def test_prefixes_and_names_are_checked() -> None:
    with pytest.raises(ValueError, match="need a prefix"):
        InSim().use(Commands).on_command("who")
    insim = InSim(prefix="!")
    commands = insim.use(Commands)
    for prefix in ("", "!!", " ", "a"):
        with pytest.raises(ValueError, match="prefix"):
            commands.on_command("who", prefix=prefix)
        with pytest.raises(ValueError, match="prefix"):
            commands.command_group("aic", prefix=prefix)
    with pytest.raises(ValueError, match="name"):
        commands.on_command(".who", prefix=".")
    commands.on_command("who", prefix=".")(print)
    with pytest.raises(ValueError, match="already"):
        commands.on_command("WHO", prefix=".")
    with pytest.raises(ValueError, match="already"):
        commands.command_group("who", prefix=".")
    commands.on_command("who")(print)  # "!who" is another command
