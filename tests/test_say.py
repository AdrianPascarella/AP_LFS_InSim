"""Sending text with ease (W4.4): insim.say() and insim.command(), against the fake LFS."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest
from fake_lfs import FakeLFS

from lfs_insim import InSim
from lfs_insim.packets import IS_MSL, IS_MST, IS_MSX, IS_MTC, PacketError


def run(test: Callable[[FakeLFS, InSim], Awaitable[None]]) -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            async with insim:
                await lfs.wait_connected()
                await _until(lambda: insim.connected)
                await test(lfs, insim)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def test_a_short_message_goes_as_mst() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        insim.say("hello")
        assert (await lfs.wait_for(IS_MST)).Msg == "hello"

    run(test)


def test_a_longer_message_goes_as_msx() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        insim.say("x" * 64)
        assert (await lfs.wait_for(IS_MSX)).Msg == "x" * 64

    run(test)


def test_the_limits_count_bytes_not_characters() -> None:
    # 32 Cyrillic letters: ^C and 32 bytes fit in IS_MST; 62 Japanese ones (2 bytes each) need
    # 2 + 124 bytes, too many even for IS_MSX.
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        insim.say("Ж" * 32)
        assert (await lfs.wait_for(IS_MST)).Msg == "Ж" * 32
        insim.say("あ" * 40)
        assert (await lfs.wait_for(IS_MSX)).Msg == "あ" * 40
        with pytest.raises(PacketError, match="limit is 95"):
            insim.say("あ" * 62)

    run(test)


def test_a_message_to_one_connection_goes_as_mtc() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        insim.say("only for you", to=3)
        packet = await lfs.wait_for(IS_MTC)
        assert (packet.UCID, packet.PLID, packet.Text) == (3, 0, "only for you")
        insim.say("y" * 127, to=3)  # IS_MTC takes up to 127 bytes
        assert (await lfs.wait_for(IS_MTC)).Text == "y" * 127

    run(test)


def test_a_message_to_this_computer_goes_as_msl() -> None:
    # UCID 0 is this computer. LFS answers IS_MTC with "only for multiplayer hosts" in single
    # player (seen in W4.7, S12), so it goes as IS_MSL, which only this computer shows.
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        insim.say("only for you", to=0)
        assert (await lfs.wait_for(IS_MSL)).Msg == "only for you"
        insim.say("y" * 127, to=0)
        assert (await lfs.wait_for(IS_MSL)).Msg == "y" * 127
        assert not [p for p in lfs.received if isinstance(p, IS_MTC)]

    run(test)


def test_a_command_goes_as_mst() -> None:
    async def test(lfs: FakeLFS, insim: InSim) -> None:
        insim.command("/restart")
        assert (await lfs.wait_for(IS_MST)).Msg == "/restart"

    run(test)


def test_say_and_command_are_not_mixed_up() -> None:
    insim = InSim()
    with pytest.raises(ValueError, match="command"):
        insim.say("/restart")
    with pytest.raises(ValueError, match="say"):
        insim.command("restart")


def test_a_command_too_long_fails() -> None:
    insim = InSim()
    with pytest.raises(PacketError, match="limit is 63"):
        insim.command("/msg " + "x" * 60)


def test_without_a_connection_say_fails() -> None:
    with pytest.raises(ConnectionError):
        InSim().say("hello")
