"""Who is who: the Roster follows every connection and player. Type !who in LFS to list them.

LFS must be listening for InSim: type /insim=29999 in LFS first.
"""

from lfs_insim import Command, InSim
from lfs_insim.packets import IS_NPL, IS_PLL
from lfs_insim.state import Roster
from lfs_insim.text import plain

insim = InSim(name="who", prefix="!")
roster = Roster(insim)  # asks LFS for everyone on each connection, then keeps up to date


@insim.on(IS_NPL)
def on_track(packet: IS_NPL) -> None:
    player = roster.players[packet.PLID]  # already there: the roster is updated first
    kind = "AI" if player.is_ai else "human"
    driver = player.connection.username or "this computer"
    print(f"{plain(player.name)} ({kind}, {player.car}) is on track, from {driver}")


@insim.on(IS_PLL)
def left(packet: IS_PLL) -> None:
    player = roster.players[packet.PLID]  # still there: the roster is updated after
    print(f"{plain(player.name)} left the race")


@insim.on_command("who")
def who(command: Command) -> None:
    if not roster.players:
        command.reply("Nobody is in the race")
    for player in roster.players.values():
        command.reply(f"{player.name}^8: {player.car}{' (AI)' if player.is_ai else ''}")


if __name__ == "__main__":
    insim.run()
