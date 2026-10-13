# Getting started

## Install

```
pip install lfs-insim
```

Python 3.11 or newer. There are no dependencies.

## Let LFS listen

LFS only accepts InSim connections when you ask it to. In the game, type:

```
/insim=29999
```

Port 29999 is the default of `InSim`. If LFS has an admin password, pass it as
`InSim(admin_password="...")`.

## A first program

```python
from lfs_insim import Command, InSim, received

insim = InSim(name="hello", prefix="!")


@insim.on.IS_VER
def connected(packet: received.IS_VER) -> None:
    print(f"Connected to LFS {packet.Version}, InSim {packet.InSimVer}")


@insim.on_command("hello")
def hello(command: Command) -> None:
    command.reply("Hello from Python")


if __name__ == "__main__":
    insim.run()
```

- `InSim(name=..., prefix="!")` prepares the connection; nothing is sent yet. `name` is how your
  program is shown in LFS (up to 15 characters). `prefix` is one character: what users type
  before a command.
- `@insim.on.IS_VER` calls the function for every `IS_VER` packet LFS sends. The same works for
  any packet: `IS_NPL` (a player joins), `IS_LAP`, `IS_BTC` (a button click)... Type `insim.on.`
  in your editor and it lists them; `received.IS_VER` is the type of the argument. The full list,
  with what each packet is, is [Packets by direction](packets.md).
- `@insim.on_command("hello")` calls the function when someone types `!hello`.
- `insim.run()` connects and dispatches packets until Ctrl+C. If LFS is not running yet, or
  closes, it keeps trying again.

Run it, then type `!hello` in LFS.

## `def` or `async def`

Handlers may be plain functions (they run at once, so keep them quick) or `async def` (they run
as tasks and may `await`). An exception in a handler is logged and never stops the others
(while developing, `InSim(errors="raise")` stops at the first one instead; see [InSim](insim.md)).

If your program already runs an asyncio event loop, use the connection as a context manager
instead of `run()`:

```python
import asyncio

from lfs_insim import InSim

insim = InSim(name="inside-a-loop")


async def main() -> None:
    async with insim:  # connects in the background and keeps the connection up
        await asyncio.sleep(60)


asyncio.run(main())
```

## Next

[InSim](insim.md) covers everything a connection can do.
