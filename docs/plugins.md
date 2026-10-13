# Plugins

A plugin is a part of a program: a function that takes the `InSim` connection and adds to it what
it does (handlers, chat commands, state). `insim.use(plugin)` adds it. Written this way, the same
file runs alone, and several plugins can share one connection, one `Roster` and one set of chat
commands.

## Writing one

```python
from lfs_insim import InSim, received
from lfs_insim.state import Roster
from lfs_insim.text import plain


def laps(insim: InSim) -> None:
    """Print every lap with the driver's name."""
    roster = insim.use(Roster)

    @insim.on.IS_LAP
    def lap(packet: received.IS_LAP) -> None:
        player = roster.players[packet.PLID]
        print(f"{plain(player.name)}: lap {packet.LapsDone} in {packet.LTime} ms")


if __name__ == "__main__":
    insim = InSim(name="laps")
    insim.use(laps)
    insim.run()
```

Run the file and it works alone. Import it from another program and `insim.use(laps)` adds it
there: the `if __name__ == "__main__":` part only runs when the file is run.

## Running several together

```python
from lfs_insim import InSim

from hello import hello  # plugins of yours, in hello.py and laps.py
from laps import laps

insim = InSim(name="together", prefix="!")
insim.use(hello)
insim.use(laps)
insim.run()
```

[`examples/together.py`](../examples/together.py) does this with three examples. The program
that puts them together decides what is the connection's: its name, the admin password, and the
`prefix` of the chat commands.

## Sharing

`insim.use(...)` gives **one of each per connection**: the first call makes it, and the next ones
give the same. That is how plugins share:

- `insim.use(Roster)`: who is connected and who is driving, asked for once.
- `insim.use(Commands)`: the chat commands. Two plugins with the same command are an error, when
  the second one is added.
- Your own plugins: a plugin that uses another gets the same one as everybody else.

If two plugins ask LFS for the same thing at the same time (`await insim.request(IS_STA)`), it is
asked for once and both get the answer.

The functions given to `@insim.on_connect` start at the same time, so one may look at the roster
before LFS has answered. `await roster.ready()` waits until the roster has everybody:

```python
from lfs_insim import InSim
from lfs_insim.state import Roster


def greeter(insim: InSim) -> None:
    roster = insim.use(Roster)

    @insim.on_connect
    async def start() -> None:
        await roster.ready()
        insim.say(f"{len(roster.connections)} connected")
```

## What a plugin needs from LFS

Some packets only come if they are asked for when connecting, in `IS_ISI`. A plugin asks for what
it needs, and the connection adds up what every plugin asked for:

```python
from lfs_insim import InSim
from lfs_insim.packets import ISF


def positions(insim: InSim) -> None:
    insim.need(flags=ISF.MCI, interval_ms=100)  # IS_MCI, every 100 ms
```

Of the intervals, the shortest one is kept: a plugin that wants fewer packets skips some. LFS
reads these on connecting, so ask for them when the plugin is added, not later.

## Buttons

Each button has a `ClickID` (0 to 239), and two plugins must not use the same one. Ask the
connection for yours:

```python
from lfs_insim import InSim


def menu(insim: InSim) -> None:
    first, last = insim.reserve_click_ids(2)
```

To remove buttons, remove your own (`IS_BFN` with `BFN.DEL_BTN` and your range):
`BFN.CLEAR` removes every plugin's. [`examples/buttons.py`](../examples/buttons.py) does both.

## Saving on closing

`@insim.on_close` runs once when the program ends (Ctrl+C, `close()`, the end of `async with`):
the place to save what a plugin keeps.

## Options, and plugins as classes

`insim.use(plugin, name=value)` passes options to the plugin, the first time:

```python
from lfs_insim import InSim


def greeting(insim: InSim, *, text: str = "Hello") -> None:
    insim.on_connect(lambda: insim.say(text))


insim = InSim()
insim.use(greeting, text="Welcome")
```

Asking again with other options is an error: there is only one of each.

A plugin may also be a class, when it is worth it: to keep state as attributes, or to be the base
of others. Derive it from `lfs_insim.Plugin`:

```python
from lfs_insim import InSim, Plugin
from lfs_insim.state import Roster


class Camera(Plugin):
    def __init__(self, insim: InSim, *, speed: float = 1.0) -> None:
        super().__init__(insim)  # registers it: a second Camera(insim) is an error
        self.speed = speed
        self.roster = insim.use(Roster)
```

`camera = insim.use(Camera, speed=2.0)` makes it and returns it, with its type for the editor.

## Combining, or inheriting

Say there is an `AIControl` plugin that drives AI cars, and you want `AITraffic` and `AIDrift`,
which drive them in other ways, and a program with both.

- If `AITraffic` **inherits** from `AIControl`, a program with `AITraffic` and `AIDrift` has two
  `AIControl`s, which know nothing of each other and may send orders to the same car. Inheriting
  is for variants that never run together.
- To run them together, **combine**: `AITraffic` and `AIDrift` use `insim.use(AIControl)`, so
  there is one, which knows which car is whose and sends the orders.

## One program, or several

LFS accepts up to 8 InSim connections at once on its port, and each one gets every packet. So
plugins can also run as separate programs, or in one program with a connection each:
`lfs_insim.run(a, b)` runs several `InSim`s together. Then they share nothing: each has its own
roster and asks LFS for its own things. One connection with several plugins shares state and
leaves connections free; separate connections keep each program apart.

## Testing a plugin

See [Testing without LFS](testing.md).
