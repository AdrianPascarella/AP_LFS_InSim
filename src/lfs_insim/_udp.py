"""OutSim and OutGauge: the UDP packets LFS sends to a port, with handlers like InSim's."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self, TypeVar

from lfs_insim import packets as _p
from lfs_insim._handlers import Errors, Handlers, StopsOnError
from lfs_insim._run import run
from lfs_insim.packets import OutGaugePack, OutSimPack, OutSimPack2, PacketError
from lfs_insim.packets._structure import Structure

log = logging.getLogger("lfs_insim")

S = TypeVar("S", OutSimPack, OutSimPack2)
UDPHandler = Callable[[S], None] | Callable[[S], Awaitable[None]]
GaugeHandler = Callable[[OutGaugePack], None] | Callable[[OutGaugePack], Awaitable[None]]


class _UDPSource(StopsOnError):
    """What OutSim and OutGauge share: listen on a UDP port and hand each packet to handlers."""

    def __init__(self, port: int, host: str, errors: Errors) -> None:
        self.host = host
        self.port = port
        self._handlers = Handlers(errors, self._fail)
        self._transport: asyncio.DatagramTransport | None = None
        self._closed: asyncio.Event | None = None
        self._reported = False  # a bad datagram was logged, and no good one has arrived since

    def _read(self, data: bytes) -> Structure:
        raise NotImplementedError

    async def close(self) -> None:
        """Stop listening and cancel running handlers. A second call waits for the first."""
        await super().close()

    async def _close(self, caller: asyncio.Task[Any] | None) -> None:
        transport, self._transport = self._transport, None
        if transport is not None:
            transport.close()
        await self._handlers.cancel(caller)
        if self._closed is not None:
            self._closed.set()

    async def wait_closed(self) -> None:
        """Wait until close() is called. With errors="raise", it raises the handler's error."""
        if self._closed is not None:
            await self._closed.wait()
        await self._raise_error()

    def run(self) -> None:
        """Listen and dispatch packets until Ctrl+C or close()."""
        run(self)

    async def __aenter__(self) -> Self:
        """Start listening. Raises OSError if the port cannot be used (already taken, say)."""
        self._closing = None
        self._closed = asyncio.Event()
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _Protocol(self), local_addr=(self.host, self.port)
        )
        self._transport = transport
        self.port = transport.get_extra_info("sockname")[1]  # the real one, if port was 0
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._exit(exc)

    def _received(self, data: bytes) -> None:
        try:
            packet = self._read(data)
        except PacketError as error:
            if not self._reported:
                log.warning(
                    "%s on port %d: skipping a packet that cannot be read (%s); "
                    "check the %s lines of LFS's cfg.txt",
                    type(self).__name__,
                    self.port,
                    error,
                    type(self).__name__,
                )
                self._reported = True
            return
        self._reported = False
        self._handlers.dispatch(packet)


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, source: _UDPSource) -> None:
        self.source = source

    def datagram_received(self, data: bytes, addr: tuple[str | int, ...]) -> None:
        self.source._received(data)


def _read_fixed(packet_type: type[Structure], data: bytes) -> Structure:
    """Read a packet whose size is fixed, plus 4 bytes when LFS adds the optional ID."""
    size = len(packet_type().pack())
    if len(data) not in (size, size + 4):
        raise PacketError(f"{len(data)} bytes, but {packet_type.__name__} has {size} or {size + 4}")
    return packet_type.unpack(data)


class OutGauge(_UDPSource):
    """The dashboard data LFS sends over UDP (OutGauge lines in LFS's cfg.txt).

    Register handlers with `@gauge.on.OutGaugePack`, then call `gauge.run()`, or
    `run(insim, gauge)` to use it together with InSim.
    """

    def __init__(self, port: int, host: str = "127.0.0.1", *, errors: Errors = "log") -> None:
        """Prepare to listen; nothing happens until it is run.

        port: the "OutGauge Port" of LFS's cfg.txt.
        host: the address to listen on; LFS sends to the "OutGauge IP" of cfg.txt.
        errors: what happens when a handler fails: "log" (the default) or "raise", as in InSim.
        """
        super().__init__(port, host, errors)
        self.on = GaugeOn(self._handlers)
        """Handlers: `@gauge.on.OutGaugePack`, or `@gauge.on(OutGaugePack)`."""

    def _read(self, data: bytes) -> Structure:
        return _read_fixed(OutGaugePack, data)


class OutSim(_UDPSource):
    """The motion data LFS sends over UDP (OutSim lines in LFS's cfg.txt).

    With "OutSim Opts 0" LFS sends OutSimPack; with any other options, OutSimPack2 with only the
    parts those options select. Register handlers with `@outsim.on.OutSimPack` (or
    `.OutSimPack2`), then call `outsim.run()`, or `run(insim, outsim)` together with InSim.
    """

    def __init__(
        self, port: int, host: str = "127.0.0.1", *, options: int = 0, errors: Errors = "log"
    ) -> None:
        """Prepare to listen; nothing happens until it is run.

        port: the "OutSim Port" of LFS's cfg.txt.
        host: the address to listen on; LFS sends to the "OutSim IP" of cfg.txt.
        options: the "OutSim Opts" of cfg.txt (hexadecimal there: `0x1ff`, or `OSO.MAIN | ...`).
        errors: what happens when a handler fails: "log" (the default) or "raise", as in InSim.
        """
        super().__init__(port, host, errors)
        self.options = options
        self.on = OutSimOn(self)
        """Handlers: `@outsim.on.OutSimPack2` (or `.OutSimPack`), or `@outsim.on(OutSimPack2)`."""

    def _read(self, data: bytes) -> Structure:
        if self.options:
            return OutSimPack2.unpack(data, self.options)
        return _read_fixed(OutSimPack, data)


class GaugeOn:
    """Register handlers: `@gauge.on.OutGaugePack`, or `@gauge.on(OutGaugePack)`."""

    def __init__(self, handlers: Handlers) -> None:
        self._handlers = handlers

    def __call__(
        self, packet_type: type[_p.OutGaugePack]
    ) -> Callable[[GaugeHandler], GaugeHandler]:
        """Decorator: call the function with every OutGaugePack.

        The function may be `def` (it runs at once, so it should be quick) or `async def` (it
        runs as a task and may await). An exception in it is logged and does not stop the others.
        """
        if packet_type is not _p.OutGaugePack:
            raise TypeError(f"OutGauge only receives OutGaugePack, not {packet_type.__name__}")

        def register(handler: GaugeHandler) -> GaugeHandler:
            self._handlers.add(packet_type, handler)
            return handler

        return register

    @property
    def OutGaugePack(self) -> Callable[[GaugeHandler], GaugeHandler]:
        """The dashboard data (OutGaugePack): `@gauge.on.OutGaugePack`."""
        return self(_p.OutGaugePack)


class OutSimOn:
    """Register handlers: `@outsim.on.OutSimPack2` (or `.OutSimPack`), or `@outsim.on(...)`."""

    def __init__(self, source: OutSim) -> None:
        self._source = source

    def __call__(self, packet_type: type[S]) -> Callable[[UDPHandler[S]], UDPHandler[S]]:
        """Decorator: call the function with every packet LFS sends.

        The function may be `def` (it runs at once, so it should be quick) or `async def` (it
        runs as a task and may await). An exception in it is logged and does not stop the others.
        With "OutSim Opts 0" LFS sends OutSimPack; with other options, OutSimPack2.
        """
        options = self._source.options
        expected = _p.OutSimPack2 if options else _p.OutSimPack
        if packet_type is not expected:
            raise TypeError(
                f"with options={options:#x}, LFS sends {expected.__name__}, "
                f"not {packet_type.__name__}"
            )

        def register(handler: UDPHandler[S]) -> UDPHandler[S]:
            self._source._handlers.add(packet_type, handler)
            return handler

        return register

    @property
    def OutSimPack(self) -> Callable[[UDPHandler[_p.OutSimPack]], UDPHandler[_p.OutSimPack]]:
        """The car's motion with "OutSim Opts 0" (OutSimPack): `@outsim.on.OutSimPack`."""
        return self(_p.OutSimPack)

    @property
    def OutSimPack2(self) -> Callable[[UDPHandler[_p.OutSimPack2]], UDPHandler[_p.OutSimPack2]]:
        """The car's motion with other options (OutSimPack2): `@outsim.on.OutSimPack2`."""
        return self(_p.OutSimPack2)
