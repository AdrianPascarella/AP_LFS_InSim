"""Handlers registered by packet type: shared by InSim, OutSim and OutGauge."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any, Literal

log = logging.getLogger("lfs_insim")

Errors = Literal["log", "raise"]
"""What a failing handler does: "log" (logged, the rest goes on) or "raise" (everything stops)."""


def check_errors(errors: object) -> None:
    if errors not in ("log", "raise"):
        raise ValueError(f"errors must be 'log' or 'raise', not {errors!r}")


class Handlers:
    """The handlers of each packet type, and the tasks of the `async def` ones still running."""

    def __init__(
        self, errors: Errors = "log", fail: Callable[[Exception], None] | None = None
    ) -> None:
        check_errors(errors)
        self.errors = errors
        self._fail = fail  # with errors="raise": called once, with the first error
        self.error: Exception | None = None
        """With errors="raise", the first error of a handler; after it, no handler runs."""
        # (handler, subtypes): subtypes is None, or the SubT values that the handler wants
        self._by_type: dict[type[Any], list[tuple[Callable[..., Any], frozenset[int] | None]]] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def add(
        self,
        packet_type: type[Any],
        handler: Callable[..., Any],
        subtypes: frozenset[int] | None = None,
    ) -> None:
        self._by_type.setdefault(packet_type, []).append((handler, subtypes))

    def dispatch(self, packet: Any) -> None:
        """Call every handler of the packet's type, in the order they were registered.

        A handler registered for some subtypes (SubT) is skipped for the others.
        """
        for handler, subtypes in self._by_type.get(type(packet), []):
            if subtypes is not None and packet.SubT not in subtypes:
                continue
            self.call(handler, (packet,), type(packet).__name__)

    def call(self, handler: Callable[..., Any], args: tuple[Any, ...], event: str) -> None:
        """Run a handler: a `def` now, an `async def` as a task. Errors: see _failed."""
        if self.error is not None:
            return
        try:
            result = handler(*args)
        except Exception as error:
            self._failed(handler, event, error)
            return
        if inspect.isawaitable(result):
            task = asyncio.ensure_future(result)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            task.add_done_callback(functools.partial(self._report, handler, event))

    async def call_and_wait(
        self, handler: Callable[..., Any], args: tuple[Any, ...], event: str
    ) -> None:
        """Run a handler and, if it is `async def`, wait for it. Errors: see _failed."""
        if self.error is not None:
            return
        try:
            result = handler(*args)
            if inspect.isawaitable(result):
                await result
        except Exception as error:
            self._failed(handler, event, error)

    def _failed(self, handler: Callable[..., Any], event: str, error: Exception) -> None:
        """Log the error; with errors="raise", keep the first one and tell the owner to close."""
        log.error("handler %s failed on %s", _name(handler), event, exc_info=error)
        if self.errors == "raise" and self.error is None:
            self.error = error
            if self._fail is not None:
                self._fail(error)

    def _report(self, handler: Callable[..., Any], event: str, task: asyncio.Future[Any]) -> None:
        if not task.cancelled() and isinstance(error := task.exception(), Exception):
            self._failed(handler, event, error)

    async def repeat(
        self, seconds: float, handler: Callable[[], Any], running: Callable[[], bool]
    ) -> None:
        """Call a handler every `seconds` while `running()`; an `async def` one is awaited.

        After an error the next call still comes (unless errors="raise"). A call that takes too
        long does not cause a burst of calls to catch up: the missed ones are skipped.
        """
        loop = asyncio.get_running_loop()
        due = loop.time() + seconds
        while True:
            await asyncio.sleep(due - loop.time())
            if not running():
                return
            await self.call_and_wait(handler, (), f"every({seconds})")
            if self.error is not None:
                return
            due += seconds
            if due < loop.time():
                due = loop.time() + seconds

    async def cancel(self) -> None:
        """Cancel the `async def` handlers still running (except the caller) and wait for them."""
        tasks = [task for task in self._tasks if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _name(handler: Callable[..., Any]) -> str:
    return getattr(handler, "__qualname__", repr(handler))


class StopsOnError:
    """InSim, OutSim and OutGauge: with errors="raise", a handler's error closes them.

    `wait_closed()` and leaving `async with` then raise that error (and so does run()).
    """

    _handlers: Handlers
    _closing: asyncio.Task[None] | None = None  # the close() started by an error

    async def close(self) -> None:
        raise NotImplementedError

    def _fail(self, error: Exception) -> None:
        if self._closing is None:
            self._closing = asyncio.ensure_future(self.close())

    async def _raise_error(self) -> None:
        if self._closing is not None:
            await asyncio.wait([self._closing])
        if self._handlers.error is not None:
            raise self._handlers.error

    async def _exit(self, exc: BaseException | None) -> None:
        """The end of `async with`: close, and raise the handler's error if nothing else is."""
        if self._closing is not None:
            await asyncio.wait([self._closing])
        await self.close()
        if exc is None:
            await self._raise_error()
