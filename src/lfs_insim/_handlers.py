"""Handlers registered by packet type: shared by InSim, OutSim and OutGauge."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger("lfs_insim")


class Handlers:
    """The handlers of each packet type, and the tasks of the `async def` ones still running."""

    def __init__(self) -> None:
        self._by_type: dict[type[Any], list[Callable[..., Any]]] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def add(self, packet_type: type[Any], handler: Callable[..., Any]) -> None:
        self._by_type.setdefault(packet_type, []).append(handler)

    def dispatch(self, packet: Any) -> None:
        """Call every handler of the packet's type, in the order they were registered."""
        for handler in self._by_type.get(type(packet), []):
            self.call(handler, (packet,), type(packet).__name__)

    def call(self, handler: Callable[..., Any], args: tuple[Any, ...], event: str) -> None:
        """Run a handler: a `def` now, an `async def` as a task. Errors are logged, not raised."""
        try:
            result = handler(*args)
        except Exception:
            log.exception("handler %s failed on %s", _name(handler), event)
            return
        if inspect.isawaitable(result):
            task = asyncio.ensure_future(result)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            task.add_done_callback(functools.partial(_report, handler, event))

    async def repeat(
        self, seconds: float, handler: Callable[[], Any], running: Callable[[], bool]
    ) -> None:
        """Call a handler every `seconds` while `running()`; an `async def` one is awaited.

        Errors are logged and the next call still comes. A call that takes too long does not
        cause a burst of calls to catch up: the missed ones are skipped.
        """
        loop = asyncio.get_running_loop()
        due = loop.time() + seconds
        while True:
            await asyncio.sleep(due - loop.time())
            if not running():
                return
            try:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                log.exception("handler %s failed on every(%s)", _name(handler), seconds)
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


def _report(handler: Callable[..., Any], event: str, task: asyncio.Future[Any]) -> None:
    if not task.cancelled() and (error := task.exception()) is not None:
        log.error("handler %s failed on %s", _name(handler), event, exc_info=error)
