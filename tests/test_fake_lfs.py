"""The fake LFS (W3.3) behaves as InSim.txt says, checked with a bare TCP client."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest
from fake_lfs import FakeLFS

from lfs_insim._stream import PacketStream
from lfs_insim.packets import IS_ISI, IS_MST, IS_TINY, IS_VER, TINY
from lfs_insim.packets._codec import InSimPacket


class Client:
    """A bare InSim program: a socket and a PacketStream, nothing else."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer
        self.stream = PacketStream()
        self.pending: list[InSimPacket] = []

    async def send(self, packet: InSimPacket) -> None:
        self.writer.write(packet.pack())
        await self.writer.drain()

    async def receive(self, timeout: float = 2.0) -> InSimPacket:
        async with asyncio.timeout(timeout):
            while not self.pending:
                data = await self.reader.read(4096)
                if not data:
                    raise ConnectionError("closed")
                self.pending.extend(self.stream.feed(data))
        return self.pending.pop(0)

    async def closed(self, timeout: float = 2.0) -> bool:
        """True if the other side closes the connection within the timeout."""
        async with asyncio.timeout(timeout):
            return await self.reader.read(4096) == b""


def run(test: Callable[[FakeLFS, Client], Awaitable[None]], **options: float | str) -> None:
    async def main() -> None:
        async with FakeLFS(**options) as lfs:  # type: ignore[arg-type]
            client = Client(*await asyncio.open_connection("127.0.0.1", lfs.port))
            try:
                await test(lfs, client)
            finally:
                client.writer.close()

    asyncio.run(main())


def test_isi_with_reqi_is_answered_with_ver() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(ReqI=1, InSimVer=10, IName="test"))
        assert await client.receive() == IS_VER(ReqI=1, Version="0.8C31", Product="S3", InSimVer=10)
        assert await lfs.wait_for(IS_ISI) == IS_ISI(ReqI=1, InSimVer=10, IName="test")
        assert lfs.connections == 1

    run(test)


def test_isi_without_reqi_gets_no_answer() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(ReqI=0, InSimVer=10))
        await client.send(IS_TINY(ReqI=5, SubT=TINY.PING))
        assert await client.receive() == IS_TINY(ReqI=5, SubT=TINY.REPLY)  # no IS_VER before

    run(test)


def test_tiny_ver_and_ping() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(InSimVer=10))
        await client.send(IS_TINY(ReqI=3, SubT=TINY.VER))
        assert await client.receive() == IS_VER(ReqI=3, Version="0.7G", Product="DEMO", InSimVer=10)
        await client.send(IS_TINY(ReqI=9, SubT=TINY.PING))
        assert await client.receive() == IS_TINY(ReqI=9, SubT=TINY.REPLY)

    run(test, version="0.7G", product="DEMO")


def test_tiny_close_closes_the_connection() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(InSimVer=10))
        await client.send(IS_TINY(SubT=TINY.CLOSE))
        assert await client.closed()
        await lfs.wait_disconnected()

    run(test)


def test_a_wrong_admin_password_closes_the_connection() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(ReqI=1, InSimVer=10, Admin="wrong"))
        assert await client.closed()

    run(test, admin="secret")


def test_the_right_admin_password_is_accepted() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(ReqI=1, InSimVer=10, Admin="secret"))
        assert isinstance(await client.receive(), IS_VER)

    run(test, admin="secret")


def test_keepalive_sends_blank_tiny_packets() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(InSimVer=10))
        assert await client.receive() == IS_TINY(ReqI=0, SubT=TINY.NONE)
        assert await client.receive() == IS_TINY(ReqI=0, SubT=TINY.NONE)

    run(test, keepalive=0.05)


def test_a_silent_program_is_disconnected_after_the_timeout() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_ISI(InSimVer=10))
        assert await client.closed(timeout=1.0)

    run(test, timeout=0.1)


def test_send_and_drop() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await lfs.wait_connected()
        await lfs.send(IS_MST(Msg="hello"))
        assert await client.receive() == IS_MST(Msg="hello")
        await lfs.drop()
        assert await client.closed()
        assert not lfs.connected

    run(test)


def test_wait_for_returns_each_packet_once() -> None:
    async def test(lfs: FakeLFS, client: Client) -> None:
        await client.send(IS_TINY(ReqI=1, SubT=TINY.NONE))
        await client.send(IS_TINY(ReqI=2, SubT=TINY.NONE))
        assert (await lfs.wait_for(IS_TINY)).ReqI == 1
        assert (await lfs.wait_for(IS_TINY)).ReqI == 2
        with pytest.raises(TimeoutError):
            await lfs.wait_for(IS_TINY, timeout=0.1)

    run(test)
