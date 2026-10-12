"""The InSim connection: TCP to LFS, the IS_ISI greeting and handlers for each packet type."""

from __future__ import annotations

import asyncio
import contextlib
import functools
import inspect
import logging
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self, TypeVar

from lfs_insim._stream import PacketStream
from lfs_insim.packets import IS_ISI, PacketError
from lfs_insim.packets._codec import InSimPacket

log = logging.getLogger("lfs_insim")

INSIM_VERSION = 10
"""The InSim version this library speaks (INSIM_VERSION in InSim.txt)."""

P = TypeVar("P", bound=InSimPacket)
Handler = Callable[[P], None] | Callable[[P], Awaitable[None]]


class InSim:
    """A connection to LFS over InSim (TCP).

    Register handlers with `@insim.on(IS_XXX)`, then call `insim.run()`. From code that already
    runs an asyncio event loop, use `async with insim:` instead.
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
        self._handlers: dict[type[InSimPacket], list[Handler[Any]]] = {}
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    def on(self, packet_type: type[P]) -> Callable[[Handler[P]], Handler[P]]:
        """Decorator: call the function with every packet of this type that LFS sends.

        The function may be `def` (it runs at once, so it should be quick) or `async def` (it
        runs as a task and may await). An exception in it is logged and does not stop the others.
        """

        def register(handler: Handler[P]) -> Handler[P]:
            self._handlers.setdefault(packet_type, []).append(handler)
            return handler

        return register

    @property
    def connected(self) -> bool:
        return self._writer is not None

    def send(self, *packets: InSimPacket) -> None:
        """Send packets to LFS. Raises ConnectionError if there is no connection."""
        if self._writer is None:
            raise ConnectionError("not connected to LFS")
        self._writer.write(b"".join(packet.pack() for packet in packets))

    async def connect(self) -> None:
        """Open the connection and send IS_ISI; packets are then dispatched in the background."""
        reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self.send(self._isi)
        self._reader_task = asyncio.create_task(self._read(reader))

    async def close(self) -> None:
        """Close the connection and cancel the async handlers that are still running."""
        task, self._reader_task = self._reader_task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._disconnect()
        handlers = list(self._tasks)
        for handler in handlers:
            handler.cancel()
        await asyncio.gather(*handlers, return_exceptions=True)

    async def wait_closed(self) -> None:
        """Wait until the connection ends (LFS closes it, or close() is called)."""
        if self._reader_task is not None:
            await asyncio.gather(self._reader_task, return_exceptions=True)

    def run(self) -> None:
        """Connect and dispatch packets until LFS closes the connection or Ctrl+C is pressed."""
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self._run())

    async def _run(self) -> None:
        async with self:
            await self.wait_closed()

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _read(self, reader: asyncio.StreamReader) -> None:
        stream = PacketStream()
        try:
            while data := await reader.read(4096):
                for packet in stream.feed(data):
                    self._dispatch(packet)
        except PacketError as error:
            log.error("closing the connection to LFS: %s", error)
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
        for handler in self._handlers.get(type(packet), []):
            try:
                result = handler(packet)
            except Exception:
                log.exception("handler %s failed on %s", _name(handler), type(packet).__name__)
                continue
            if inspect.isawaitable(result):
                task = asyncio.ensure_future(result)
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
                task.add_done_callback(functools.partial(_report, handler, type(packet).__name__))


def _name(handler: Callable[..., Any]) -> str:
    return getattr(handler, "__qualname__", repr(handler))


def _report(handler: Callable[..., Any], packet: str, task: asyncio.Future[Any]) -> None:
    if not task.cancelled() and (error := task.exception()) is not None:
        log.error("handler %s failed on %s", _name(handler), packet, exc_info=error)
