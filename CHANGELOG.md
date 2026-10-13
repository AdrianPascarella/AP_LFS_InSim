# Changelog

## Unreleased

- Chat commands take their arguments from the function: `def speed(command, kmh: int, who: str =
  "all")` for `!speed 80`. Words that do not fit are answered with the usage, and `!speed ?` with
  the usage and the docstring's first line. A function of only the `Command` works as before.
- `on_command(..., admin=True)` (LFS admins and the host) and `allow=` (your own rule).
- `insim.command_group("aic")`: `!aic start`, `!aic stop`; `!aic` alone lists them.
- Units: `car.speed_kmh`, `car.x_m`, `car.heading_deg`... on `CompCar`, `Vec`, the contacts of
  `IS_CON` / `IS_OBH` / `IS_HLV` and `OutGaugePack`, and `lfs_insim.units` with the conversions
  both ways (`Vec.from_metres()` to send a position). See [Units](docs/units.md).

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
