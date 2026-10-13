"""Chat commands such as "!hello" (used by InSim.on_command and InSim.command_group).

With a prefix in IS_ISI, LFS sends what users type starting with it as IS_MSO (MSO_PREFIX, and
hidden from the other users). The command is the word after the prefix, in any case; the words
after it are its arguments.

The arguments are the parameters of the function after the Command: with
`def speed(command, kmh: int, who: str = "all")`, "!speed 80" calls `speed(command, 80, "all")`.
Words that do not fit are answered with the usage, and the function is not called; "!speed ?" is
answered with the usage and the first line of the docstring. A function that takes only the
Command gets any words, unchecked, in `command.args`.
"""

from __future__ import annotations

import functools
import inspect
import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from lfs_insim._handlers import Handlers
from lfs_insim.packets import IS_MSO, MSO

CommandHandler = Callable[..., None] | Callable[..., Awaitable[None]]
Allow = Callable[["Command"], bool]

_TYPES: dict[Any, str] = {str: "text", int: "a whole number", float: "a number"}


@dataclass(frozen=True)
class Command:
    """A chat command that someone typed: "!kick Bob" gives name "kick" and args ("Bob",)."""

    name: str
    """The command, in lower case and without the prefix ("aic start" in a group)."""
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


class _Misuse(Exception):
    """Words that do not fit the function; the message says why, for the reply."""


@dataclass(frozen=True)
class _Param:
    name: str
    type: Any
    optional: bool
    rest: bool

    def usage(self) -> str:
        if self.rest:
            return f"[{self.name}...]"
        return f"[{self.name}]" if self.optional else f"<{self.name}>"

    def convert(self, word: str) -> Any:
        try:
            return self.type(word)
        except ValueError:
            raise _Misuse(f"{self.name} must be {_TYPES[self.type]}, not {word!r}") from None


def _params(name: str, handler: CommandHandler) -> list[_Param] | None:
    """The arguments of a command function; None if it takes only the Command (any words)."""
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        return None  # a builtin without a signature
    params = list(signature.parameters.values())
    if not params or params[0].kind in (params[0].KEYWORD_ONLY, params[0].VAR_KEYWORD):
        raise TypeError(f"{name}: the function needs a first parameter for the Command")
    if params[0].kind is params[0].VAR_POSITIONAL:
        return None  # like print(*args): it takes the Command and nothing is checked
    try:
        hints = typing.get_type_hints(handler)
    except Exception:
        hints = {}
    result: list[_Param] = []
    for param in params[1:]:
        if param.kind is param.VAR_KEYWORD:
            continue
        if param.kind is param.KEYWORD_ONLY:
            if param.default is param.empty:
                raise TypeError(f"{name}: {param.name} must have a default (it is not a word)")
            continue
        kind = hints.get(param.name, str)
        if kind not in _TYPES:
            shown = getattr(kind, "__name__", repr(kind))
            raise TypeError(
                f"{name}: {param.name} is a {shown}; command arguments are str, int or float"
            )
        optional = param.default is not param.empty
        result.append(_Param(param.name, kind, optional, param.kind is param.VAR_POSITIONAL))
    return result or None


@dataclass(frozen=True)
class _Entry:
    """A command and what is needed to call it."""

    name: str  # "speed", or "aic start" in a group
    handler: CommandHandler
    params: list[_Param] | None
    doc: str
    admin: bool
    allow: tuple[Allow, ...]

    def usage(self, prefix: str) -> str:
        return " ".join([prefix + self.name, *(p.usage() for p in self.params or [])])

    def help(self, prefix: str) -> str:
        return f"{self.usage(prefix)}: {self.doc}" if self.doc else self.usage(prefix)

    def arguments(self, words: tuple[str, ...]) -> list[Any]:
        if self.params is None:
            return []
        values: list[Any] = []
        for i, param in enumerate(self.params):
            if param.rest:
                return values + [param.convert(word) for word in words[i:]]
            if i < len(words):
                values.append(param.convert(words[i]))
            elif not param.optional:
                raise _Misuse(f"{param.name} is missing")
        if len(words) > len(self.params):
            raise _Misuse("too many words")
        return values


@dataclass
class _Group:
    name: str
    admin: bool
    allow: tuple[Allow, ...]
    entries: dict[str, _Entry] = field(default_factory=dict)


class CommandGroup:
    """Commands under one name: `aic = insim.command_group("aic")`, then `@aic.on_command("start")`
    for "!aic start". "!aic" alone lists them."""

    def __init__(self, commands: Commands, group: _Group) -> None:
        self._commands = commands
        self._group = group

    def on_command(
        self, name: str, *, admin: bool = False, allow: Allow | None = None
    ) -> Callable[[CommandHandler], CommandHandler]:
        """Decorator: a command of this group, as InSim.on_command; the group's limits apply too."""
        return self._commands.register(name, admin, allow, self._group)


class Commands:
    """The command functions of an InSim, by name."""

    def __init__(self, prefix: str, make_roster: Callable[[], Any]) -> None:
        self.prefix = prefix
        self._make_roster = make_roster
        self._roster: Any = None  # a Roster, made once a command is only for admins
        self._by_name: dict[str, _Entry] = {}
        self._groups: dict[str, _Group] = {}

    def _check(self, name: str, taken: dict[str, Any] | None = None) -> str:
        """The name as it is kept (lower case); ValueError if it cannot be a new command."""
        if not self.prefix:
            raise ValueError("chat commands need a prefix: InSim(prefix='!')")
        key = name.lower()
        if not key or key.split() != [key] or key.startswith(self.prefix):
            raise ValueError(f"{name!r} is not a command name: one word, without the prefix")
        names = (self._by_name.keys() | self._groups.keys()) if taken is None else taken.keys()
        if key in names:
            raise ValueError(f"the command {name!r} already has a function")
        return key

    def register(
        self, name: str, admin: bool, allow: Allow | None, group: _Group | None = None
    ) -> Callable[[CommandHandler], CommandHandler]:
        """The decorator of on_command; the name is checked now, not when the function comes."""
        key = self._check(name, None if group is None else group.entries)
        full = key if group is None else f"{group.name} {key}"

        def add(handler: CommandHandler) -> CommandHandler:
            doc = (inspect.getdoc(handler) or "").split("\n", 1)[0] if _own_doc(handler) else ""
            limits = () if allow is None else (allow,)
            entry = _Entry(full, handler, _params(full, handler), doc, admin, limits)
            (self._by_name if group is None else group.entries)[key] = entry
            if admin:
                self._need_admins()
            return handler

        return add

    def group(self, name: str, admin: bool, allow: Allow | None) -> CommandGroup:
        key = self._check(name)
        group = _Group(key, admin, () if allow is None else (allow,))
        self._groups[key] = group
        if admin:
            self._need_admins()
        return CommandGroup(self, group)

    def _need_admins(self) -> None:
        if self._roster is None:
            self._roster = self._make_roster()

    def _is_admin(self, ucid: int) -> bool:
        if ucid == 0:
            return True  # the host, or this computer
        connection = None if self._roster is None else self._roster.connections.get(ucid)
        return connection is not None and bool(connection.admin)

    def handle(
        self,
        packet: IS_MSO,
        handlers: Handlers,
        say: Callable[..., None],
    ) -> None:
        """Run the command in this message, if it is one of ours; otherwise do nothing."""
        if not (self._by_name or self._groups) or packet.UserType == MSO.SYSTEM:
            return
        text = packet.text
        if not text.startswith(self.prefix):
            return
        words = text[len(self.prefix) :].split()
        if not words:
            return
        key = words[0].lower()
        group = self._groups.get(key)
        entry: _Entry | None
        if group is None:
            if (entry := self._by_name.get(key)) is None:
                return  # perhaps another program's command
            name, args = key, tuple(words[1:])
            admin, allow = entry.admin, entry.allow
        else:
            entry = group.entries.get(words[1].lower()) if len(words) > 1 else None
            if entry is None:  # the group's name alone, or with a command it does not have
                name, args = key, tuple(words[1:])
                admin, allow = group.admin, group.allow
            else:
                name, args = entry.name, tuple(words[2:])
                admin, allow = group.admin or entry.admin, group.allow + entry.allow
        reply = functools.partial(say, to=packet.UCID)
        command = Command(name, args, packet.UCID, packet.PLID, packet, reply)
        shown = self.prefix + name
        if admin and not self._is_admin(packet.UCID):
            reply(f"{shown} is only for admins")
            return
        if not all(_allowed(check, command, handlers) for check in allow):
            reply(f"You may not use {shown}")
            return
        if entry is None:
            if group is not None:
                listed = args in ((), ("?",))
                first = (
                    f"{shown} commands:"
                    if listed
                    else (f"{shown} has no command {args[0]!r}. Its commands:")
                )
                for line in [first, *(e.help(self.prefix) for e in group.entries.values())]:
                    reply(line)
            return
        if args == ("?",):
            reply(entry.help(self.prefix))
            return
        try:
            values = entry.arguments(args)
        except _Misuse as misuse:
            reply(f"{shown}: {misuse}. Use: {entry.usage(self.prefix)}")
            return
        handlers.call(entry.handler, (command, *values), f"command {shown}")


def _allowed(check: Allow, command: Command, handlers: Handlers) -> bool:
    """An `allow` function's answer; one that fails says no (and is reported like a handler)."""
    try:
        return bool(check(command))
    except Exception as error:
        handlers._failed(check, f"allow of command {command.name}", error)
        return False


def _own_doc(handler: CommandHandler) -> bool:
    """Whether the docstring is the function's own (print's is not about the command)."""
    return inspect.isfunction(handler) or inspect.ismethod(handler)
