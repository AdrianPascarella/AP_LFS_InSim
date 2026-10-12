"""A fake LFS for the tests (W3.3): an InSim TCP server on 127.0.0.1 that behaves like LFS.

It does only what InSim.txt says LFS does, so the connection code can be tested without the game:

- after IS_ISI with a non-zero ReqI, it sends IS_VER;
- TINY_VER is answered with IS_VER, TINY_PING with TINY_REPLY (same ReqI);
- TINY_CLOSE closes the connection;
- with `keepalive`, it sends a blank IS_TINY (TINY_NONE) every `keepalive` seconds;
- with `timeout`, it closes the connection when nothing arrives for that long (LFS: 70 s).

Assumed, not in InSim.txt (checked against the real LFS in W3.1): a wrong admin password closes
the connection without an answer.

Every packet it receives is kept in `received`; `send()` sends to the connected program, and
`drop()` cuts the connection as if LFS had crashed.
"""

from __future__ import annotations

import asyncio
import contextlib
from types import TracebackType
from typing import Self, TypeVar

from lfs_insim._stream import PacketStream
from lfs_insim.packets import IS_ISI, IS_TINY, IS_VER, TINY
from lfs_insim.packets._codec import InSimPacket

P = TypeVar("P", bound=InSimPacket)


class FakeLFS:
    """`async with FakeLFS() as lfs:` starts it on a free port (`lfs.port`); leaving stops it."""

    def __init__(
        self,
        *,
        version: str = "0.8C31",
        product: str = "S3",
        insim_ver: int = 10,
        admin: str = "",
        keepalive: float | None = None,
        timeout: float | None = None,
    ) -> None:
        self.version = version
        self.product = product
        self.insim_ver = insim_ver
        self.admin = admin
        self.keepalive = keepalive
        self.timeout = timeout
        self.received: list[InSimPacket] = []
        self.connections = 0
        """How many times a program has connected."""
        self._server: asyncio.Server | None = None
        self._port = 0
        self._writer: asyncio.StreamWriter | None = None
        self._changed = asyncio.Condition()
        self._taken: dict[type[InSimPacket], int] = {}

    @property
    def port(self) -> int:
        assert self._port, "the fake LFS has never been started"
        return self._port

    @property
    def connected(self) -> bool:
        return self._writer is not None

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.stop()

    async def start(self) -> None:
        """Listen again, on the same port as before (a free one the first time)."""
        self._server = await asyncio.start_server(self._serve, "127.0.0.1", self._port)
        self._port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        """Stop listening and drop the connection, as if LFS had been closed."""
        server, self._server = self._server, None  # from now on, _serve refuses connections
        if server is not None:
            server.close()
        await self.drop()
        if server is not None:
            await server.wait_closed()  # waits for every connection it accepted to end

    async def send(self, *packets: InSimPacket) -> None:
        """Send packets to the connected program."""
        assert self._writer is not None, "no program is connected"
        self._writer.write(b"".join(packet.pack() for packet in packets))
        await self._writer.drain()

    async def send_raw(self, data: bytes) -> None:
        """Send bytes as they are: half packets, broken ones..."""
        assert self._writer is not None, "no program is connected"
        self._writer.write(data)
        await self._writer.drain()

    async def drop(self) -> None:
        """Cut the connection, as if LFS had been closed."""
        writer, self._writer = self._writer, None
        if writer is not None:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
            await self._notify()

    async def wait_for(self, cls: type[P], timeout: float = 2.0) -> P:
        """The next packet of this class that the program sent (each one is returned once)."""

        def found() -> P | None:
            matches = [packet for packet in self.received if isinstance(packet, cls)]
            taken = self._taken.get(cls, 0)
            if len(matches) > taken:
                self._taken[cls] = taken + 1
                return matches[taken]
            return None

        async with asyncio.timeout(timeout), self._changed:
            while (packet := found()) is None:
                await self._changed.wait()
            return packet

    async def wait_connected(self, connections: int = 1, timeout: float = 2.0) -> None:
        """Wait until the program has connected this many times in all, and is connected."""
        async with asyncio.timeout(timeout), self._changed:
            await self._changed.wait_for(lambda: self.connections >= connections and self.connected)

    async def wait_disconnected(self, timeout: float = 2.0) -> None:
        async with asyncio.timeout(timeout), self._changed:
            await self._changed.wait_for(lambda: not self.connected)

    async def _notify(self) -> None:
        async with self._changed:
            self._changed.notify_all()

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        # One program at a time is enough for the tests; and none once stop() has begun.
        if self._writer is not None or self._server is None:
            writer.close()
            return
        self._writer = writer
        self.connections += 1
        await self._notify()
        keepalive: asyncio.Task[None] | None = None
        stream = PacketStream()
        try:
            while self._writer is writer:
                async with asyncio.timeout(self.timeout):
                    data = await reader.read(4096)
                if not data:
                    break
                for packet in stream.feed(data):
                    self.received.append(packet)
                    await self._notify()
                    if not await self._answer(packet):
                        return
                    if isinstance(packet, IS_ISI) and self.keepalive and keepalive is None:
                        keepalive = asyncio.create_task(self._keep_alive(writer))
        except (TimeoutError, ConnectionError):
            pass
        finally:
            if keepalive is not None:
                keepalive.cancel()
            if self._writer is writer:
                await self.drop()

    async def _answer(self, packet: InSimPacket) -> bool:
        """Reply as LFS would. False means LFS closes the connection."""
        if isinstance(packet, IS_ISI):
            if packet.Admin != self.admin:
                return False
            if packet.ReqI:
                await self.send(self._ver(packet.ReqI))
        elif isinstance(packet, IS_TINY):
            if packet.SubT == TINY.CLOSE:
                return False
            if packet.SubT == TINY.VER:
                await self.send(self._ver(packet.ReqI))
            elif packet.SubT == TINY.PING:
                await self.send(IS_TINY(ReqI=packet.ReqI, SubT=TINY.REPLY))
        return True

    def _ver(self, req_i: int) -> IS_VER:
        return IS_VER(
            ReqI=req_i, Version=self.version, Product=self.product, InSimVer=self.insim_ver
        )

    async def _keep_alive(self, writer: asyncio.StreamWriter) -> None:
        assert self.keepalive is not None
        while self._writer is writer:
            await asyncio.sleep(self.keepalive)
            if self._writer is writer:
                await self.send(IS_TINY(ReqI=0, SubT=TINY.NONE))
