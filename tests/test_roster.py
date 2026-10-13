"""Who is who: lfs_insim.state.Roster (W4.3), against the fake LFS."""

import asyncio
from collections.abc import Awaitable, Callable

from fake_lfs import FakeLFS

from lfs_insim import InSim
from lfs_insim.packets import (
    IS_CNL,
    IS_CPR,
    IS_ISM,
    IS_NCN,
    IS_NPL,
    IS_PLL,
    IS_PLP,
    IS_TINY,
    IS_TOC,
    TINY,
)
from lfs_insim.state import Roster

FAST = (0.01, 0.02, 0.05)
AI = 2  # PType bit 1


def host() -> IS_NCN:
    return IS_NCN(UCID=0, UName="", PName="Host", Admin=1, Total=2)


def guest() -> IS_NCN:
    return IS_NCN(UCID=3, UName="guest", PName="^1Guest", Total=2, Flags=4)


def npl(plid: int, ucid: int, name: str, *, ai: bool = False, num_p: int = 1) -> IS_NPL:
    return IS_NPL(
        PLID=plid,
        UCID=ucid,
        PType=AI if ai else 0,
        PName=name,
        Plate="PLATE",
        CName="XFG",
        NumP=num_p,
    )


def run(
    test: Callable[[FakeLFS, InSim, Roster], Awaitable[None]],
    *,
    connections: tuple[IS_NCN, ...] = (),
    players: tuple[IS_NPL, ...] = (),
) -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            lfs.replies[TINY.NCN] = list(connections)
            lfs.replies[TINY.NPL] = list(players)
            insim = InSim(port=lfs.port)
            insim._retry_delays = FAST
            roster = Roster(insim)
            async with insim:
                await lfs.wait_connected()
                await _until(lambda: len(roster.players) == len(players))
                await _until(lambda: len(roster.connections) == len(connections))
                await test(lfs, insim, roster)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def test_the_state_is_asked_for_on_connecting() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        guest_conn = roster.connections[3]
        assert (guest_conn.username, guest_conn.name, guest_conn.admin) == (
            "guest",
            "^1Guest",
            False,
        )
        assert guest_conn.remote and not roster.connections[0].remote
        assert roster.connections[0].admin
        human, robot = roster.players[1], roster.players[2]
        assert (human.name, human.plate, human.car, human.is_ai) == (
            "^1Guest",
            "PLATE",
            "XFG",
            False,
        )
        assert human.connection is guest_conn
        assert robot.is_ai and robot.connection is roster.connections[0]
        assert guest_conn.players == [human]
        assert roster.connections[0].players == [robot]

    run(
        test,
        connections=(host(), guest()),
        players=(npl(1, 3, "^1Guest", num_p=2), npl(2, 0, "AI 1", ai=True, num_p=2)),
    )


def test_connections_come_and_go() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(guest(), npl(5, 3, "^1Guest"))
        await _until(lambda: 5 in roster.players)
        await lfs.send(IS_CNL(UCID=3, Total=1))
        await _until(lambda: 3 not in roster.connections)
        assert 5 not in roster.players  # its player left with it
        assert list(roster.connections) == [0]

    run(test, connections=(host(),))


def test_players_join_go_to_the_pits_come_back_and_leave() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(npl(4, 0, "Host"))
        await _until(lambda: 4 in roster.players)
        player = roster.players[4]
        assert not player.in_pits
        await lfs.send(IS_PLP(PLID=4))
        await _until(lambda: player.in_pits)
        assert roster.players[4] is player  # still in the list
        await lfs.send(npl(4, 0, "Host"))  # "if PLID already exists, then leaving pits"
        await _until(lambda: not player.in_pits)
        assert roster.players[4] is player
        await lfs.send(IS_PLL(PLID=4))
        await _until(lambda: 4 not in roster.players)
        assert roster.connections[0].players == []

    run(test, connections=(host(),))


def test_a_join_request_is_not_a_player() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(npl(6, 0, "Host", num_p=0), npl(7, 0, "Host"))
        await _until(lambda: 7 in roster.players)
        assert 6 not in roster.players

    run(test, connections=(host(),))


def test_renaming_changes_the_connection_and_its_human_players() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(IS_CPR(UCID=0, PName="New name", Plate="NEW"))
        await _until(lambda: roster.connections[0].name == "New name")
        assert (roster.players[1].name, roster.players[1].plate) == ("New name", "NEW")
        assert roster.players[2].name == "AI 1"  # an AI keeps its own name

    run(
        test,
        connections=(host(),),
        players=(npl(1, 0, "Host", num_p=2), npl(2, 0, "AI 1", ai=True, num_p=2)),
    )


def test_taking_over_a_car_moves_the_player() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(IS_TOC(PLID=1, OldUCID=0, NewUCID=3))
        await _until(lambda: roster.players[1].connection.ucid == 3)
        assert roster.connections[0].players == []
        assert roster.connections[3].players == [roster.players[1]]

    run(test, connections=(host(), guest()), players=(npl(1, 0, "Host"),))


def test_clearing_the_race_removes_every_player() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(IS_TINY(SubT=TINY.CLR))
        await _until(lambda: not roster.players)
        assert len(roster.connections) == 2
        assert all(not connection.players for connection in roster.connections.values())

    run(
        test,
        connections=(host(), guest()),
        players=(npl(1, 3, "^1Guest", num_p=2), npl(2, 0, "AI 1", ai=True, num_p=2)),
    )


def test_a_player_of_an_unknown_connection_waits_for_it() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(npl(8, 9, "Late"))
        await _until(lambda: 8 in roster.players)
        await lfs.send(IS_NCN(UCID=9, UName="late", PName="Late", Total=2))
        await _until(lambda: roster.connections[9].username == "late")
        assert roster.players[8].connection is roster.connections[9]
        assert roster.connections[9].players == [roster.players[8]]

    run(test, connections=(host(),))


def test_the_state_is_rebuilt_after_reconnecting() -> None:
    # The previous project cleared after asking again, and lost LFS's quick answer (LEGADO.md
    # P22): clearing after request_all() makes this fail.
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        lfs.replies[TINY.NCN] = [host()]
        lfs.replies[TINY.NPL] = [npl(9, 0, "Host")]
        await lfs.drop()
        await lfs.wait_connected(connections=2)
        await _until(lambda: list(roster.players) == [9])
        assert list(roster.connections) == [0]

    run(test, connections=(host(), guest()), players=(npl(1, 3, "^1Guest"),))


def test_starting_or_ending_multiplayer_asks_for_the_state_again() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        lfs.replies[TINY.NCN] = [host(), guest()]
        await lfs.send(IS_ISM(Host=1, HName="server"))
        await _until(lambda: 3 in roster.connections)
        lfs.replies[TINY.NCN] = [host()]
        await lfs.send(IS_TINY(SubT=TINY.MPE))
        await _until(lambda: 3 not in roster.connections)

    run(test, connections=(host(),))


def test_handlers_see_who_arrives_and_who_leaves() -> None:
    # The roster changes before the user's handlers when someone arrives, and after them when
    # someone leaves: an async handler still finds the one leaving until its first await.
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        seen: list[str] = []

        @insim.on(IS_NPL)
        def joined(packet: IS_NPL) -> None:
            seen.append(f"joined {roster.players[packet.PLID].name}")

        @insim.on(IS_PLL)
        def left(packet: IS_PLL) -> None:
            seen.append(f"left {roster.players[packet.PLID].name}")

        @insim.on(IS_CNL)
        async def gone(packet: IS_CNL) -> None:
            seen.append(f"gone {roster.connections[packet.UCID].username}")
            await asyncio.sleep(0)

        await lfs.send(guest(), npl(5, 3, "Bob"))
        await _until(lambda: seen == ["joined Bob"])
        await lfs.send(IS_PLL(PLID=5), IS_CNL(UCID=3, Total=1))
        await _until(lambda: 3 not in roster.connections)
        assert seen == ["joined Bob", "left Bob", "gone guest"]

    run(test, connections=(host(),))


def test_unknown_ids_are_ignored() -> None:
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(
            IS_PLL(PLID=99),
            IS_PLP(PLID=99),
            IS_CNL(UCID=99),
            IS_CPR(UCID=99, PName="x"),
            IS_TOC(PLID=99, NewUCID=0),
            npl(4, 0, "Host"),
        )
        await _until(lambda: 4 in roster.players)

    run(test, connections=(host(),))


def test_a_ucid_reused_at_once_keeps_the_new_connection() -> None:
    # Someone leaves and someone else gets the same UCID in the same TCP read (S18).
    async def test(lfs: FakeLFS, insim: InSim, roster: Roster) -> None:
        await lfs.send(IS_CNL(UCID=3, Total=1), IS_NCN(UCID=3, UName="new", PName="New", Total=2))
        await _until(lambda: 3 not in roster.connections or roster.connections[3].username == "new")
        await asyncio.sleep(0.05)
        assert roster.connections[3].username == "new"

    run(test, connections=(host(), guest()))
