"""Chat commands such as "!hello" (used by InSim.on_command and InSim.command_group).

With a prefix in IS_ISI, LFS sends what users type starting with it as IS_MSO (MSO_PREFIX, and
hidden from the other users). The command is the word after the prefix, in any case; the words
after it are its arguments.

As a guest in someone else's server, LFS sends what anyone types, prefix or not, and everyone sees
it; "/o !who" reaches only this computer's InSim. Then only this computer may use the commands,
unless InSim(guest_commands="everyone"); admin commands are only for this computer; and replies go
to this computer as IS_MSL, and to anyone else in the public chat (a guest cannot send IS_MTC).

A command or a group may have a prefix of its own (`on_command("who", prefix=".")`); LFS hides
only the messages with the prefix of IS_ISI, so as host the others are seen by everyone.

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
from typing import Any, Literal, get_args

from lfs_insim._handlers import Handlers
from lfs_insim.packets import IS_MSO, MSO

CommandHandler = Callable[..., None] | Callable[..., Awaitable[None]]
Allow = Callable[["Command"], bool]
GuestCommands = Literal["local", "everyone"]

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
    local: bool
    """Typed on this computer (UCID 0, or this computer's UCID when LFS is a guest)."""
    packet: IS_MSO
    """The IS_MSO it came in."""
    _reply: Callable[[str], None] = field(repr=False, compare=False)

    def reply(self, text: str) -> None:
        """Answer only the connection that typed it (insim.say with to=its UCID).

        As a guest, only this computer can be answered alone (IS_MSL); anyone else is answered
        in the public chat, the only way a guest has.
        """
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
    prefix: str
    handler: CommandHandler
    params: list[_Param] | None
    doc: str
    admin: bool
    allow: tuple[Allow, ...]

    def usage(self) -> str:
        return " ".join([self.prefix + self.name, *(p.usage() for p in self.params or [])])

    def help(self) -> str:
        return f"{self.usage()}: {self.doc}" if self.doc else self.usage()

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
    prefix: str
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
        """Decorator: a command of this group, as InSim.on_command; the group's prefix and limits
        apply too."""
        return self._commands.register(name, admin, allow, self._group)


class Commands:
    """The command functions of an InSim, by name."""

    def __init__(
        self, prefix: str, make_roster: Callable[[], Any], guest_commands: GuestCommands
    ) -> None:
        if guest_commands not in get_args(GuestCommands):
            raise ValueError(f'guest_commands is "local" or "everyone", not {guest_commands!r}')
        self.prefix = prefix
        self.guest_commands = guest_commands
        self._make_roster = make_roster
        self._roster: Any = None  # a Roster, made with the first command: who is who
        # by prefix, then by name: "!who" and ".who" are two commands
        self._by_name: dict[str, dict[str, _Entry]] = {}
        self._groups: dict[str, dict[str, _Group]] = {}

    def _prefix(self, prefix: str | None) -> str:
        """The prefix to use (the InSim's if None); ValueError if there is none or it is bad."""
        if prefix is None:
            if not self.prefix:
                raise ValueError(
                    "chat commands need a prefix: InSim(prefix='!') or on_command(..., prefix='!')"
                )
            return self.prefix
        if len(prefix) != 1 or prefix.isspace() or prefix.isalnum():
            raise ValueError(f"a prefix is one character, not a letter or digit: not {prefix!r}")
        return prefix

    def _check(self, name: str, prefix: str, taken: dict[str, Any] | None = None) -> str:
        """The name as it is kept (lower case); ValueError if it cannot be a new command."""
        key = name.lower()
        if not key or key.split() != [key] or key.startswith(prefix):
            raise ValueError(f"{name!r} is not a command name: one word, without the prefix")
        names: set[str]
        if taken is None:
            names = self._by_name.get(prefix, {}).keys() | self._groups.get(prefix, {}).keys()
        else:
            names = set(taken)
        if key in names:
            raise ValueError(f"the command {prefix}{key} already has a function")
        return key

    def register(
        self,
        name: str,
        admin: bool,
        allow: Allow | None,
        group: _Group | None = None,
        prefix: str | None = None,
    ) -> Callable[[CommandHandler], CommandHandler]:
        """The decorator of on_command; the name is checked now, not when the function comes."""
        prefix = group.prefix if group is not None else self._prefix(prefix)
        key = self._check(name, prefix, None if group is None else group.entries)
        full = key if group is None else f"{group.name} {key}"

        def add(handler: CommandHandler) -> CommandHandler:
            doc = (inspect.getdoc(handler) or "").split("\n", 1)[0] if _own_doc(handler) else ""
            limits = () if allow is None else (allow,)
            entry = _Entry(full, prefix, handler, _params(full, handler), doc, admin, limits)
            entries = self._by_name.setdefault(prefix, {}) if group is None else group.entries
            entries[key] = entry
            self._need_roster()
            return handler

        return add

    def group(
        self, name: str, admin: bool, allow: Allow | None, prefix: str | None = None
    ) -> CommandGroup:
        prefix = self._prefix(prefix)
        key = self._check(name, prefix)
        group = _Group(key, prefix, admin, () if allow is None else (allow,))
        self._groups.setdefault(prefix, {})[key] = group
        self._need_roster()
        return CommandGroup(self, group)

    def _need_roster(self) -> None:
        if self._roster is None:
            self._roster = self._make_roster()

    def _is_local(self, ucid: int) -> bool:
        local = self._roster.local
        if local is None:  # not known yet: UCID 0 is this computer unless LFS is a guest
            return ucid == 0 and not self._roster.guest
        return bool(ucid == local.ucid)

    def _is_admin(self, ucid: int, local: bool) -> bool:
        if self._roster.guest:
            return local  # the server's admins are not ours
        if ucid == 0:
            return True  # the host, or this computer
        connection = self._roster.connections.get(ucid)
        return connection is not None and bool(connection.admin)

    def handle(
        self,
        packet: IS_MSO,
        handlers: Handlers,
        say: Callable[..., None],
    ) -> None:
        """Run the command in this message, if it is one of ours; otherwise do nothing."""
        if packet.UserType == MSO.SYSTEM:
            return
        text = packet.text
        prefix = text[:1]
        by_name, groups = self._by_name.get(prefix, {}), self._groups.get(prefix, {})
        if not (by_name or groups):
            return
        words = text[1:].split()
        if not words:
            return
        guest = bool(self._roster.guest)
        local = self._is_local(packet.UCID)
        if guest and not local and self.guest_commands == "local":
            return  # someone else's server: not for them, and they get no answer
        key = words[0].lower()
        group = groups.get(key)
        entry: _Entry | None
        if group is None:
            if (entry := by_name.get(key)) is None:
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
        reply: Callable[[str], None]
        if not guest:
            reply = functools.partial(say, to=packet.UCID)
        else:  # a guest cannot send IS_MTC: this computer gets IS_MSL, anyone else the chat
            reply = functools.partial(say, to=0) if local else say
        command = Command(name, args, packet.UCID, packet.PLID, local, packet, reply)
        shown = prefix + name
        if admin and not self._is_admin(packet.UCID, local):
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
                for line in [first, *(e.help() for e in group.entries.values())]:
                    reply(line)
            return
        if args == ("?",):
            reply(entry.help())
            return
        try:
            values = entry.arguments(args)
        except _Misuse as misuse:
            reply(f"{shown}: {misuse}. Use: {entry.usage()}")
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
