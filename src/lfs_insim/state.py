"""Who is who in LFS: the connections and the players, kept up to date. Optional (D4).

    from lfs_insim.state import Roster

    roster = Roster(insim)          # before insim.run()

    @insim.on(IS_NPL)
    def joined(packet: IS_NPL) -> None:
        player = roster.players[packet.PLID]
        print(player.name, "driven by", player.connection.username)

The roster asks LFS for every connection and player on each (re)connection, and follows the
packets that change them. It is up to date in every handler: when someone arrives or changes it
is updated before the handlers run, and when someone leaves (IS_PLL, IS_CNL), after them, so a
handler can still look up who is leaving (an `async def` one, until its first await).

It also knows whether LFS is a guest in someone else's server (`roster.guest`) and which
connection is this computer (`roster.local`).

The on_connect functions of every plugin start at once, so one may look before LFS has answered:
`await roster.ready()` waits until the whole picture of this connection has arrived.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from lfs_insim._connection import InSim
from lfs_insim._plugins import Plugin
from lfs_insim.packets import (
    IS_CNL,
    IS_CPR,
    IS_ISM,
    IS_NCN,
    IS_NPL,
    IS_PLL,
    IS_PLP,
    IS_TINY,
    IS_TOC,
    TINY,
)
from lfs_insim.packets._structure import InSimPacket

__all__ = ["Connection", "Player", "Roster"]

_REMOTE = 4  # IS_NCN.Flags bit 2
_AI = 2  # IS_NPL.PType bit 1


@dataclass(eq=False)
class Connection:
    """A connection to LFS: a person at a computer. UCID 0 is the host (or this computer)."""

    ucid: int
    username: str = ""
    """LFS username ("" for the host of a local game)."""
    name: str = ""
    """Nickname, with LFS's colour codes (`lfs_insim.text.strip_colours` removes them)."""
    admin: bool = False
    remote: bool = False
    players: list[Player] = field(default_factory=list)
    """The cars it has in the race: its own, and the AI it added."""


@dataclass(eq=False)
class Player:
    """A car in the race, driven by a person or by the AI."""

    plid: int
    connection: Connection
    """Whose car it is: the driver's connection, or the one that added the AI."""
    name: str = ""
    plate: str = ""
    car: str = ""
    """An official car ("XFG") or a mod's SkinID ("5A1FB3")."""
    is_ai: bool = False
    in_pits: bool = False
    """In the garage (IS_PLP): still in the race, not on track, until it leaves the pits."""


class Roster(Plugin):
    """The connections and players of LFS, by UCID and PLID: `roster = insim.use(Roster)`,
    before running insim. One per InSim, shared with the commands and every other plugin.
    """

    def __init__(self, insim: InSim) -> None:
        super().__init__(insim)
        self._insim = insim
        self._connections: dict[int, Connection] = {}
        self._players: dict[int, Player] = {}
        self._guest = False
        self._local: int | None = None  # the UCID of this computer, from its IS_NCN
        self._ready = asyncio.Event()  # set when everyone has been asked for, on this connection
        self._asking = 0  # refreshes started: only the latest may say the picture is ready
        insim.on_connect(self._refresh)
        insim.on_disconnect(self._ready.clear)
        insim.on(IS_ISM)(self._restarted)  # a new host or game: ask again
        insim.on(IS_TINY, TINY.MPE)(self._restarted)
        insim.watch(before=self._before, after=self._after)

    @property
    def connections(self) -> Mapping[int, Connection]:
        """Every connection, by UCID (read only)."""
        return MappingProxyType(self._connections)

    @property
    def players(self) -> Mapping[int, Player]:
        """Every player in the race, by PLID (read only)."""
        return MappingProxyType(self._players)

    @property
    def guest(self) -> bool:
        """True while LFS is a guest in someone else's server (IS_ISM with Host 0).

        False in single player and as host. Only the host may answer one connection (IS_MTC),
        and as a guest the host is UCID 0 and this computer another UCID: see `local`.
        """
        return self._guest

    @property
    def local(self) -> Connection | None:
        """This computer's connection: the one LFS does not mark as remote (None until known).

        UCID 0 in single player and as host; another UCID as a guest.
        """
        return None if self._local is None else self._connections.get(self._local)

    async def ready(self) -> None:
        """Wait until the roster has the whole picture of this connection: every connection and
        player, and whether LFS is a guest. At once if it has it; again after LFS changes host or
        game (IS_ISM, TINY_MPE) and after a reconnection, until LFS has answered.

        In single player LFS does not answer the guest question, so the first picture takes about
        a second.
        """
        await self._ready.wait()

    async def _refresh(self) -> None:
        """Forget everything and ask LFS again; the answers go through _before like any packet."""
        self._ready.clear()
        self._asking += 1
        asking = self._asking
        self._connections.clear()
        self._players.clear()
        self._local = None
        answered = await asyncio.gather(self._ask_multiplayer(), self._ask_everyone())
        if all(answered) and asking == self._asking:
            self._ready.set()

    async def _ask_everyone(self) -> bool:
        try:
            await self._insim.request_all(IS_NCN)
            await self._insim.request_all(IS_NPL)
        except ConnectionError:
            return False  # lost or closed: the next connection asks
        return True

    async def _ask_multiplayer(self) -> bool:
        try:
            await self._insim.request(IS_ISM, timeout=1.0)  # handled by _before
        except TimeoutError:
            self._guest = False  # not in multiplayer: LFS does not answer
        except ConnectionError:
            return False  # the next connection asks again
        return True

    async def _restarted(self, packet: IS_ISM | IS_TINY) -> None:
        if isinstance(packet, IS_ISM) and packet.ReqI:
            return  # the answer to TINY_ISM, asked for by _refresh: nothing has changed
        await self._refresh()

    def _before(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_NCN):
            connection = self._connection(packet.UCID)
            connection.username = packet.UName
            connection.name = packet.PName
            connection.admin = bool(packet.Admin)
            connection.remote = bool(packet.Flags & _REMOTE)
            if not connection.remote:
                self._local = packet.UCID
        elif isinstance(packet, IS_ISM):
            self._guest = not packet.Host
            if not packet.ReqI:
                self._ready.clear()  # now, not when _restarted runs: ready() must not say yes
        elif isinstance(packet, IS_TINY) and packet.SubT == TINY.MPE:
            self._guest = False
            self._ready.clear()
        elif isinstance(packet, IS_NPL):
            self._joined(packet)
        elif isinstance(packet, IS_PLP):
            if (player := self._players.get(packet.PLID)) is not None:
                player.in_pits = True
        elif isinstance(packet, IS_CPR):
            if (renamed := self._connections.get(packet.UCID)) is not None:
                renamed.name = packet.PName
                for player in renamed.players:
                    if not player.is_ai:
                        player.name, player.plate = packet.PName, packet.Plate
        elif isinstance(packet, IS_TOC):
            if (player := self._players.get(packet.PLID)) is not None:
                self._move(player, self._connection(packet.NewUCID))
        elif isinstance(packet, IS_TINY) and packet.SubT == TINY.CLR:
            self._players.clear()
            for connection in self._connections.values():
                connection.players.clear()

    def _after(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_PLL):
            if (player := self._players.pop(packet.PLID, None)) is not None:
                player.connection.players.remove(player)
        elif isinstance(packet, IS_CNL):
            connection = self._connections.pop(packet.UCID, None)
            if self._local == packet.UCID:
                self._local = None
            for player in connection.players if connection is not None else []:
                self._players.pop(player.plid, None)

    def _joined(self, packet: IS_NPL) -> None:
        if packet.NumP == 0:
            return  # a join request (ISF.REQ_JOIN), not a player yet
        connection = self._connection(packet.UCID)
        player = self._players.get(packet.PLID)
        if player is None:
            player = self._players[packet.PLID] = Player(packet.PLID, connection)
            connection.players.append(player)
        else:
            self._move(player, connection)  # leaving the pits
        player.name, player.plate, player.car = packet.PName, packet.Plate, packet.CName
        player.is_ai = bool(packet.PType & _AI)
        player.in_pits = False

    def _connection(self, ucid: int) -> Connection:
        """The connection with this UCID; an empty one until its IS_NCN comes, if it is new."""
        connection = self._connections.get(ucid)
        if connection is None:
            connection = self._connections[ucid] = Connection(ucid)
        return connection

    def _move(self, player: Player, connection: Connection) -> None:
        if player.connection is not connection:
            player.connection.players.remove(player)
            player.connection = connection
            connection.players.append(player)
