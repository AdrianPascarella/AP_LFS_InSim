"""Asking LFS for information and waiting for the answer (W4.2), against the fake LFS."""

import asyncio
import time
from collections.abc import Awaitable, Callable

import pytest

from lfs_insim import InSim
from lfs_insim.packets import IS_MSO, IS_NCI, IS_NPL, IS_RES, IS_STA, IS_TINY, IS_VER, TINY
from lfs_insim.testing import FakeLFS

QUIET = 0.2  # request_all's wait for more answers, short for the tests


def run(test: Callable[[FakeLFS, InSim], Awaitable[None]]) -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            async with insim:
                await lfs.wait_connected()
                await test(lfs, insim)

    asyncio.run(main())


def test_request_sends_the_tiny_and_returns_the_answer() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        version = await insim.request(IS_VER)
        assert version.Version == "0.8C31"
        tiny = await lfs.wait_for(IS_TINY)
        assert tiny.SubT == TINY.VER
        assert tiny.ReqI not in (0, 1)  # 0 means "not a request", 1 is IS_ISI's own
        assert version.ReqI == tiny.ReqI

    run(test)


def test_request_all_stops_when_the_counter_is_reached() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.NPL] = [IS_NPL(PLID=plid, NumP=3) for plid in (1, 2, 3)]
        start = time.monotonic()
        players = await insim.request_all(IS_NPL, quiet=5)
        assert [player.PLID for player in players] == [1, 2, 3]
        assert time.monotonic() - start < 2  # did not wait for the quiet time

    run(test)


def test_request_all_without_a_counter_waits_for_quiet() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.NCI] = [IS_NCI(UCID=1), IS_NCI(UCID=2)]
        guests = await insim.request_all(IS_NCI, quiet=QUIET)
        assert [guest.UCID for guest in guests] == [1, 2]

    run(test)


def test_request_all_with_no_answer_is_an_empty_list() -> None:
    # LFS sends nothing for TINY_RES before anyone has finished (seen in the live test, S12).
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        assert await insim.request_all(IS_RES, quiet=QUIET) == []

    run(test)


def test_request_without_an_answer_times_out() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        with pytest.raises(TimeoutError):
            await insim.request(IS_STA, timeout=QUIET)

    run(test)


def test_requests_at_the_same_time_get_their_own_answers() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.NPL] = [IS_NPL(PLID=7, NumP=1)]
        lfs.replies[TINY.SST] = [IS_STA(NumP=1)]
        version, players, state = await asyncio.gather(
            insim.request(IS_VER), insim.request_all(IS_NPL), insim.request(IS_STA)
        )
        assert len({version.ReqI, players[0].ReqI, state.ReqI}) == 3
        assert players[0].PLID == 7 and state.NumP == 1

    run(test)


def test_answers_also_reach_the_handlers() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        seen: list[IS_NPL] = []
        insim.on(IS_NPL)(seen.append)
        lfs.replies[TINY.NPL] = [IS_NPL(PLID=1, NumP=1)]
        players = await insim.request_all(IS_NPL)
        assert seen == players

    run(test)


def test_an_answer_of_another_type_is_not_taken() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.SST] = [IS_MSO(Msg="not a state"), IS_STA(NumP=2)]
        state = await insim.request(IS_STA)
        assert state.NumP == 2

    run(test)


def test_request_identifiers_are_reused() -> None:
    # More requests than there are ReqI values (2 to 255): finished ones free theirs.
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        for _ in range(300):
            await insim.request(IS_VER)

    run(test)


def test_request_without_a_connection_fails() -> None:
    async def main() -> None:
        with pytest.raises(ConnectionError):
            await InSim().request(IS_VER)

    asyncio.run(main())


def test_losing_the_connection_while_waiting_fails() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        waiting = asyncio.create_task(insim.request(IS_STA, timeout=5))
        await lfs.wait_for(IS_TINY)
        await lfs.drop()
        with pytest.raises(ConnectionError):
            await waiting

    run(test)


def test_asking_with_the_wrong_function_is_a_type_error() -> None:
    insim = InSim()
    with pytest.raises(TypeError, match="request_all"):
        asyncio.run(insim.request(IS_NPL))
    with pytest.raises(TypeError, match=r"request\(IS_VER\)"):
        asyncio.run(insim.request_all(IS_VER))
    with pytest.raises(TypeError, match="IS_MSO"):
        asyncio.run(insim.request(IS_MSO))


# The same request at the same time is sent once (W10.3): plugins ask for the same on connecting.


def _asked(lfs: FakeLFS, sub: TINY) -> list[IS_TINY]:
    return [p for p in lfs.received if isinstance(p, IS_TINY) and p.SubT == sub]


def test_the_same_request_all_at_the_same_time_is_sent_once() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.NPL] = [IS_NPL(PLID=plid, NumP=2) for plid in (1, 2)]
        first, second = await asyncio.gather(insim.request_all(IS_NPL), insim.request_all(IS_NPL))
        assert [p.PLID for p in first] == [p.PLID for p in second] == [1, 2]
        first.clear()  # each gets a list of its own
        assert len(second) == 2
        assert len(_asked(lfs, TINY.NPL)) == 1

    run(test)


def test_the_same_request_at_the_same_time_is_sent_once() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.SST] = [IS_STA(NumP=4)]
        first, second = await asyncio.gather(insim.request(IS_STA), insim.request(IS_STA))
        assert first.NumP == second.NumP == 4
        assert len(_asked(lfs, TINY.SST)) == 1

    run(test)


def test_the_same_request_later_is_sent_again() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        lfs.replies[TINY.SST] = [IS_STA(NumP=4)]
        await insim.request(IS_STA)
        await insim.request(IS_STA)
        assert len(_asked(lfs, TINY.SST)) == 2

    run(test)


def test_a_shared_request_survives_the_first_asker_giving_up() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        first = asyncio.create_task(insim.request(IS_STA))
        second = asyncio.create_task(insim.request(IS_STA))
        tiny = await lfs.wait_for(IS_TINY)
        assert tiny.SubT == TINY.SST
        first.cancel()
        await lfs.send(IS_STA(ReqI=tiny.ReqI, NumP=3))
        assert (await second).NumP == 3
        assert first.cancelled()

    run(test)


def test_after_news_from_lfs_the_same_request_is_sent_again() -> None:
    # Something that arrived may have changed the answer (a new host, say): Roster asks again
    # when IS_ISM comes, and must not get the answer to the question it asked before.
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        news: list[IS_MSO] = []
        insim.on(IS_MSO)(news.append)
        first = asyncio.create_task(insim.request(IS_STA))
        first_tiny = await lfs.wait_for(IS_TINY)
        await lfs.send(IS_MSO(Msg="news"))
        async with asyncio.timeout(2):
            while not news:
                await asyncio.sleep(0.01)
        second = asyncio.create_task(insim.request(IS_STA))
        second_tiny = await lfs.wait_for(IS_TINY)
        assert second_tiny.SubT == TINY.SST
        assert second_tiny.ReqI != first_tiny.ReqI
        await lfs.send(IS_STA(ReqI=first_tiny.ReqI, NumP=1), IS_STA(ReqI=second_tiny.ReqI, NumP=2))
        assert ((await first).NumP, (await second).NumP) == (1, 2)

    run(test)
