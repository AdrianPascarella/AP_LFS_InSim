"""run(): InSim, OutSim and OutGauge together, in one process and one event loop."""

from __future__ import annotations

import asyncio
import contextlib
from types import TracebackType
from typing import Protocol, Self


class Source(Protocol):
    """Anything run() can start: InSim, OutSim or OutGauge."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def wait_closed(self) -> None: ...


def run(*sources: Source) -> None:
    """Start every source and dispatch their packets until Ctrl+C.

    It also returns when any of them is closed (with `await insim.close()` in a handler, say),
    and then closes the others. Example: `run(insim, gauge)`. If one was closed by a failing
    handler with errors="raise", that error is raised.
    """
    if not sources:
        raise TypeError("run() needs at least one InSim, OutSim or OutGauge")
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run(sources))


async def _run(sources: tuple[Source, ...]) -> None:
    async with contextlib.AsyncExitStack() as stack:
        for source in sources:
            await stack.enter_async_context(source)
        waits = [asyncio.create_task(source.wait_closed()) for source in sources]
        try:
            done, _ = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for wait in waits:
                wait.cancel()
        for wait in done:
            if (error := wait.exception()) is not None:
                raise error
