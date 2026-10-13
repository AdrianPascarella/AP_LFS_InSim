"""insim.on and insim.send: callable, and with one attribute per packet.

    @insim.on.IS_NPL                 # the editor lists only the packets that LFS sends
    def joined(packet: received.IS_NPL) -> None: ...

    insim.send.IS_MST(Msg="hello")   # the editor lists only the packets a program sends

`insim.on(IS_NPL)` and `insim.send(packet, ...)` do the same. The attributes are generated from
the specification (lfs_insim/_shortcuts.py); the logic is here.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Generic, ParamSpec, TypeVar, overload

from lfs_insim.packets._directions import InfoPacket, InstructionPacket, direction_error

P = TypeVar("P", bound=InfoPacket)
Handler = Callable[[P], None] | Callable[[P], Awaitable[None]]
Fields = ParamSpec("Fields")


class Receive:
    """Register handlers: `@insim.on.IS_NPL`, or `@insim.on(IS_NPL)`."""

    def __init__(self, add: Callable[[type[InfoPacket], Callable[..., Any]], None]) -> None:
        self._add = add

    def __call__(self, packet_type: type[P]) -> Callable[[Handler[P]], Handler[P]]:
        """Decorator: call the function with every packet of this type that LFS sends.

        The function may be `def` (it runs at once, so it should be quick) or `async def` (it
        runs as a task and may await). An exception in it is logged and does not stop the others.
        Only packets that LFS sends ("info" or "both ways" in InSim.txt): others raise TypeError.
        """
        if not (isinstance(packet_type, type) and issubclass(packet_type, InfoPacket)):
            raise TypeError(direction_error(packet_type, InfoPacket))

        def register(handler: Handler[P]) -> Handler[P]:
            self._add(packet_type, handler)
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
