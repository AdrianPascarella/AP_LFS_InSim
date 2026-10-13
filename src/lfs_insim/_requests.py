"""Asking LFS for information and waiting for the answer (internal; used by InSim.request).

An info request is an IS_TINY whose ReqI LFS copies into the answer, so each request gets a
ReqI of its own and the answers are told apart by it. ReqI 1 is left to IS_ISI (its IS_VER), and
0 means "not an answer". The same request asked again while it waits, with nothing arrived from
LFS since it was sent, is not sent again: the askers share its answer (plugins tend to ask for
the same on connecting). Once something has arrived, it may have changed what LFS would answer
(a new host, say), so a new request is sent.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import Any, TypeVar

from lfs_insim.packets import (
    IS_AXI,
    IS_AXM,
    IS_CPP,
    IS_IPB,
    IS_ISM,
    IS_MAL,
    IS_MCI,
    IS_NCI,
    IS_NCN,
    IS_NLP,
    IS_NPL,
    IS_PLH,
    IS_REO,
    IS_RES,
    IS_RIP,
    IS_RST,
    IS_SLC,
    IS_STA,
    IS_VER,
    TINY,
)
from lfs_insim.packets._structure import InSimPacket

SINGLE: dict[type[InSimPacket], TINY] = {
    IS_VER: TINY.VER,
    IS_STA: TINY.SST,
    IS_CPP: TINY.SCP,
    IS_ISM: TINY.ISM,
    IS_NLP: TINY.NLP,
    IS_REO: TINY.REO,
    IS_RST: TINY.RST,
    IS_AXI: TINY.AXI,
    IS_RIP: TINY.RIP,
    IS_MAL: TINY.MAL,
    IS_PLH: TINY.PLH,
    IS_IPB: TINY.IPB,
}
"""Answers that come in one packet, and the TINY that asks for them."""

MULTI: dict[type[InSimPacket], tuple[TINY, str | None]] = {
    IS_NCN: (TINY.NCN, "Total"),  # one per connection, host included
    IS_NPL: (TINY.NPL, "NumP"),  # one per player
    IS_RES: (TINY.RES, "NumRes"),  # one per result; none before anyone finishes
    IS_NCI: (TINY.NCI, None),  # host only
    IS_SLC: (TINY.SLC, None),  # host only
    IS_MCI: (TINY.MCI, None),  # "a set of IS_MCI"
    IS_AXM: (TINY.AXM, None),  # the layout, in as many packets as it needs
}
"""Answers that come in several packets: the TINY, and the field that says how many there are
(without one, the answers are taken as complete when no more arrive for a while)."""

FIRST_REQI = 2

T = TypeVar("T")


@dataclass
class Waiting:
    """One request waiting for its answers."""

    reply: type[InSimPacket]
    answers: asyncio.Queue[InSimPacket | ConnectionError] = field(default_factory=asyncio.Queue)


class Requests:
    """The requests that are waiting, by ReqI."""

    def __init__(self) -> None:
        self._waiting: dict[int, Waiting] = {}
        self._next = FIRST_REQI
        self._shared: dict[object, tuple[asyncio.Future[Any], int]] = {}
        self._arrived = 0  # packets from LFS so far: a shared request is only joined if unchanged

    async def shared(self, key: object, ask: Callable[[], Awaitable[T]]) -> T:
        """The answer to `ask()`, or to the same request (same key) already waiting, if nothing
        has arrived from LFS since it was sent.

        It runs as a task of its own, so one asker giving up (cancelled) does not end it for the
        others; each gets the same answer, or the same error.
        """
        task, arrived = self._shared.get(key, (None, -1))
        if task is None or arrived != self._arrived:
            task = asyncio.ensure_future(ask())
            self._shared[key] = (task, self._arrived)
            task.add_done_callback(lambda done: self._finished(key, done))
        result: T = await asyncio.shield(task)
        return result

    def _finished(self, key: object, task: asyncio.Future[Any]) -> None:
        if self._shared.get(key, (None, 0))[0] is task:
            del self._shared[key]
        if not task.cancelled():
            task.exception()  # retrieved: if every asker gave up, asyncio would complain

    @contextlib.contextmanager
    def waiting(self, reply: type[InSimPacket]) -> Iterator[tuple[int, Waiting]]:
        """Reserve a ReqI for a request until it is finished."""
        req_i = self._free_req_i()
        waiting = self._waiting[req_i] = Waiting(reply)
        try:
            yield req_i, waiting
        finally:
            del self._waiting[req_i]

    def deliver(self, packet: InSimPacket) -> None:
        """Hand a packet from LFS to the request it answers, if any."""
        self._arrived += 1
        waiting = self._waiting.get(getattr(packet, "ReqI", 0))  # every packet has ReqI
        if waiting is not None and isinstance(packet, waiting.reply):
            waiting.answers.put_nowait(packet)

    def fail(self, error: ConnectionError) -> None:
        """The connection is gone: every waiting request ends with this error."""
        for waiting in self._waiting.values():
            waiting.answers.put_nowait(error)

    def _free_req_i(self) -> int:
        for _ in range(256 - FIRST_REQI):
            req_i = self._next
            self._next = req_i + 1 if req_i < 255 else FIRST_REQI
            if req_i not in self._waiting:
                return req_i
        raise RuntimeError("too many requests waiting at once (the limit is 254)")


def wrong_function(reply: type[InSimPacket], function: str) -> str:
    """The TypeError message when `function` cannot ask for `reply`."""
    name = reply.__name__
    if reply in MULTI:
        return f"LFS answers with several {name}: use request_all({name})"
    if reply in SINGLE:
        return f"LFS answers with a single {name}: use request({name})"
    return f"{name} is not something LFS sends on request"


async def answer(waiting: Waiting, timeout: float | None) -> InSimPacket:
    """The next answer, or the connection error, within the time given."""
    async with asyncio.timeout(timeout):
        item = await waiting.answers.get()
    if isinstance(item, ConnectionError):
        raise item
    return item
