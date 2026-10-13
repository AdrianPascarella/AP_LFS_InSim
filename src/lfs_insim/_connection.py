"""The InSim connection: TCP to LFS, the IS_ISI greeting and handlers for each packet type."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self, cast

from lfs_insim import _requests
from lfs_insim._commands import Allow, CommandGroup, CommandHandler, Commands
from lfs_insim._events import P
from lfs_insim._handlers import Errors, Handlers, StopsOnError
from lfs_insim._shortcuts import On, Send
from lfs_insim._stream import PacketStream
from lfs_insim.packets import (
    IS_ISI,
    IS_MSL,
    IS_MSO,
    IS_MST,
    IS_MSX,
    IS_MTC,
    IS_TINY,
    IS_VER,
    TINY,
    PacketError,
)
from lfs_insim.packets._directions import InstructionPacket
from lfs_insim.packets._structure import InSimPacket

log = logging.getLogger("lfs_insim")

INSIM_VERSION = 10
"""The InSim version this library speaks (INSIM_VERSION in InSim.txt)."""

SILENCE_TIMEOUT = 70.0
"""Seconds without data after which the connection is taken for dead. LFS sends a keepalive
packet every 30 s, and itself closes a connection that is silent for 70 s (InSim.txt)."""

RETRY_DELAYS = (1.0, 2.0, 4.0, 8.0, 10.0)
"""Seconds between attempts to reach LFS; the last one repeats for as long as LFS is away."""

ConnectHandler = Callable[[], None] | Callable[[], Awaitable[None]]
PacketWatcher = Callable[[InSimPacket], None]


class InSim(StopsOnError):
    """A connection to LFS over InSim (TCP).

    Register handlers with `@insim.on.IS_XXX`, then call `insim.run()`. From code that already
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
        errors: Errors = "log",
    ) -> None:
        """Prepare the connection; nothing is sent until it is opened.

        name: a short name for your program, shown in LFS (up to 15 characters).
        admin_password: the admin password, if one is set in LFS.
        host, port: where LFS listens (`/insim 29999` in LFS opens the port).
        flags: ISF options, e.g. `ISF.MCI | ISF.LOCAL`.
        interval_ms: time between IS_MCI or IS_NLP packets (0 = none).
        prefix: the special host message prefix character, e.g. "!".
        errors: what happens when a handler fails. "log" (the default): the error is logged and
            everything goes on. "raise", for development: the first error closes the connection
            and is raised again by `run()`, `wait_closed()` and `async with`.
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
        self._handlers = Handlers(errors, self._fail)
        self._commands = Commands(prefix, self._make_roster)
        self._requests = _requests.Requests()
        self._connect_handlers: list[ConnectHandler] = []
        self._disconnect_handlers: list[ConnectHandler] = []
        self._connections = 0  # connections opened by `async with` / run(), for `reconnected`
        self._announced = False  # on_connect ran for this connection, so on_disconnect will
        self._every: list[tuple[float, ConnectHandler]] = []
        self._ticks: list[asyncio.Task[None]] = []  # the every() loops of this connection
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._supervisor: asyncio.Task[None] | None = None
        self._accepted = False  # LFS answered IS_ISI with IS_VER on this connection
        self._silence_timeout = SILENCE_TIMEOUT
        self._retry_delays: tuple[float, ...] = RETRY_DELAYS
        self._watch_before: list[PacketWatcher] = []
        self._watch_after: list[PacketWatcher] = []
        self.on = On(self._handlers.add)
        """Handlers: `@insim.on.IS_NPL` (the editor lists what LFS sends), or `@insim.on(IS_NPL)`.

        The function gets the packet; it may be `def` (it runs at once, so it should be quick) or
        `async def` (it runs as a task and may await). An exception in it is logged and does not
        stop the others. Packets that LFS never sends raise TypeError.
        """
        self.send = Send(self._write)
        """Send: `insim.send.IS_MST(Msg="hi")` (the editor lists what a program sends), or
        `insim.send(IS_MST(Msg="hi"), ...)` for packets already built, several at once.

        Raises ConnectionError if there is no connection, and TypeError for packets that only
        LFS sends.
        """

    def on_command(
        self, name: str, *, admin: bool = False, allow: Allow | None = None
    ) -> Callable[[CommandHandler], CommandHandler]:
        """Decorator: call the function when someone types the prefix and this name in the chat.

        With `InSim(prefix="!")`, `@insim.on_command("kick")` is called for "!kick Bob" with a
        Command first: `command.reply("...")` answers only who typed it. The parameters after it
        are the words typed, converted to their annotation (str, int or float; a `*rest` takes
        the remaining ones): `def kick(command: Command, name: str, minutes: int = 5)`. Words
        that do not fit are answered with the usage, and "!kick ?" with the usage and the first
        line of the docstring. A function of only the Command gets any words in `command.args`.

        admin=True: only LFS admins and the host (UCID 0) may use it. allow: a function of the
        Command that says who else may not (False). The name is matched in any case. `def` or
        `async def`, as for `on()`; the IS_MSO still reaches the IS_MSO handlers. A command
        without a function is left alone (it may be for another program).
        """
        return self._commands.register(name, admin, allow)

    def command_group(
        self, name: str, *, admin: bool = False, allow: Allow | None = None
    ) -> CommandGroup:
        """Commands under one name: `aic = insim.command_group("aic")`, then
        `@aic.on_command("start")` for "!aic start". "!aic" alone lists them. admin and allow
        apply to every command of the group, as in on_command.
        """
        return self._commands.group(name, admin, allow)

    def _make_roster(self) -> Any:
        from lfs_insim.state import Roster  # state imports this module

        return Roster(self)

    def on_connect(self, handler: ConnectHandler) -> ConnectHandler:
        """Decorator: call the function (no arguments) after every connection and reconnection.

        IS_ISI has been sent, so it may send requests: the place to ask LFS for the initial state.
        """
        self._connect_handlers.append(handler)
        return handler

    def on_disconnect(self, handler: ConnectHandler) -> ConnectHandler:
        """Decorator: call the function (no arguments) when a connection ends.

        Once for each on_connect: when LFS closes or is lost, and when you close. The connection
        is already gone, so it cannot send; a reconnection follows unless you closed. An
        `async def` one is awaited, also when closing.
        """
        self._disconnect_handlers.append(handler)
        return handler

    def watch(
        self, *, before: PacketWatcher | None = None, after: PacketWatcher | None = None
    ) -> None:
        """See every packet from LFS before and after the handlers: to keep state they read.

        `before(packet)` runs before the answers to request() and the handlers, so they see the
        state with the packet in it; `after(packet)` runs after the handlers (and after the first
        step of the `async def` ones), so they still see the state from before, as Roster does
        when someone leaves. Both must be plain `def`: they run to the end, in the order given.
        """
        if before is None and after is None:
            raise TypeError("watch() needs before=, after= or both")
        for name, watcher in (("before", before), ("after", after)):
            if inspect.iscoroutinefunction(watcher):
                raise TypeError(f"watch({name}=...) must be a plain def, not async def")
        if before is not None:
            self._watch_before.append(before)
        if after is not None:
            self._watch_after.append(after)

    @property
    def reconnected(self) -> bool:
        """True from the second connection on: in on_connect, whether this is a reconnection."""
        return self._connections > 1

    def every(self, seconds: float) -> Callable[[ConnectHandler], ConnectHandler]:
        """Decorator: call the function (no arguments) every `seconds` while connected to LFS.

        It starts when LFS accepts the connection, stops when it ends and starts again after a
        reconnection, so it may always send. The function may be `def` or `async def` (awaited
        before the next call, so calls never overlap). A call that takes too long skips the
        missed ones instead of catching up. An exception in it is logged and the next call comes.
        """
        if seconds <= 0:
            raise ValueError(f"every() needs a positive number of seconds, not {seconds}")

        def register(handler: ConnectHandler) -> ConnectHandler:
            self._every.append((seconds, handler))
            return handler

        return register

    @property
    def connected(self) -> bool:
        return self._writer is not None

    def _write(self, packets: tuple[InstructionPacket, ...]) -> None:
        if self._writer is None:
            raise ConnectionError("not connected to LFS")
        self._writer.write(b"".join(packet.pack() for packet in packets))

    def say(self, text: str, *, to: int | None = None) -> None:
        """Write in the chat, as if typed in LFS: `insim.say("Hello")`. Everyone sees it.

        With `to=UCID` only that connection sees it: `to=0` is this computer (IS_MSL, in single
        player too); another UCID needs LFS to be a multiplayer host (IS_MTC; 255 = everyone).
        The limit counts bytes as LFS stores them: 95 for the chat (63 goes as IS_MST, longer
        as IS_MSX), 127 with `to`; longer text raises PacketError (a ValueError). For commands
        such as /restart, use command().
        """
        packet: InSimPacket
        if to == 0:
            packet = IS_MSL(Msg=text)  # LFS refuses IS_MTC in single player ("only for hosts")
        elif to is not None:
            packet = IS_MTC(UCID=to, Text=text)
        elif text.startswith("/"):
            raise ValueError(f"{text!r} is a command: use insim.command() to send it")
        else:
            packet = IS_MST(Msg=text)
            try:
                packet.pack()
            except PacketError:
                packet = IS_MSX(Msg=text)
        packet.pack()  # too long: fail here, even without a connection
        self.send(packet)

    def command(self, command: str) -> None:
        """Run an LFS command, as if typed in LFS: `insim.command("/restart")`.

        Up to 63 bytes (IS_MST); longer raises PacketError (a ValueError). LFS answers commands
        sent this way with IS_ACR when it is the host.
        """
        if not command.startswith("/"):
            raise ValueError(f"{command!r} is not a command (they start with /): use insim.say()")
        packet = IS_MST(Msg=command)
        packet.pack()
        self.send(packet)

    async def request(self, reply: type[P], *, timeout: float | None = 2.0) -> P:
        """Ask LFS for a packet and wait for it: `state = await insim.request(IS_STA)`.

        Sends the IS_TINY that asks for it (TINY_SST for IS_STA, TINY_VER for IS_VER...); the
        answer also reaches the `@insim.on` handlers. Raises TimeoutError if LFS does not answer
        within `timeout` seconds, ConnectionError if there is no connection or it is lost while
        waiting, and TypeError for a packet that LFS does not send on request, or sends in
        several parts (those are for request_all).
        """
        sub = _requests.SINGLE.get(reply)
        if sub is None:
            raise TypeError(_requests.wrong_function(reply, "request"))
        with self._requests.waiting(reply) as (req_i, waiting):
            self.send(IS_TINY(ReqI=req_i, SubT=sub))
            return cast(P, await _requests.answer(waiting, timeout))

    async def request_all(self, reply: type[P], *, quiet: float = 0.5) -> list[P]:
        """Ask LFS for packets that come in several: `players = await insim.request_all(IS_NPL)`.

        For IS_NCN, IS_NPL, IS_RES, IS_NCI, IS_SLC, IS_MCI and IS_AXM. Returns when as many have
        arrived as the packets themselves say (Total in IS_NCN, NumP in IS_NPL, NumRes in
        IS_RES), or when none has arrived for `quiet` seconds: an empty list if LFS has nothing
        to send (no results before anyone finishes, say). The answers also reach the handlers.
        Raises ConnectionError and TypeError as request() does.
        """
        entry = _requests.MULTI.get(reply)
        if entry is None:
            raise TypeError(_requests.wrong_function(reply, "request_all"))
        sub, counter = entry
        answers: list[P] = []
        with self._requests.waiting(reply) as (req_i, waiting):
            self.send(IS_TINY(ReqI=req_i, SubT=sub))
            while True:
                try:
                    packet = await _requests.answer(waiting, quiet)
                except TimeoutError:
                    return answers
                answers.append(cast(P, packet))
                if counter is not None and len(answers) >= getattr(packet, counter):
                    return answers

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
        """Stop reconnecting, send TINY_CLOSE, close the connection, cancel running handlers.

        A second call waits for the first. The handler that calls it is not cancelled.
        """
        await super().close()

    async def _close(self, caller: asyncio.Task[Any] | None) -> None:
        await self._stop_ticks(caller)  # first: one of them may be the caller (see _stop_ticks)
        supervisor, self._supervisor = self._supervisor, None
        if supervisor is not None and supervisor is not caller:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)
        if self._writer is not None:
            self.send(IS_TINY(ReqI=0, SubT=TINY.CLOSE))
        task, self._reader_task = self._reader_task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._disconnect()
        await self._handlers.cancel(caller)

    async def wait_closed(self) -> None:
        """Wait until close() is called (or, after a bare connect(), until the connection ends).

        With errors="raise", it raises the error of the handler that closed it.
        """
        task = self._supervisor or self._reader_task
        if task is not None:
            await asyncio.wait([task])
        await self._raise_error()

    def run(self) -> None:
        """Connect, reconnecting whenever needed, and dispatch packets until Ctrl+C or close()."""
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self._run())

    async def _run(self) -> None:
        async with self:
            await self.wait_closed()

    async def __aenter__(self) -> Self:
        """Start keeping the connection up in the background; returns without waiting for LFS."""
        self._closing = None
        self._supervisor = asyncio.create_task(self._keep_connected())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._exit(exc)

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
                self._connections += 1
                self._announced = True
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
                    # Let this packet's async handlers take their first step and its after
                    # watchers run before the next packet read in the same chunk.
                    await asyncio.sleep(0)
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

    def _start_ticks(self) -> None:
        writer = self._writer

        def running() -> bool:  # still the connection this tick was started for
            return writer is not None and self._writer is writer

        for seconds, handler in self._every:
            tick = self._handlers.repeat(seconds, handler, running)
            self._ticks.append(asyncio.create_task(tick))

    async def _stop_ticks(self, keep: asyncio.Task[Any] | None = None) -> None:
        # The caller's own tick (if close() is called from one: `keep`) is not cancelled: it ends
        # by itself, because the connection it was started for is gone.
        ticks, self._ticks = self._ticks, []
        ticks = [tick for tick in ticks if tick not in (keep, asyncio.current_task())]
        for tick in ticks:
            tick.cancel()
        await asyncio.gather(*ticks, return_exceptions=True)

    async def _disconnect(self) -> None:
        await self._stop_ticks()
        writer, self._writer = self._writer, None
        if writer is not None:
            self._requests.fail(ConnectionError("the connection to LFS was lost"))
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
            if self._announced:
                self._announced = False
                self._in_closing = True  # a close() in them must not wait for this
                try:
                    for handler in self._disconnect_handlers:
                        await self._handlers.call_and_wait(handler, (), "on_disconnect")
                finally:
                    self._in_closing = False

    def _dispatch(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_TINY) and packet.SubT == TINY.NONE and packet.ReqI == 0:
            self.send(IS_TINY(ReqI=0, SubT=TINY.NONE))  # keepalive: LFS expects the same back
        elif isinstance(packet, IS_VER) and not self._accepted:
            self._accepted = True
            self._start_ticks()
        for before in self._watch_before:
            self._handlers.call(before, (packet,), f"{type(packet).__name__} (before handlers)")
        self._requests.deliver(packet)
        self._handlers.dispatch(packet)
        if isinstance(packet, IS_MSO):
            self._commands.handle(packet, self._handlers, self.say)
        # After the handlers, and after the first step of the async ones: their tasks were
        # scheduled first, so until their first await they still see the state before the packet.
        loop = asyncio.get_running_loop()
        for after in self._watch_after:
            loop.call_soon(self._handlers.call, after, (packet,), type(packet).__name__)
