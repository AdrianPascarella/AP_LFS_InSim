"""insim.on and insim.send: callable, and with one attribute per packet.

    @insim.on.IS_NPL                 # the editor lists only the packets that LFS sends
    def joined(packet: received.IS_NPL) -> None: ...

    insim.send.IS_MST(Msg="hello")   # the editor lists only the packets a program sends

`insim.on(IS_NPL)` and `insim.send(packet, ...)` do the same. The attributes are generated from
the specification (lfs_insim/_shortcuts.py); the logic is here.

IS_TINY and IS_SMALL carry a subtype (SubT): `@insim.on.IS_TINY(TINY.MPE)` or
`@insim.on.IS_SMALL(SMALL.VTA, SMALL.RTP)` call the function only for those. Only the subtypes
that LFS sends are accepted (lfs_insim/_subtypes.py, generated from the specification).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import IntEnum
from typing import Any, Generic, ParamSpec, TypeVar, overload

from lfs_insim._subtypes import SUBTYPES, ReceivedSMALL, ReceivedTINY
from lfs_insim.packets import IS_SMALL, IS_TINY
from lfs_insim.packets._directions import InfoPacket, InstructionPacket, direction_error

P = TypeVar("P", bound=InfoPacket)
Handler = Callable[[P], None] | Callable[[P], Awaitable[None]]
Fields = ParamSpec("Fields")
S = TypeVar("S", bound=IntEnum)


class Receive:
    """Register handlers: `@insim.on.IS_NPL`, or `@insim.on(IS_NPL)`."""

    def __init__(self, add: Callable[..., None]) -> None:
        self._add = add

    @overload
    def __call__(
        self, packet_type: type[IS_TINY], subtype: ReceivedTINY, /, *more: ReceivedTINY
    ) -> Callable[[Handler[IS_TINY]], Handler[IS_TINY]]: ...
    @overload
    def __call__(
        self, packet_type: type[IS_SMALL], subtype: ReceivedSMALL, /, *more: ReceivedSMALL
    ) -> Callable[[Handler[IS_SMALL]], Handler[IS_SMALL]]: ...
    @overload
    def __call__(self, packet_type: type[P]) -> Callable[[Handler[P]], Handler[P]]: ...
    def __call__(
        self, packet_type: type[Any], *subtypes: IntEnum
    ) -> Callable[[Handler[Any]], Handler[Any]]:
        """Decorator: call the function with every packet of this type that LFS sends.

        For IS_TINY and IS_SMALL, naming subtypes (`on(IS_TINY, TINY.MPE)`) limits it to those;
        only the subtypes that LFS sends are accepted.

        The function may be `def` (it runs at once, so it should be quick) or `async def` (it
        runs as a task and may await). An exception in it is logged and does not stop the others.
        Only packets that LFS sends ("info" or "both ways" in InSim.txt): others raise TypeError.
        """
        return self._register(packet_type, subtypes)

    def _register(
        self, packet_type: type[Any], subtypes: tuple[Any, ...]
    ) -> Callable[[Handler[Any]], Handler[Any]]:
        if not (isinstance(packet_type, type) and issubclass(packet_type, InfoPacket)):
            raise TypeError(direction_error(packet_type, InfoPacket))
        if subtypes:
            if packet_type not in SUBTYPES:
                raise TypeError(f"{packet_type.__name__} has no subtypes")
            enum, sent_by_lfs = SUBTYPES[packet_type]
            if not all(isinstance(subtype, enum) for subtype in subtypes):
                raise TypeError(
                    f"{packet_type.__name__} subtypes are {enum.__name__} members "
                    f"({enum.__name__}.{next(iter(enum)).name}...), not {subtypes!r}"
                )
            never = sorted({s for s in subtypes if s not in sent_by_lfs})
            if never:
                raise TypeError(
                    f"LFS never sends {packet_type.__name__} with "
                    f"{', '.join(f'{enum.__name__}.{s.name}' for s in never)}: the function would "
                    f"never run. Those are for your program to send "
                    f"(insim.send.{packet_type.__name__}(SubT=...)). LFS sends "
                    f"{', '.join(f'{enum.__name__}.{s.name}' for s in sorted(sent_by_lfs))}"
                )
        only = frozenset(subtypes) or None

        def register(handler: Handler[Any]) -> Handler[Any]:
            self._add(packet_type, handler, only)
            return handler

        return register


class Transmit:
    """Send packets: `insim.send.IS_MST(Msg="hello")`, or `insim.send(IS_MST(Msg="hello"))`."""

    def __init__(self, write: Callable[[tuple[InstructionPacket, ...]], None]) -> None:
        self._write = write

    def __call__(self, *packets: InstructionPacket) -> None:
        """Send packets to LFS. Raises ConnectionError if there is no connection.

        Only packets that a program sends ("instruction" or "both ways" in InSim.txt): others
        raise TypeError, before the connection is looked at.
        """
        for packet in packets:
            if not isinstance(packet, InstructionPacket):
                raise TypeError(direction_error(type(packet), InstructionPacket))
        self._write(packets)


class Receiver(Generic[P]):
    """`insim.on.IS_XXX`: the decorator of `insim.on(IS_XXX)`, typed for that packet."""

    def __init__(self, packet_type: type[P]) -> None:
        self.packet_type = packet_type

    @overload
    def __get__(self, obj: None, owner: type[Any]) -> Receiver[P]: ...
    @overload
    def __get__(self, obj: Receive, owner: type[Any]) -> Callable[[Handler[P]], Handler[P]]: ...
    def __get__(self, obj: Receive | None, owner: type[Any]) -> Any:
        return self if obj is None else obj(self.packet_type)


class Subtyped(Generic[P, S]):
    """`insim.on.IS_TINY`: a decorator, and `insim.on.IS_TINY(TINY.MPE)` for one subtype."""

    def __init__(self, receive: Receive, packet_type: type[P]) -> None:
        self._receive = receive
        self._packet_type = packet_type

    @overload
    def __call__(self, handler: Handler[P], /) -> Handler[P]: ...
    @overload
    def __call__(self, subtype: S, /, *more: S) -> Callable[[Handler[P]], Handler[P]]: ...
    def __call__(self, first: Any, /, *more: IntEnum) -> Any:
        if isinstance(first, int):
            return self._receive._register(self._packet_type, (first, *more))
        return self._receive._register(self._packet_type, ())(first)


class SubReceiver(Generic[P, S]):
    """`insim.on.IS_XXX` of a packet with subtypes: the decorator, with an optional filter."""

    def __init__(self, packet_type: type[P]) -> None:
        self.packet_type = packet_type

    @overload
    def __get__(self, obj: None, owner: type[Any]) -> SubReceiver[P, S]: ...
    @overload
    def __get__(self, obj: Receive, owner: type[Any]) -> Subtyped[P, S]: ...
    def __get__(self, obj: Receive | None, owner: type[Any]) -> Any:
        return self if obj is None else Subtyped(obj, self.packet_type)


class Sender(Generic[Fields]):
    """`insim.send.IS_XXX(...)`: build the packet with these fields and send it."""

    def __init__(self, packet_type: Callable[Fields, InstructionPacket]) -> None:
        self.packet_type = packet_type

    @overload
    def __get__(self, obj: None, owner: type[Any]) -> Sender[Fields]: ...
    @overload
    def __get__(self, obj: Transmit, owner: type[Any]) -> Callable[Fields, None]: ...
    def __get__(self, obj: Transmit | None, owner: type[Any]) -> Any:
        if obj is None:
            return self
        build = self.packet_type

        def send(*args: Fields.args, **kwargs: Fields.kwargs) -> None:
            obj(build(*args, **kwargs))

        send.__name__ = send.__qualname__ = getattr(build, "__name__", "send")
        send.__doc__ = build.__doc__
        return send
