"""Chat commands such as "!hello" (used by InSim.on_command).

With a prefix in IS_ISI, LFS sends what users type starting with it as IS_MSO (MSO_PREFIX, and
hidden from the other users). The command is the word after the prefix, in any case; the words
after it are its arguments.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from lfs_insim.packets import IS_MSO, MSO

CommandHandler = Callable[["Command"], None] | Callable[["Command"], Awaitable[None]]


@dataclass(frozen=True)
class Command:
    """A chat command that someone typed: "!kick Bob" gives name "kick" and args ("Bob",)."""

    name: str
    """The command, in lower case and without the prefix."""
    args: tuple[str, ...]
    """The words after it, as typed."""
    ucid: int
    """The connection that typed it."""
    plid: int
    """Its player, if it typed it while driving (0 if not)."""
    packet: IS_MSO
    """The IS_MSO it came in."""
    _reply: Callable[[str], None] = field(repr=False, compare=False)

    def reply(self, text: str) -> None:
        """Answer only the connection that typed it (insim.say with to=its UCID)."""
        self._reply(text)


class Commands:
    """The command functions of an InSim, by name."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self._by_name: dict[str, CommandHandler] = {}

    def check(self, name: str) -> str:
        """The name as it is kept (lower case); ValueError if it cannot be a new command."""
        if not self.prefix:
            raise ValueError("chat commands need a prefix: InSim(prefix='!')")
        key = name.lower()
        if not key or key.split() != [key] or key.startswith(self.prefix):
            raise ValueError(f"{name!r} is not a command name: one word, without the prefix")
        if key in self._by_name:
            raise ValueError(f"the command {name!r} already has a function")
        return key

    def add(self, name: str, handler: CommandHandler) -> None:
        self._by_name[self.check(name)] = handler

    def find(self, packet: IS_MSO) -> tuple[CommandHandler, str, tuple[str, ...]] | None:
        """The function for this message, its name and its arguments; None if it is not one."""
        if not self._by_name or packet.UserType == MSO.SYSTEM:
            return None
        text = packet.text
        if not text.startswith(self.prefix):
            return None
        words = text[len(self.prefix) :].split()
        if not words or (handler := self._by_name.get(words[0].lower())) is None:
            return None
        return handler, words[0].lower(), tuple(words[1:])
