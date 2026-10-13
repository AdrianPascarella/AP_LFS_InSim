# Changelog

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
