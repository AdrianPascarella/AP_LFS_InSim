"""Chat lines typed on this computer during a replay, for the Commands plugin.

Seen with LFS 0.8C: while a replay is loaded (playing or paused), a line typed here comes only as
IS_MSO with MSO.SYSTEM, UCID 0, TextStart 0 and the bare text ("!who"), not as MSO.PREFIX or
MSO.USER. LFS's own notices come the same way, so Commands takes one only if it starts with one of
its commands. Once, LFS also sent the line later in the usual form: that copy is not run again.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from lfs_insim.packets import IS_MSO, MSO

COPY_WINDOW = 60.0
"""Seconds during which the usual form of a line run from the SYSTEM form is taken as its copy."""


def typed_in_replay(packet: IS_MSO, guest: bool) -> bool:
    """Whether a SYSTEM message has the form of a line typed here during a replay; never as a
    guest, where the server's notices come too."""
    return (
        packet.UserType == MSO.SYSTEM and packet.UCID == 0 and packet.TextStart == 0 and not guest
    )


class ReplayLines:
    """The lines run lately from the SYSTEM form, to drop their copy in the usual form once."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self._lines: list[tuple[float, str]] = []  # when, the line

    def ran(self, line: str) -> None:
        self._lines.append((self.clock(), line))

    def is_copy(self, packet: IS_MSO, line: str) -> bool:
        """Whether `line`, typed in the usual form, is the copy of one run from the SYSTEM form
        within COPY_WINDOW; each run has one copy at most (forgotten when found)."""
        now = self.clock()
        self._lines = [(at, each) for at, each in self._lines if now - at <= COPY_WINDOW]
        if packet.UCID != 0:
            return False
        for each in self._lines:
            if each[1] == line:
                self._lines.remove(each)
                return True
        return False
