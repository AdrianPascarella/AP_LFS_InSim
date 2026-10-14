"""insim.request, insim.request_all and insim.instruct: callable, and with one attribute per packet.

    state = await insim.request.IS_STA()               # the editor lists what LFS sends on request
    players = await insim.request_all.IS_NPL()         # ...what it sends in several packets
    reply = await insim.instruct.IS_RIP(RName="race")  # ...the instructions it answers

`insim.request(IS_STA)`, `insim.request_all(IS_NPL)` and `insim.instruct(IS_RIP(...))` do the
same. The attributes are the tables: which TINY asks for each packet, and how many come. Written
by hand, because InSim.txt says it in comments.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Coroutine
from typing import Any, Generic, Protocol, TypeVar, cast, overload

from lfs_insim import packets
from lfs_insim._requests import Requests, answer
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
    IS_SSH,
    IS_STA,
    IS_TINY,
    IS_VER,
    TINY,
)
from lfs_insim.packets._structure import InSimPacket

R = TypeVar("R", bound=InSimPacket)
R_co = TypeVar("R_co", bound=InSimPacket, covariant=True)
Answered = TypeVar("Answered", IS_RIP, IS_SSH)


class AskOne(Protocol[R_co]):
    def __call__(self, *, timeout: float | None = 2.0) -> Coroutine[Any, Any, R_co]: ...


class AskAll(Protocol[R]):
    def __call__(self, *, quiet: float = 0.5) -> Coroutine[Any, Any, list[R]]: ...


class Asking:
    """What the three share: the waiting requests and the way to send."""

    def __init__(self, requests: Requests, send: Callable[[IS_TINY | IS_RIP | IS_SSH], None]):
        self._requests = requests
        self._send = send


class One(Generic[R]):
    """`insim.request.IS_XXX`: a packet that LFS sends once when this TINY asks for it."""

    def __init__(self, reply: type[R], subtype: TINY) -> None:
        self.reply = reply
        self.subtype = subtype

    @overload
    def __get__(self, obj: None, owner: type[Any]) -> One[R]: ...
    @overload
    def __get__(self, obj: Request, owner: type[Any]) -> AskOne[R]: ...
    def __get__(self, obj: Request | None, owner: type[Any]) -> Any:
        if obj is None:
            return self
        reply = self.reply

        def ask(*, timeout: float | None = 2.0) -> Coroutine[Any, Any, R]:
            return obj(reply, timeout=timeout)

        ask.__name__ = ask.__qualname__ = reply.__name__
        ask.__doc__ = reply.__doc__
        return ask


class All(Generic[R]):
    """`insim.request_all.IS_XXX`: packets that LFS sends in several when this TINY asks for them,
    and the field that says how many (None: complete when no more arrive for a while)."""

    def __init__(self, reply: type[R], subtype: TINY, counter: str | None) -> None:
        self.reply = reply
        self.subtype = subtype
        self.counter = counter

    @overload
    def __get__(self, obj: None, owner: type[Any]) -> All[R]: ...
    @overload
    def __get__(self, obj: RequestAll, owner: type[Any]) -> AskAll[R]: ...
    def __get__(self, obj: RequestAll | None, owner: type[Any]) -> Any:
        if obj is None:
            return self
        reply = self.reply

        def ask(*, quiet: float = 0.5) -> Coroutine[Any, Any, list[R]]:
            return obj(reply, quiet=quiet)

        ask.__name__ = ask.__qualname__ = reply.__name__
        ask.__doc__ = reply.__doc__
        return ask


class Request(Asking):
    """Ask LFS for a packet and wait for it: `state = await insim.request.IS_STA()`.

    Sends the IS_TINY that asks for it (TINY_SST for IS_STA, TINY_VER for IS_VER...); the answer
    also reaches the `@insim.on` handlers. Raises TimeoutError if LFS does not answer within
    `timeout` seconds, and ConnectionError if there is no connection or it is lost while
    waiting. The same request made while one waits is not sent again: both get its answer (or
    its error), within the first one's timeout. `insim.request(IS_STA)` does the same.
    """

    IS_VER = One(IS_VER, TINY.VER)
    """VERsion"""
    IS_STA = One(IS_STA, TINY.SST)
    """STAte"""
    IS_CPP = One(IS_CPP, TINY.SCP)
    """Cam Pos Pack: where the camera is"""
    IS_ISM = One(IS_ISM, TINY.ISM)
    """InSim Multi: the host joined (nothing if not in multiplayer)"""
    IS_NLP = One(IS_NLP, TINY.NLP)
    """Node and Lap Packet"""
    IS_REO = One(IS_REO, TINY.REO)
    """REOrder: the starting order"""
    IS_RST = One(IS_RST, TINY.RST)
    """Race STart: the race settings"""
    IS_AXI = One(IS_AXI, TINY.AXI)
    """AutoX Info: the layout loaded"""
    IS_RIP = One(IS_RIP, TINY.RIP)
    """Replay Information Packet: the replay loaded (to load one, `insim.instruct.IS_RIP`)"""
    IS_MAL = One(IS_MAL, TINY.MAL)
    """Mods ALlowed"""
    IS_PLH = One(IS_PLH, TINY.PLH)
    """PLayer Handicaps"""
    IS_IPB = One(IS_IPB, TINY.IPB)
    """IP Bans"""

    async def __call__(self, reply: type[R], *, timeout: float | None = 2.0) -> R:
        """Ask LFS for a packet of this type and wait for it (see the class)."""
        entry = _entry(Request, reply, One)
        if entry is None:
            raise TypeError(_wrong_function(reply, "request"))
        sub = entry.subtype

        async def ask() -> InSimPacket:
            with self._requests.waiting(reply) as (req_i, waiting):
                self._send(IS_TINY(ReqI=req_i, SubT=sub))
                return await answer(waiting, timeout)

        return cast(R, await self._requests.shared((reply, "request"), ask))


class RequestAll(Asking):
    """Ask LFS for packets that come in several: `players = await insim.request_all.IS_NPL()`.

    Returns when as many have arrived as the packets themselves say (Total in IS_NCN, NumP in
    IS_NPL, NumRes in IS_RES), or when none has arrived for `quiet` seconds: an empty list if
    LFS has nothing to send (no results before anyone finishes, say). The answers also reach the
    handlers. Raises ConnectionError as request does, and shares a request made at the same time
    as request does (each gets its own list). `insim.request_all(IS_NPL)` does the same.
    """

    IS_NCN = All(IS_NCN, TINY.NCN, "Total")
    """New ConN: one per connection, host included"""
    IS_NPL = All(IS_NPL, TINY.NPL, "NumP")
    """New PLayer joining race: one per player"""
    IS_RES = All(IS_RES, TINY.RES, "NumRes")
    """RESult: one per result; none before anyone finishes"""
    IS_NCI = All(IS_NCI, TINY.NCI, None)
    """New Conn Info: one per guest (hosts only)"""
    IS_SLC = All(IS_SLC, TINY.SLC, None)
    """SeLected Car: one per connection (hosts only)"""
    IS_MCI = All(IS_MCI, TINY.MCI, None)
    """Multi Car Info: a set, up to 16 cars each"""
    IS_AXM = All(IS_AXM, TINY.AXM, None)
    """AutoX Multiple objects: the layout, in as many as it needs"""

    async def __call__(self, reply: type[R], *, quiet: float = 0.5) -> list[R]:
        """Ask LFS for the packets of this type and wait for them (see the class)."""
        entry = _entry(RequestAll, reply, All)
        if entry is None:
            raise TypeError(_wrong_function(reply, "request_all"))
        sub, counter = entry.subtype, entry.counter

        async def ask() -> list[InSimPacket]:
            answers: list[InSimPacket] = []
            with self._requests.waiting(reply) as (req_i, waiting):
                self._send(IS_TINY(ReqI=req_i, SubT=sub))
                while True:
                    try:
                        packet = await answer(waiting, quiet)
                    except TimeoutError:
                        return answers
                    answers.append(packet)
                    if counter is not None and len(answers) >= getattr(packet, counter):
                        return answers

        return cast(list[R], list(await self._requests.shared((reply, "request_all"), ask)))


class Instruct(Asking):
    """Send an instruction that LFS answers when it has done it, and wait for the reply:
    `reply = await insim.instruct.IS_RIP(RName="race", timeout=30)`.

    Sent with a ReqI of its own; LFS replies with the same packet type and that ReqI. Check the
    reply's Error. Raises TimeoutError and ConnectionError as request does; each is sent, even
    the same one twice. `insim.instruct(IS_RIP(...))` does the same with a packet already built,
    and does not change it.
    """

    async def IS_RIP(
        self,
        *,
        MPR: int = 0,
        Paused: int = 0,
        Options: int = 0,
        CTime: int = 0,
        RName: str = "",
        timeout: float | None = 2.0,
    ) -> packets.IS_RIP:
        """Replay Information Packet: load a replay (RName), or move through the loaded one
        (RName empty) to CTime ms. MPR is 0 for a single player replay, 1 for multiplayer;
        Options are RIPOPT flags. Loading takes a while: give it a longer timeout."""
        packet = IS_RIP(MPR=MPR, Paused=Paused, Options=Options, CTime=CTime, RName=RName)
        return await self(packet, timeout=timeout)

    async def IS_SSH(self, *, Name: str = "", timeout: float | None = 2.0) -> packets.IS_SSH:
        """ScreenSHot: save one, in LFS's screenshot folder, with this name (no extension)."""
        return await self(IS_SSH(Name=Name), timeout=timeout)

    async def __call__(self, packet: Answered, *, timeout: float | None = 2.0) -> Answered:
        """Send a copy of this instruction and wait for LFS's reply (see the class)."""
        if not isinstance(packet, INSTRUCTIONS):
            raise TypeError(_not_answered(packet))
        with self._requests.waiting(type(packet)) as (req_i, waiting):
            sent = copy.copy(packet)
            sent.ReqI = req_i
            self._send(sent)
            return cast(Answered, await answer(waiting, timeout))


INSTRUCTIONS = (IS_RIP, IS_SSH)
"""The instructions that LFS answers with the same packet type and ReqI: Instruct's attributes."""


def _entry(namespace: type[Asking], reply: object, kind: type[Any]) -> Any:
    """The attribute of `namespace` for this packet type, or None if it has none."""
    entry = namespace.__dict__.get(getattr(reply, "__name__", ""))
    return entry if isinstance(entry, kind) and entry.reply is reply else None


def _wrong_function(reply: object, function: str) -> str:
    """The TypeError message when `function` cannot ask for `reply`."""
    if isinstance(reply, INSTRUCTIONS):
        name = type(reply).__name__
        return f"to send {name} and wait for LFS's reply, use instruct.{name}(...)"
    name = getattr(reply, "__name__", repr(reply))
    if _entry(RequestAll, reply, All) is not None:
        return f"LFS answers with several {name}: use request_all.{name}()"
    if _entry(Request, reply, One) is not None:
        return f"LFS answers with a single {name}: use request.{name}()"
    return f"{name} is not something LFS sends on request"


def _not_answered(packet: object) -> str:
    """The TypeError message when instruct() is given a packet that LFS does not answer."""
    name = getattr(type(packet), "__name__", repr(packet))
    answered = ", ".join(cls.__name__ for cls in INSTRUCTIONS)
    return f"LFS does not answer {name} with a reply: instruct takes {answered}"
