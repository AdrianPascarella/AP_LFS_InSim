# InSim

```python
from lfs_insim import InSim

insim = InSim(name="my program", prefix="!")
```

The options of `InSim(...)`: `admin_password`, `host` and `port` (default `127.0.0.1:29999`),
`flags` (the `ISF` options, such as `ISF.MCI | ISF.LOCAL`), `interval_ms` (time between
`IS_MCI`/`IS_NLP` packets) and `prefix`.

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


@insim.on.IS_SMALL(SMALL.STP, SMALL.RTP)         # or any of several
def timing(packet: received.IS_SMALL) -> None: ...
```

Without names (`@insim.on.IS_TINY`) the function gets every subtype. A subtype of the other
packet, or of a packet without subtypes, is an error in the editor and a `TypeError` when run.

Text fields are `str`. They keep LFS's `^` codes; see [text](roster-and-text.md#text).

### Chat commands

With a `prefix`, `@insim.on_command("kick")` is called for `!kick Bob` with a `Command`:

```python
from lfs_insim import Command


@insim.on_command("kick")
def kick(command: Command) -> None:
    # command.name == "kick", command.args == ("Bob",)
    # command.ucid: the connection that typed it; command.plid: its player (0 if none)
    command.reply(f"Kicking {', '.join(command.args)}")  # only the sender sees this
```

Names are matched in any case. Commands are hidden from the other users. A command with no
function is left alone, since it may be meant for another program.

### On connection, and on a rhythm

```python
@insim.on_connect
async def start() -> None:
    ...  # after every connection and reconnection: ask LFS for the initial state here


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
