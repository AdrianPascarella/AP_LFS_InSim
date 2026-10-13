# InSim

```python
from lfs_insim import InSim

insim = InSim(name="my program", prefix="!")
```

The options of `InSim(...)`: `admin_password`, `host` and `port` (default `127.0.0.1:29999`),
`flags` (the `ISF` options, such as `ISF.MCI | ISF.LOCAL`), `interval_ms` (time between
`IS_MCI`/`IS_NLP` packets), `prefix` and `errors`.

`errors` says what happens when one of your handlers raises an exception. With `"log"` (the
default) it is logged and everything goes on: right for a program that runs for hours. With
`"raise"`, for development, the first error closes the connection and `run()` raises it, so a
bug cannot go unnoticed in the log.

```python
insim = InSim(name="my program", errors="raise")   # while developing
```

## Receiving

```python
from lfs_insim import received


@insim.on.IS_NPL
def joined(packet: received.IS_NPL) -> None:
    print(packet.PName, "is on track in a", packet.CName)
```

Type `insim.on.` and the editor lists the packets LFS sends. Annotating the argument with
`received.IS_NPL` lists them again; it is the same class as `lfs_insim.packets.IS_NPL`. The
list, with the direction of each packet, is [Packets by direction](packets.md). The long form
`@insim.on(IS_NPL)` does exactly the same.

`IS_TINY` and `IS_SMALL` are general purpose packets with a subtype (`SubT`). To receive only
some of them, name them:

```python
from lfs_insim.packets import SMALL, TINY


@insim.on.IS_TINY(TINY.MPE)                      # only this subtype
def multiplayer_ended(packet: received.IS_TINY) -> None: ...


@insim.on.IS_SMALL(SMALL.VTA, SMALL.RTP)         # or any of several
def timing(packet: received.IS_SMALL) -> None: ...
```

Without names (`@insim.on.IS_TINY`) the function gets every subtype. Only the subtypes that LFS
sends are accepted (the list is in [Packets by direction](packets.md#subtypes)): `TINY.NCN`
is a request that your program sends, so `@insim.on.IS_TINY(TINY.NCN)` would never run. That,
a subtype of the other packet, or one of a packet without subtypes, is an error in the editor
and a `TypeError` when run.

Text fields are `str`. They keep LFS's `^` codes; see [text](roster-and-text.md#text).

### Chat commands

Chat commands are a plugin: `commands = insim.use(Commands)`. With a prefix (`InSim(prefix="!")`,
or `insim.use(Commands, prefix="!")`), `@commands.on_command("speed")` is called for `!speed 80`
with a `Command` first. The parameters after it are the words typed, converted to their annotation:

```python
from lfs_insim import Command, Commands

commands = insim.use(Commands)


@commands.on_command("speed")
def speed(command: Command, kmh: int, who: str = "all") -> None:
    """Set the speed limit."""
    # !speed 80 Bob -> kmh == 80, who == "Bob"
    # command.ucid: the connection that typed it; command.plid: its player (0 if none)
    command.reply(f"Limit for {who}: {kmh} km/h")  # only the sender sees this
```

Arguments can be `str` (no annotation means `str`), `int` or `float`; a default makes one
optional, and `*words: str` takes all the remaining ones. Words that do not fit are answered with
the usage, and the function is not called:

```text
!speed abc   ->  !speed: kmh must be a whole number, not 'abc'. Use: !speed <kmh> [who]
!speed ?     ->  !speed <kmh> [who]: Set the speed limit.
```

A function that takes only the `Command` gets whatever was typed in `command.args`, unchecked.

**Who may use it.** `admin=True` keeps a command for LFS admins and the host (UCID 0). `allow` is
a function of the `Command` for your own rule; the others are told they may not use it:

```python
@commands.on_command("kick", admin=True)
def kick(command: Command, name: str) -> None: ...


@commands.on_command("boost", allow=lambda command: command.ucid in {3, 5})
def boost(command: Command) -> None: ...
```

**Groups.** Several commands under one name: `!aic start 3`, `!aic stop`. `!aic` alone lists
them. `admin` and `allow` on the group apply to all of its commands.

```python
aic = commands.command_group("aic", admin=True)


@aic.on_command("start")
def start(command: Command, plid: int) -> None:
    """Start driving a car."""


@aic.on_command("stop")
def stop(command: Command) -> None: ...
```

Register commands before running. Names are matched in any case. Commands are hidden from the
other users. A command with no function is left alone, since it may be meant for another program.
`command.local` says whether it was typed on this computer.

**A prefix of their own.** A command or a group may use another prefix than the `InSim`'s: one
character, not a letter or digit. `!who` and `.who` can then be two different commands, and
`InSim()` needs no prefix if every command brings its own.

```python
@commands.on_command("who", prefix=".")
def who(command: Command) -> None: ...


admin_tools = commands.command_group("adm", prefix="#", admin=True)  # #adm kick Bob, #adm ...
```

As host, LFS hides from the others only the messages that start with the `InSim`'s prefix: a
command with another one is seen by everyone.

**As a guest in someone else's server.** When your LFS has joined a server that is not yours,
your program still gets the chat, but it is not the host, so things change:

- Only this computer may use your commands; what others type is ignored, without an answer.
  `insim.use(Commands, guest_commands="everyone")` lets everyone in, and `allow` still applies.
- `admin=True` means this computer only: the server's admins are not yours.
- Commands are not hidden: everyone in the server sees `!speed 80`. To keep one to yourself,
  type `/o !speed 80`: only your InSim sees it.
- `command.reply()` shows the answer only to you (`IS_MSL`). Someone else is answered in the
  public chat, because a guest cannot write to just one connection.

`Roster` tells you where you are: `roster.guest` and `roster.local` (this computer's
connection; see [Who is who](roster-and-text.md)).

### On connection, and on a rhythm

```python
@insim.on_connect
async def start() -> None:
    ...  # after every connection and reconnection: ask LFS for the initial state here
    if insim.reconnected:
        ...  # not the first connection: LFS has removed your buttons, so draw them again


@insim.on_disconnect
def stop() -> None:
    ...  # the connection has ended (LFS closed, was lost, or you closed): it cannot send


@insim.every(2)
async def tick() -> None:
    ...  # every 2 seconds while connected; calls never overlap
```

## Sending

```python
insim.say("Hello everyone")        # the chat; everyone sees it
insim.say("Just you", to=3)        # only the connection with UCID 3 (0 = this computer)
insim.command("/restart")          # an LFS command
insim.send.IS_MST(Msg="/end")      # any packet that a program sends
```

Type `insim.send.` and the editor lists the packets a program sends, with their fields. To
send several at once, or one already built, use `insim.send(IS_MST(Msg="/end"), other)`.

`say()` picks the right packet for you and raises `ValueError` if the text is too long
(`PacketError` is a `ValueError`). Sending raises `ConnectionError` if LFS is not connected.

## Asking LFS

```python
from lfs_insim.packets import IS_NCN, IS_STA


@insim.every(5)
async def report() -> None:
    state = await insim.request(IS_STA)            # one packet
    everyone = await insim.request_all(IS_NCN)     # a list: one per connection
    print(state.NumP, len(everyone))
```

`request` raises `TimeoutError` if LFS does not answer within 2 seconds (change it with
`timeout=`). The answers also reach your `@insim.on` handlers. Asking for a packet that LFS does
not send on request raises `TypeError` and says which function to use instead.

## Buttons

Buttons are `IS_BTN` packets; clicks come back as `IS_BTC` (and `IS_BTT` for text typed into a
button). Each button of your program needs its own `ClickID` (0 to 239), and sending a button
again with the same `ClickID` updates it. See [`examples/buttons.py`](../examples/buttons.py).

## Closing

`insim.run()` ends with Ctrl+C. From a handler or an event loop, `await insim.close()` sends the
goodbye to LFS and stops reconnecting.

## Without `run()`

`await insim.connect()` connects once (no reconnection) and returns; `wait_closed()` waits until
it ends. Use `async with insim:` or `run()` unless you need that.
