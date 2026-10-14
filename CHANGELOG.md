# Changelog

## Unreleased

- `await insim.request.IS_STA()`, `await insim.request_all.IS_NPL()`: the editor lists what LFS
  sends on request, and what it sends in several packets, with what each returns.
  `insim.request(IS_STA)` and `insim.request_all(IS_NPL)` still work.
- `await insim.instruct.IS_RIP(RName="race", timeout=30)` and `insim.instruct.IS_SSH(Name=...)`:
  send an instruction that LFS answers when it is done (load or move through a replay, save a
  screenshot) and wait for the reply. `insim.instruct(packet)` for one already built. See
  [Asking LFS](docs/insim.md#asking-lfs).
- `lfs_insim.packets.unpack_insim(data)`: read one InSim packet from its bytes, whatever its type.
  It refuses bytes left over after the packet. See
  [Packets from their bytes](docs/testing.md#packets-from-their-bytes).
- `PTYPE` (`FEMALE`, `AI`, `REMOTE`): the bits of `IS_NPL.PType`, e.g.
  `packet.PType & PTYPE.AI`. Also `NCNF` (`IS_NCN.Flags`: `REMOTE`), `SCHF` (`IS_SCH.Flags`:
  `SHIFT`, `CTRL`) and `HCPF` (`PlayerHCap.Flags` in `IS_PLH`: `SET_MASS`, `SET_TRES`, `SILENT`).
  InSim.txt gives these bits only in a comment, so there were no enums.

## 0.6.0

- **Breaking:** chat commands are a plugin. `commands = insim.use(Commands)`, then
  `@commands.on_command(...)` and `commands.command_group(...)`; `InSim` no longer has
  `on_command` or `command_group`. `guest_commands=` moves from `InSim` to
  `insim.use(Commands, guest_commands=...)`. Their prefix is the `InSim`'s by default, or
  `insim.use(Commands, prefix="!")`.
- Plugins: `insim.use(Type, **options)` gives the one instance of a plugin for that connection,
  made the first time. A plugin is a function or a class that takes the InSim; `lfs_insim.Plugin`
  is the base class for the second kind, and making a second one of the same type directly raises
  `ValueError`.
- The same `request()` or `request_all()` made while one waits is sent once, and both get the
  answer, unless something has arrived from LFS in between (it may have changed the answer).
- `insim.need(flags=..., interval_ms=...)`: what a plugin needs in `IS_ISI`, added to the rest
  (flags added up, the shortest interval kept). Asked for while connected, from the next connection.
- `insim.reserve_click_ids(count)`: a range of button ClickIDs that no other plugin gets.
- `@insim.on_close`: once, when the InSim is closed (also on Ctrl+C), for a plugin to save what it
  keeps.
- When LFS closes the connection before answering `IS_ISI`, the warning also names the other cause
  seen: 8 InSim programs already connected (LFS's limit).
- `lfs_insim.testing.FakeLFS`: a fake LFS to test a program or a plugin without the game. See
  [Testing without LFS](docs/testing.md).
- New guide pages: [Plugins](docs/plugins.md) and [Testing without LFS](docs/testing.md). The
  examples are plugins (functions), and `examples/together.py` runs three of them in one program.
- `await roster.ready()` waits until the roster has the whole picture of the connection.
- `Roster` is a plugin: `roster = insim.use(Roster)` (`Roster(insim)` still works, once). The chat
  commands now share it instead of making a second roster that asked LFS for everyone again.

## 0.5.0

- Chat commands as a guest in someone else's server: only this computer may use them unless
  `InSim(guest_commands="everyone")`; `admin=True` means this computer; `command.reply()` answers
  you with `IS_MSL` (LFS refuses `IS_MTC` from a guest) and anyone else in the public chat;
  `/o !command` keeps a command to yourself. `Command.local` says whether this computer typed it.
  See [As a guest](docs/insim.md#chat-commands).
- `on_command(..., prefix=".")` and `command_group(..., prefix=".")`: a prefix of their own
  instead of the `InSim`'s, so `!who` and `.who` can be different commands. See
  [Chat commands](docs/insim.md#chat-commands).
- `roster.guest` and `roster.local` (this computer's connection). Programs with chat commands now
  always have a roster of their own.
- `Roster` no longer logs an error when the connection closes while it asks LFS for everyone.

## 0.4.0

- Chat commands take their arguments from the function: `def speed(command, kmh: int, who: str =
  "all")` for `!speed 80`. Words that do not fit are answered with the usage, and `!speed ?` with
  the usage and the docstring's first line. A function of only the `Command` works as before.
- `on_command(..., admin=True)` (LFS admins and the host) and `allow=` (your own rule).
- `insim.command_group("aic")`: `!aic start`, `!aic stop`; `!aic` alone lists them.
- Units: `car.speed_kmh`, `car.x_m`, `car.heading_deg`... on `CompCar`, `Vec`, the contacts of
  `IS_CON` / `IS_OBH` / `IS_HLV` and `OutGaugePack`, and `lfs_insim.units` with the conversions
  both ways (`Vec.from_metres()` to send a position). See [Units](docs/units.md).
- `insim.watch(before=..., after=...)`: see every packet before and after the handlers, to keep
  state of your own the way `Roster` does (it now uses only this). `InSimPacket`, the base of
  every packet, is in `lfs_insim.packets` to annotate them. See
  [Your own state](docs/roster-and-text.md#your-own-state).
- `IS_REO(NumP=3, PLID=[5, 2, 9])` and `IS_HCP(Info=[...])` with fewer items than the packet holds:
  the rest is filled with zeros (no player, no handicap) when sent. Other fixed lists, like
  `Tyres`, must still be complete.
- Packets that arrive together are handled one after the other: a packet's `async def` handlers
  take their first step, and `Roster` and `watch(after=)` see it, before the next packet. Before,
  a connection that left and a new one with the same UCID, read at once, could vanish from
  `Roster`.

## 0.3.0

- `@insim.on_disconnect`: called when a connection ends (LFS closed, lost, or you closed), once
  for each `on_connect`. `insim.reconnected` says, in `on_connect`, whether it is a reconnection.
- `InSim(errors="raise")` (and `OutSim`, `OutGauge`): the first error in a handler closes and is
  raised by `run()`, `wait_closed()` and `async with`, instead of only being logged. For
  development; the default stays `"log"`.
- `lfs_insim.text.Colour` and `coloured()`: colours to send (`f"{Colour.RED}Stop"`).
- `close()` closes once: a second call (from a handler and from `async with`, say) waits for the
  first instead of cancelling it half way, and `wait_closed()` returns when the closing is done.
- `@insim.on.IS_TINY(TINY.MPE)` and `@insim.on.IS_SMALL(SMALL.VTA, SMALL.RTP)`: the function is
  called only for those subtypes. `@insim.on.IS_TINY` alone still gets all of them.
  `insim.on(IS_TINY, TINY.MPE)` is the same. Only the subtypes that LFS sends are accepted, as
  InSim.txt marks them (`TINY.NCN` is a request: an error). Checked by the type checker and when
  run; the list is in [Packets by direction](docs/packets.md#subtypes).

## 0.2.0

- `@insim.on.IS_NPL` and `insim.send.IS_MST(Msg=...)`: the editor lists only the packets LFS sends
  under `insim.on.` and only the packets a program sends under `insim.send.`, and `send.IS_XXX`
  shows the fields of the packet. Same for `@outsim.on.OutSimPack2` and `@gauge.on.OutGaugePack`.
  `insim.on(IS_NPL)` and `insim.send(IS_MST(...))` still work and do the same.
- `lfs_insim.received` and `lfs_insim.sent`: the same packet classes, listed by direction
  (`packet: received.IS_NPL`).
- Every packet knows its direction (`info`, `instruction` or `both ways`, as InSim.txt marks it).
  `on()` of a packet LFS never sends, or `send()` of one only LFS sends, is an error in mypy and a
  `TypeError` when run.
- New page [Packets by direction](docs/packets.md); guide and examples use the new forms.

## 0.1.0

First release (alpha). The API may still change before 1.0.

- InSim over TCP: every packet of the protocol, generated from the specification published at
  lfs.net; handlers with `@insim.on`, chat commands, `say()`/`command()`, `request()`/
  `request_all()`, `every()`, and automatic reconnection.
- OutSim (`OutSimPack` and `OutSimPack2`) and OutGauge over UDP, alone or together with InSim
  through `run()`.
- `lfs_insim.state.Roster` (connections and players) and `lfs_insim.text` (`plain`,
  `strip_colours`).
- Checked against a real LFS 0.8C, and by the tests against a fake LFS.
