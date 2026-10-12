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
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from lfs_insim._connection import InSim
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
from lfs_insim.packets._codec import InSimPacket

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


class Roster:
    """The connections and players of LFS, by UCID and PLID. Create it before running insim."""

    def __init__(self, insim: InSim) -> None:
        self._insim = insim
        self._connections: dict[int, Connection] = {}
        self._players: dict[int, Player] = {}
        insim.on_connect(self._refresh)
        insim._watch(self._before, self._after)

    @property
    def connections(self) -> Mapping[int, Connection]:
        """Every connection, by UCID (read only)."""
        return MappingProxyType(self._connections)

    @property
    def players(self) -> Mapping[int, Player]:
        """Every player in the race, by PLID (read only)."""
        return MappingProxyType(self._players)

    async def _refresh(self) -> None:
        """Forget everything and ask LFS again; the answers go through _before like any packet."""
        self._connections.clear()
        self._players.clear()
        await self._insim.request_all(IS_NCN)
        await self._insim.request_all(IS_NPL)

    def _before(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_NCN):
            connection = self._connection(packet.UCID)
            connection.username = packet.UName
            connection.name = packet.PName
            connection.admin = bool(packet.Admin)
            connection.remote = bool(packet.Flags & _REMOTE)
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
        elif isinstance(packet, IS_ISM) or (
            isinstance(packet, IS_TINY) and packet.SubT == TINY.MPE
        ):
            self._insim._handlers.call(self._refresh, (), "Roster")

    def _after(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_PLL):
            if (player := self._players.pop(packet.PLID, None)) is not None:
                player.connection.players.remove(player)
        elif isinstance(packet, IS_CNL):
            connection = self._connections.pop(packet.UCID, None)
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
