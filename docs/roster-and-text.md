# Who is who, and text

## Roster

Almost every program needs to know who is connected and who is driving. `Roster` follows the
packets for you:

```python
from lfs_insim import InSim
from lfs_insim.packets import IS_NPL
from lfs_insim.state import Roster

insim = InSim(name="who")
roster = Roster(insim)  # create it before running the connection


@insim.on(IS_NPL)
def joined(packet: IS_NPL) -> None:
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

`IS_MSO.text` is the message without the player's name in front of it.
