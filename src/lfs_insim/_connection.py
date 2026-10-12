"""The InSim connection: TCP to LFS, the IS_ISI greeting and handlers for each packet type."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Self, TypeVar

from lfs_insim._handlers import Handlers
from lfs_insim._stream import PacketStream
from lfs_insim.packets import IS_ISI, IS_TINY, IS_VER, TINY, PacketError
from lfs_insim.packets._codec import InSimPacket

log = logging.getLogger("lfs_insim")

INSIM_VERSION = 10
"""The InSim version this library speaks (INSIM_VERSION in InSim.txt)."""

SILENCE_TIMEOUT = 70.0
"""Seconds without data after which the connection is taken for dead. LFS sends a keepalive
packet every 30 s, and itself closes a connection that is silent for 70 s (InSim.txt)."""

RETRY_DELAYS = (1.0, 2.0, 4.0, 8.0, 10.0)
"""Seconds between attempts to reach LFS; the last one repeats for as long as LFS is away."""

P = TypeVar("P", bound=InSimPacket)
Handler = Callable[[P], None] | Callable[[P], Awaitable[None]]
ConnectHandler = Callable[[], None] | Callable[[], Awaitable[None]]


class InSim:
    """A connection to LFS over InSim (TCP).

    Register handlers with `@insim.on(IS_XXX)`, then call `insim.run()`. From code that already
    runs an asyncio event loop, use `async with insim:` instead. Both keep the connection up: if
    LFS is not running yet, or closes, they try again until `close()` (or Ctrl+C).
    """

    def __init__(
        self,
        name: str = "lfs_insim",
        admin_password: str = "",
        *,
        host: str = "127.0.0.1",
        port: int = 29999,
        flags: int = 0,
        interval_ms: int = 0,
        prefix: str = "",
    ) -> None:
        """Prepare the connection; nothing is sent until it is opened.

        name: a short name for your program, shown in LFS (up to 15 characters).
        admin_password: the admin password, if one is set in LFS.
        host, port: where LFS listens (`/insim 29999` in LFS opens the port).
        flags: ISF options, e.g. `ISF.MCI | ISF.LOCAL`.
        interval_ms: time between IS_MCI or IS_NLP packets (0 = none).
        prefix: the special host message prefix character, e.g. "!".
        """
        if len(prefix) > 1:
            raise ValueError(f"prefix must be one character, not {prefix!r}")
        self.host = host
        self.port = port
        self._isi = IS_ISI(
            ReqI=1,  # non-zero: LFS answers with IS_VER
            Flags=flags,
            InSimVer=INSIM_VERSION,
            Prefix=ord(prefix) if prefix else 0,
            Interval=interval_ms,
            Admin=admin_password,
            IName=name,
        )
        self._isi.pack()  # fail now, not when connecting, if a name is too long
        self._handlers = Handlers()
        self._connect_handlers: list[ConnectHandler] = []
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._supervisor: asyncio.Task[None] | None = None
        self._accepted = False  # LFS answered IS_ISI with IS_VER on this connection
        self._silence_timeout = SILENCE_TIMEOUT
        self._retry_delays: tuple[float, ...] = RETRY_DELAYS

    def on(self, packet_type: type[P]) -> Callable[[Handler[P]], Handler[P]]:
        """Decorator: call the function with every packet of this type that LFS sends.

        The function may be `def` (it runs at once, so it should be quick) or `async def` (it
        runs as a task and may await). An exception in it is logged and does not stop the others.
        """

        def register(handler: Handler[P]) -> Handler[P]:
            self._handlers.add(packet_type, handler)
            return handler

        return register

    def on_connect(self, handler: ConnectHandler) -> ConnectHandler:
        """Decorator: call the function (no arguments) after every connection and reconnection.

        IS_ISI has been sent, so it may send requests: the place to ask LFS for the initial state.
        """
        self._connect_handlers.append(handler)
        return handler

    @property
    def connected(self) -> bool:
        return self._writer is not None

    def send(self, *packets: InSimPacket) -> None:
        """Send packets to LFS. Raises ConnectionError if there is no connection."""
        if self._writer is None:
            raise ConnectionError("not connected to LFS")
        self._writer.write(b"".join(packet.pack() for packet in packets))

    async def connect(self) -> None:
        """Connect once and send IS_ISI; packets are then dispatched in the background.

        Raises OSError if LFS cannot be reached, and does not reconnect: for that, use
        `async with insim:` or `run()`.
        """
        reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self._accepted = False
        self.send(self._isi)
        self._reader_task = asyncio.create_task(self._read(reader))

    async def close(self) -> None:
        """Stop reconnecting, send TINY_CLOSE, close the connection, cancel running handlers."""
        supervisor, self._supervisor = self._supervisor, None
        if supervisor is not None and supervisor is not asyncio.current_task():
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)
        if self._writer is not None:
            self.send(IS_TINY(ReqI=0, SubT=TINY.CLOSE))
        task, self._reader_task = self._reader_task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._disconnect()
        await self._handlers.cancel()

    async def wait_closed(self) -> None:
        """Wait until close() is called (or, after a bare connect(), until the connection ends)."""
        task = self._supervisor or self._reader_task
        if task is not None:
            await asyncio.wait([task])

    def run(self) -> None:
        """Connect, reconnecting whenever needed, and dispatch packets until Ctrl+C or close()."""
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self._run())

    async def _run(self) -> None:
        async with self:
            await self.wait_closed()

    async def __aenter__(self) -> Self:
        """Start keeping the connection up in the background; returns without waiting for LFS."""
        self._supervisor = asyncio.create_task(self._keep_connected())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _keep_connected(self) -> None:
        failures = 0  # attempts since LFS last accepted the connection
        while True:
            try:
                await self.connect()
            except OSError as error:
                if failures == 0:
                    log.warning(
                        "LFS is not answering at %s:%d (%s); trying again until it does",
                        self.host,
                        self.port,
                        error,
                    )
            else:
                log.info("connected to LFS at %s:%d", self.host, self.port)
                for handler in self._connect_handlers:
                    self._handlers.call(handler, (), "on_connect")
                if self._reader_task is not None:
                    await asyncio.wait([self._reader_task])
                if self._accepted:
                    failures = 0
                else:
                    log.warning(
                        "LFS closed the connection before answering IS_ISI "
                        "(a wrong admin password?)"
                    )
            delay = self._retry_delays[min(failures, len(self._retry_delays) - 1)]
            failures += 1
            await asyncio.sleep(delay)

    async def _read(self, reader: asyncio.StreamReader) -> None:
        stream = PacketStream()
        try:
            while True:
                async with asyncio.timeout(self._silence_timeout):
                    data = await reader.read(4096)
                if not data:
                    break
                for packet in stream.feed(data):
                    self._dispatch(packet)
        except PacketError as error:
            log.error("closing the connection to LFS: %s", error)
        except TimeoutError:
            log.warning(
                "no data from LFS for %s s: the connection is taken for dead", self._silence_timeout
            )
        except ConnectionError as error:
            log.warning("the connection to LFS was lost: %s", error)
        finally:
            await self._disconnect()

    async def _disconnect(self) -> None:
        writer, self._writer = self._writer, None
        if writer is not None:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    def _dispatch(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_TINY) and packet.SubT == TINY.NONE and packet.ReqI == 0:
            self.send(IS_TINY(ReqI=0, SubT=TINY.NONE))  # keepalive: LFS expects the same back
        elif isinstance(packet, IS_VER):
            self._accepted = True
        self._handlers.dispatch(packet)
