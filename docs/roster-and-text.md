# Who is who, and text

## Roster

Almost every program needs to know who is connected and who is driving. `Roster` follows the
packets for you:

```python
from lfs_insim import InSim, received
from lfs_insim.state import Roster

insim = InSim(name="who")
roster = Roster(insim)  # create it before running the connection


@insim.on.IS_NPL
def joined(packet: received.IS_NPL) -> None:
    player = roster.players[packet.PLID]
    print(player.name, "is driven from", player.connection.username or "this computer")
```

- `roster.connections` maps UCID to a `Connection` (`username`, `name`, `admin`, `remote`,
  `players`).
- `roster.players` maps PLID to a `Player` (`name`, `plate`, `car`, `is_ai`, `in_pits`,
  `connection`). An AI belongs to the connection that added it.
- On every connection and reconnection it asks LFS for everyone, so it starts complete.
- It is already up to date in your handlers: when someone arrives it is updated before them, and
  when someone leaves (`IS_PLL`, `IS_CNL`) after them, so you can still look up who is leaving.
- It is read only: change things in LFS, not in the roster.

See [`examples/who.py`](../examples/who.py).

### Your own state

`Roster` is built on `insim.watch()`, and you can use it for state of your own. `before` sees
every packet before the handlers, so they find the packet already counted; `after` sees it after
them (and after the first step of the `async def` ones), so they can still look up what is about
to go:

```python
from lfs_insim import InSim
from lfs_insim.packets import IS_LAP, IS_PLL, InSimPacket


class Laps:
    def __init__(self, insim: InSim) -> None:
        self.done: dict[int, int] = {}  # PLID to laps done
        insim.watch(before=self._before, after=self._after)

    def _before(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_LAP):
            self.done[packet.PLID] = packet.LapsDone

    def _after(self, packet: InSimPacket) -> None:
        if isinstance(packet, IS_PLL):
            self.done.pop(packet.PLID, None)
```

Give one of them or both. They must be plain `def` (an `async def` is a `TypeError`): they run
to the end before anything else happens. An error in one is handled like an error in a handler
(`errors="log"` or `"raise"`).

## Text

Text fields (`PName`, `Msg`, ...) arrive as `str`, with LFS's `^` codes kept as LFS sends them:
colours (`^1`, `^7`...) and escaped characters (`^v` is `|`, `^h` is `#`, `^^` is `^`). The
library has already turned LFS's code-page bytes into the right characters, so accents and other
alphabets just work.

```python
from lfs_insim.text import plain, strip_colours

plain("^4^h773 ^7Bob")         # '#773 Bob'  to print or save
strip_colours("^1Red ^7car")   # 'Red car'   only the colours
```

Use `plain()` to show text outside LFS. Do not send its result back to LFS: the escapes are
gone, so send the original.

To send colours, put a `Colour` in the text. `coloured()` adds the colour and goes back to the
default colour after the text:

```python
from lfs_insim.text import Colour, coloured

insim.say(f"{Colour.RED}Stop{Colour.DEFAULT} now")   # '^1Stop^8 now'
insim.say(coloured("Stop", Colour.RED) + " now")      # the same
```

`Colour` has `BLACK`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `MAGENTA`, `CYAN`, `WHITE` and
`DEFAULT`.

`IS_MSO.text` is the message without the player's name in front of it.
