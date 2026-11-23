"""Commands typed on this computer in the forms that are not MSO.PREFIX (issue #1), against the
fake LFS.

Seen with LFS 0.8C (lfs-free-camera): while a replay is loaded, a line typed here comes only as
MSO.SYSTEM from UCID 0 with TextStart 0 and the bare text; once, the usual form came later too.
Notices (LFS's, and those recorded in the replay) come as SYSTEM too; chat recorded in the replay
comes as MSO.USER from its UCID. As a guest, "/o text" comes as MSO.O, also with UCID 0.
"""

import asyncio
from collections.abc import Awaitable, Callable

from lfs_insim import Command, Commands, InSim
from lfs_insim._typed_here import COPY_WINDOW
from lfs_insim.packets import IS_ISM, IS_MSL, IS_MSO, IS_MST, IS_MTC, IS_NCN, MSO, TINY
from lfs_insim.state import Roster
from lfs_insim.testing import FakeLFS

REMOTE = 4  # IS_NCN.Flags bit 2


def system(text: str, *, ucid: int = 0, text_start: int = 0) -> IS_MSO:
    return IS_MSO(UCID=ucid, UserType=MSO.SYSTEM, TextStart=text_start, Msg=text)


def typed(text: str, *, ucid: int, user_type: int = MSO.PREFIX) -> IS_MSO:
    name = "^1Someone : "
    return IS_MSO(UCID=ucid, UserType=user_type, TextStart=len(name), Msg=name + text)


def commands(**options: object) -> tuple[InSim, Commands, list[Command]]:
    insim = InSim(prefix="!")
    plugin = insim.use(Commands, **options)
    got: list[Command] = []

    @plugin.on_command("who")
    def who(command: Command, *words: str) -> None:
        got.append(command)
        command.reply("Here")

    @plugin.on_command("kick", admin=True)
    def kick(command: Command) -> None:
        got.append(command)

    return insim, plugin, got


def run(test: Callable[[FakeLFS], Awaitable[None]], insim: InSim, lfs: FakeLFS) -> None:
    async def main() -> None:
        async with lfs:
            insim.port = lfs.port
            async with insim:
                await lfs.wait_connected()
                await _until(lambda: insim.connected)
                await insim.use(Roster).ready()  # whether LFS is a guest
                await test(lfs)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def _sent(lfs: FakeLFS, kind: type) -> list[object]:
    return [packet for packet in lfs.received if isinstance(packet, kind)]


def as_guest(lfs: FakeLFS, *, local_known: bool = True) -> FakeLFS:
    lfs.replies[TINY.ISM] = [IS_ISM(Host=0, HName="testing")]
    host = IS_NCN(UCID=0, PName="host", Admin=1, Total=3, Flags=REMOTE)
    me = IS_NCN(UCID=1, UName="me", PName="Me", Admin=1, Total=3)
    lfs.replies[TINY.NCN] = [host, me] if local_known else [host]
    return lfs


# Typed during a replay


def test_a_command_typed_during_a_replay_runs_as_this_computer() -> None:
    insim, _, got = commands()

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(system("!who"), system("!kick"))
        await _until(lambda: len(got) == 2)
        assert [(c.name, c.ucid, c.local) for c in got] == [("who", 0, True), ("kick", 0, True)]
        assert (await lfs.wait_for(IS_MSL)).Msg == "Here"  # answered to this computer

    run(test, insim, FakeLFS())


def test_the_usual_copy_of_a_line_typed_during_a_replay_does_not_run_again() -> None:
    insim, _, got = commands()

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(system("!who now"), typed("!who now", ucid=0))
        await _until(lambda: got)
        await asyncio.sleep(0.1)
        assert len(got) == 1
        # only one copy per line: typed again in the usual form, it runs
        await lfs.send(typed("!who now", ucid=0))
        await _until(lambda: len(got) == 2)
        # another line, or someone else typing the same words, is not a copy
        await lfs.send(system("!who now"), typed("!who later", ucid=0), typed("!who now", ucid=3))
        await _until(lambda: len(got) == 5)

    run(test, insim, FakeLFS())


def test_a_copy_after_the_window_runs() -> None:
    insim, plugin, got = commands()
    now = [100.0]
    plugin._replay_lines.clock = lambda: now[0]

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(system("!who"))
        await _until(lambda: got)
        now[0] += COPY_WINDOW + 1
        await lfs.send(typed("!who", ucid=0))
        await _until(lambda: len(got) == 2)

    run(test, insim, FakeLFS())


def test_notices_and_recorded_chat_are_not_taken_as_this_computer() -> None:
    insim, _, got = commands()

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(
            system("Bob joined the race"),  # a notice
            system("!nothing of ours"),  # a prefix, but no command of ours
            system("^1Bob : !who", text_start=8),  # not the bare text
            system("!who", ucid=3),  # not UCID 0
        )
        # chat recorded in the replay: its own connection, not this computer, not an admin
        await lfs.send(typed("!kick", ucid=3, user_type=MSO.USER))
        assert (await lfs.wait_for(IS_MTC)).Text == "!kick is only for admins"
        await lfs.send(typed("!who", ucid=3, user_type=MSO.USER))
        await _until(lambda: got)
        assert [(c.ucid, c.local) for c in got] == [(3, False)]
        await asyncio.sleep(0.1)
        assert len(got) == 1

    run(test, insim, FakeLFS())


def test_as_guest_system_messages_are_never_commands() -> None:
    insim, _, got = commands(guest_commands="everyone")

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(system("!who"), system("!kick"))  # the server's notices
        await asyncio.sleep(0.2)
        assert got == []
        assert not _sent(lfs, IS_MSL) and not _sent(lfs, IS_MST)

    run(test, insim, as_guest(FakeLFS()))


# "/o" as a guest


def test_as_guest_slash_o_with_ucid_0_is_this_computer() -> None:
    insim, _, got = commands()

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(IS_MSO(UCID=0, UserType=MSO.O, TextStart=0, Msg="!kick"))
        await lfs.send(IS_MSO(UCID=0, UserType=MSO.O, TextStart=0, Msg="!who"))
        await _until(lambda: len(got) == 2)
        assert [(c.name, c.local) for c in got] == [("kick", True), ("who", True)]
        assert (await lfs.wait_for(IS_MSL)).Msg == "Here"
        assert not _sent(lfs, IS_MST)

    run(test, insim, as_guest(FakeLFS()))


def test_as_guest_slash_o_counts_before_this_computer_is_known() -> None:
    insim, _, got = commands()

    async def test(lfs: FakeLFS) -> None:
        await lfs.send(IS_MSO(UCID=0, UserType=MSO.O, TextStart=0, Msg="!who"))
        await _until(lambda: got)
        assert (got[0].ucid, got[0].local) == (0, True)
        assert (await lfs.wait_for(IS_MSL)).Msg == "Here"
        # the host typing in the chat is still not this computer
        await lfs.send(typed("!who", ucid=0, user_type=MSO.USER))
        await asyncio.sleep(0.1)
        assert len(got) == 1

    run(test, insim, as_guest(FakeLFS(), local_known=False))
