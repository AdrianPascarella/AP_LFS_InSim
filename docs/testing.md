# Testing without LFS

`lfs_insim.testing.FakeLFS` is an InSim server on your own computer that behaves like LFS, so a
program or a plugin can be tested without the game, with pytest or anything else:

```python
import asyncio

from lfs_insim import Command, Commands, InSim
from lfs_insim.packets import IS_MSL, IS_MSO, MSO
from lfs_insim.testing import FakeLFS


def greeter(insim: InSim) -> None:
    """The plugin under test: answers !hello."""
    commands = insim.use(Commands)

    @commands.on_command("hello")
    def hello(command: Command) -> None:
        command.reply("Hello from Python")


def test_hello_is_answered() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port, prefix="!")
            insim.use(greeter)
            async with insim:
                await lfs.wait_connected()
                # What LFS sends when you type "!hello" (UCID 0 is this computer)
                await lfs.send(IS_MSO(UCID=0, UserType=MSO.PREFIX, TextStart=5, Msg="Me : !hello"))
                answer = await lfs.wait_for(IS_MSL)  # the reply to this computer
                assert answer.Msg == "Hello from Python"

    asyncio.run(main())
```

What it does on its own, as LFS would:

- answers `IS_ISI` with `IS_VER`, and closes the connection if `admin=` does not match the
  password your program sends;
- answers `TINY_VER` and `TINY_PING`; any other request (`TINY_NCN`, `TINY_NPL`, `TINY_SST`...)
  with what you put in `lfs.replies`, e.g. `lfs.replies[TINY.NCN] = [IS_NCN(...)]`;
- closes the connection on `TINY_CLOSE`; with `keepalive=30`, sends LFS's keepalive packet.

Everything else LFS would do (someone joining, chat, a race starting) your test sends with
`await lfs.send(...)`, as the packets LFS would send. What your program sends is kept in
`lfs.received`, and `await lfs.wait_for(IS_MST)` waits for the next one of a type. `lfs.drop()`
cuts the connection as if LFS had crashed, to test what happens on reconnecting.

It takes one program at a time; the real LFS takes up to 8.
