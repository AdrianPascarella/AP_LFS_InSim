"""LFS as a guest in someone else's server (W9), against the fake LFS.

What a guest LFS sends was seen in the real game (LOG.md S19): IS_ISM with Host=0; this computer
is a connection without the remote flag (UCID 1 there), the host is UCID 0 with it; what anyone
types comes as MSO.USER whatever the prefix; "/o text" comes as MSO.O with TextStart 0. LFS refuses
IS_MTC from a guest ("only for multiplayer hosts"), but shows IS_MSL.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import pytest
from fake_lfs import FakeLFS

from lfs_insim import Command, Commands, InSim
from lfs_insim.packets import (
    IS_ISM,
    IS_MSL,
    IS_MSO,
    IS_MST,
    IS_MTC,
    IS_NCN,
    IS_NPL,
    IS_TINY,
    MSO,
    TINY,
)
from lfs_insim.state import Roster

REMOTE = 4  # IS_NCN.Flags bit 2
P = TypeVar("P")


def server_host(admin: int = 1) -> IS_NCN:
    return IS_NCN(UCID=0, PName="host", Admin=admin, Total=3, Flags=REMOTE)


def this_computer() -> IS_NCN:
    return IS_NCN(UCID=1, UName="me", PName="Me", Admin=1, Total=3)


def stranger(admin: int = 0) -> IS_NCN:
    return IS_NCN(UCID=3, UName="bob", PName="Bob", Admin=admin, Total=3, Flags=REMOTE)


def as_guest(lfs: FakeLFS, *, stranger_admin: int = 0) -> FakeLFS:
    lfs.replies[TINY.ISM] = [IS_ISM(Host=0, HName="testing")]
    lfs.replies[TINY.NCN] = [server_host(), this_computer(), stranger(stranger_admin)]
    return lfs


def typed(text: str, *, ucid: int, user_type: int = MSO.USER) -> IS_MSO:
    name = "^1Someone : "
    return IS_MSO(UCID=ucid, UserType=user_type, TextStart=len(name), Msg=name + text)


def run(test: Callable[[FakeLFS], Awaitable[None]], insim: InSim, lfs: FakeLFS) -> None:
    async def main() -> None:
        async with lfs:
            insim.port = lfs.port
            async with insim:
                await lfs.wait_connected()
                await _until(lambda: insim.connected)
                await _asked_for(lfs, TINY.ISM)
                await asyncio.sleep(0.1)  # the answers are in
                await test(lfs)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


async def _asked_for(lfs: FakeLFS, sub: TINY) -> None:
    await _until(lambda: any(isinstance(p, IS_TINY) and p.SubT == sub for p in lfs.received))


def _sent(lfs: FakeLFS, cls: type[P]) -> list[P]:
    return [packet for packet in lfs.received if isinstance(packet, cls)]


# The roster (W9.1)


def roster_run(test: Callable[[FakeLFS, Roster], Awaitable[None]], lfs: FakeLFS) -> None:
    insim = InSim()
    roster = Roster(insim)
    run(lambda lfs: test(lfs, roster), insim, lfs)


def test_the_roster_knows_when_lfs_is_a_guest_and_which_connection_is_this_computer() -> None:
    async def test(lfs: FakeLFS, roster: Roster) -> None:
        assert roster.guest
        assert roster.local is roster.connections[1]
        lfs.replies[TINY.ISM] = []
        lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, PName="Me", Total=1)]
        await lfs.send(IS_TINY(SubT=TINY.MPE))  # back to single player
        await _until(lambda: not roster.guest)
        await _until(lambda: list(roster.connections) == [0])
        assert roster.local is roster.connections[0]

    roster_run(test, as_guest(FakeLFS()))


def test_as_host_this_computer_is_the_host() -> None:
    lfs = FakeLFS()
    lfs.replies[TINY.ISM] = [IS_ISM(Host=1, HName="mine")]
    lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, PName="Me", Total=2), stranger()]

    async def test(lfs: FakeLFS, roster: Roster) -> None:
        assert not roster.guest
        assert roster.local is roster.connections[0]

    roster_run(test, lfs)


def test_joining_a_server_makes_lfs_a_guest() -> None:
    async def test(lfs: FakeLFS, roster: Roster) -> None:
        assert not roster.guest  # single player: LFS does not answer TINY_ISM
        as_guest(lfs)
        await lfs.send(IS_ISM(Host=0, HName="testing"))  # LFS sends it on joining
        await _until(lambda: roster.guest and roster.local is roster.connections.get(1))

    lfs = FakeLFS()
    lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, PName="Me", Total=1)]
    roster_run(test, lfs)


def test_the_answer_to_tiny_ism_does_not_ask_again() -> None:
    async def test(lfs: FakeLFS, roster: Roster) -> None:
        await asyncio.sleep(0.3)
        asked = [p for p in _sent(lfs, IS_TINY) if p.SubT == TINY.ISM]
        assert len(asked) == 1

    roster_run(test, as_guest(FakeLFS()))


def test_a_connection_known_only_from_its_player_is_not_this_computer() -> None:
    async def test(lfs: FakeLFS, roster: Roster) -> None:
        await _until(lambda: 1 in roster.connections)  # made for its player, without IS_NCN
        assert roster.local is None

    lfs = FakeLFS()
    lfs.replies[TINY.ISM] = [IS_ISM(Host=0, HName="testing")]
    lfs.replies[TINY.NCN] = [server_host()]
    lfs.replies[TINY.NPL] = [IS_NPL(PLID=2, UCID=1, PName="Me", NumP=1)]
    roster_run(test, lfs)


# Commands (W9.2, W9.3, W9.4)


def commands(**options: str) -> tuple[InSim, list[Command]]:
    insim = InSim(prefix="!")
    chat = insim.use(Commands, **options)
    got: list[Command] = []

    @chat.on_command("who")
    def who(command: Command) -> None:
        got.append(command)
        command.reply("Here")

    @chat.on_command("kick", admin=True)
    def kick(command: Command) -> None:
        got.append(command)

    return insim, got


def test_as_guest_only_this_computer_may_use_commands() -> None:
    insim, got = commands()

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!who", ucid=3), typed("!who", ucid=0), typed("!kick", ucid=3))
        await lfs.send(typed("!who", ucid=1))
        await _until(lambda: got)
        assert [(c.ucid, c.local) for c in got] == [(1, True)]
        reply = await lfs.wait_for(IS_MSL)  # only this computer sees it
        assert reply.Msg == "Here"
        await asyncio.sleep(0.1)
        assert len(got) == 1  # the others were ignored, without an answer
        assert not _sent(lfs, IS_MTC) and not _sent(lfs, IS_MST)

    run(test, insim, as_guest(FakeLFS(), stranger_admin=1))


def test_as_guest_everyone_may_be_let_in_and_is_answered_in_public() -> None:
    insim, got = commands(guest_commands="everyone")

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!who", ucid=3))
        reply = await lfs.wait_for(IS_MST)  # the only way to reach someone else as a guest
        assert reply.Msg == "Here"
        assert [(c.ucid, c.local) for c in got] == [(3, False)]
        assert not _sent(lfs, IS_MTC)

    run(test, insim, as_guest(FakeLFS()))


def test_as_guest_admin_commands_are_only_for_this_computer() -> None:
    insim, got = commands(guest_commands="everyone")

    async def test(lfs: FakeLFS) -> None:
        # the server's host and its admins are not our admins
        await lfs.send(typed("!kick", ucid=0), typed("!kick", ucid=3))
        assert [(await lfs.wait_for(IS_MST)).Msg for _ in range(2)] == [
            "!kick is only for admins"
        ] * 2
        await lfs.send(typed("!kick", ucid=1))
        await _until(lambda: got)
        assert [c.ucid for c in got] == [1]

    run(test, insim, as_guest(FakeLFS(), stranger_admin=1))


def test_allow_still_applies_to_everyone_else() -> None:
    insim = InSim(prefix="!")
    commands = insim.use(Commands, guest_commands="everyone")
    got: list[int] = []
    commands.on_command("boost", allow=lambda command: command.ucid != 3)(
        lambda command: got.append(command.ucid)
    )

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!boost", ucid=3))
        assert (await lfs.wait_for(IS_MST)).Msg == "You may not use !boost"
        assert got == []

    run(test, insim, as_guest(FakeLFS()))


def test_commands_typed_with_slash_o_are_from_this_computer() -> None:
    insim, got = commands()

    async def test(lfs: FakeLFS) -> None:
        # "/o !who": only this computer's InSim sees it; LFS sends the text alone
        await lfs.send(IS_MSO(UCID=1, UserType=MSO.O, TextStart=0, Msg="!who"))
        await _until(lambda: got)
        assert (got[0].ucid, got[0].local) == (1, True)
        assert (await lfs.wait_for(IS_MSL)).Msg == "Here"

    run(test, insim, as_guest(FakeLFS()))


def test_as_host_commands_work_as_before() -> None:
    insim, got = commands()
    lfs = FakeLFS()
    lfs.replies[TINY.ISM] = [IS_ISM(Host=1, HName="mine")]
    lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, PName="Me", Total=2), stranger()]

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(typed("!who", ucid=3, user_type=MSO.PREFIX))
        reply = await lfs.wait_for(IS_MTC)
        assert (reply.UCID, reply.Text) == (3, "Here")
        await lfs.send(typed("!who", ucid=0, user_type=MSO.PREFIX))
        assert (await lfs.wait_for(IS_MSL)).Msg == "Here"
        assert [(c.ucid, c.local) for c in got] == [(3, False), (0, True)]

    run(test, insim, lfs)


def test_guest_commands_is_checked() -> None:
    with pytest.raises(ValueError, match="guest_commands"):
        InSim(prefix="!").use(Commands, guest_commands="friends")
