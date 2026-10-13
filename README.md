# lfs_insim

A Python library for the [Live for Speed](https://www.lfs.net) InSim protocol: **InSim** (TCP),
**OutSim** and **OutGauge** (UDP). Plain `import`, no framework, no dependencies.

> **Status: alpha.** The library is checked against a real LFS (0.8C), but its API may still
> change before 1.0.

- Python 3.11 or newer, no dependencies, fully typed.
- Every packet class is generated from the official specification published at lfs.net, so the
  fields are named exactly as in `InSim.txt`.
- Handlers with decorators, `await insim.request(...)`, chat commands, a roster of connections
  and players, and automatic reconnection if LFS restarts.

## Install

```
pip install lfs-insim
```

## A first program

In LFS, type `/insim=29999` to let it listen for InSim. Then run this and type `!hello` in the
game:

```python
from lfs_insim import Command, InSim
from lfs_insim.packets import IS_VER

insim = InSim(name="hello", prefix="!")  # admin_password="..." if LFS has one


@insim.on(IS_VER)
def connected(packet: IS_VER) -> None:
    print(f"Connected to LFS {packet.Version}, InSim {packet.InSimVer}")


@insim.on_command("hello")
def hello(command: Command) -> None:
    command.reply("Hello from Python")


if __name__ == "__main__":
    insim.run()  # blocks until Ctrl+C; reconnects on its own if LFS restarts
```

## What is in the box

| You want to… | Use |
| --- | --- |
| Receive a packet | `@insim.on(IS_XXX)` |
| Answer a chat command | `@insim.on_command("name")` |
| Send packets, chat or `/commands` | `insim.send(...)`, `insim.say(...)`, `insim.command(...)` |
| Ask LFS and wait for the answer | `await insim.request(IS_STA)`, `request_all(...)` |
| Run something on a rhythm | `@insim.every(seconds)` |
| Know who is connected and who is driving | `lfs_insim.state.Roster` |
| Read car physics or the dashboard | `OutSim` and `OutGauge` |
| Show LFS text without colour codes | `lfs_insim.text.plain(...)` |

The guide is in [`docs/`](docs/README.md). Short, runnable programs are in [`examples/`](examples): `hello.py`, `who.py`, `buttons.py` and
`gauge.py`.

## Development

This repository is worked on with the notes in [`docs/dev`](docs/dev) (in Spanish). To check
everything: `python scripts/verify.py`.

## License

MIT — see [LICENSE](LICENSE).
