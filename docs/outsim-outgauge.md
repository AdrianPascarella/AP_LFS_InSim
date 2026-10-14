# OutSim and OutGauge

Both are UDP: LFS sends them to a port of your choice, and you listen. Neither needs InSim.

## OutGauge (the dashboard)

With LFS closed, set these lines in its `cfg.txt`:

```
OutGauge Mode 1
OutGauge IP 127.0.0.1
OutGauge Port 30001
```

If you also set `OutGauge ID`, LFS adds that number to every packet (`packet.ID`).

```python
from lfs_insim import OutGauge, received

gauge = OutGauge(port=30001)


@gauge.on.OutGaugePack
def dashboard(packet: received.OutGaugePack) -> None:
    print(f"{packet.Speed * 3.6:.0f} km/h at {packet.RPM:.0f} rpm")


if __name__ == "__main__":
    gauge.run()
```

LFS can send up to 100 packets a second. If you only need them now and then, keep the last one
and act on a rhythm (see [`examples/gauge.py`](../examples/gauge.py)).

## OutSim (the car's motion)

The `OutSim ...` lines of `cfg.txt` work the same way. With `OutSim Opts 0`, LFS sends
`OutSimPack`; with any other options, `OutSimPack2`, which carries only the parts those options
select. Give the same options to `OutSim`:

```python
from lfs_insim import OutSim, received
from lfs_insim.packets import OSO

outsim = OutSim(port=30002, options=OSO.MAIN | OSO.INPUTS)


@outsim.on.OutSimPack2
def motion(packet: received.OutSimPack2) -> None:
    print(packet)  # the parts that were not sent are None
```

The options must match `OutSim Opts` in `cfg.txt`, written in hexadecimal there. If a datagram
cannot be read, the library logs one warning pointing at `cfg.txt` and skips it.

## Without cfg.txt: started by InSim

An InSim program can make LFS send them, with no `cfg.txt` lines: give `InSim` the port with
`udp_port`, and send `SMALL_SSP` (OutSim) or `SMALL_SSG` (OutGauge). `UVal` is the interval in
hundredths of a second (10 = ten a second; InSim.txt does not say the unit, this is what LFS
0.8C32 does), and 0 stops it. LFS sends them only while a car is on track, the one being viewed.

```python
from lfs_insim import InSim, OutGauge, received, run
from lfs_insim.packets import IS_SMALL, SMALL

insim = InSim(name="gauges", udp_port=30001)
gauge = OutGauge(port=30001)


@insim.on_connect
def start() -> None:
    insim.send(IS_SMALL(SubT=SMALL.SSG, UVal=10))  # every 0.1 s


@gauge.on.OutGaugePack
def dashboard(packet: received.OutGaugePack) -> None:
    print(f"{packet.Speed * 3.6:.0f} km/h")


if __name__ == "__main__":
    run(insim, gauge)
```

Sent this way, OutSim is always `OutSimPack` (`OutSim(port)` with no options). With `udp_port`,
LFS also sends IS_MCI and IS_NLP to that port instead of to the InSim connection, so `InSim`
refuses `ISF.MCI` and `ISF.NLP` with it: if you need them too, open a second `InSim` without
`udp_port` (LFS takes up to 8). For both OutSim and OutGauge, use two `InSim` with different
ports: on one port the two cannot be told apart.

## Together with InSim

`run()` starts several sources in one process and one event loop:

```python
from lfs_insim import InSim, OutGauge, run

insim = InSim(name="both")
gauge = OutGauge(port=30001)

run(insim, gauge)
```

If the port is already taken, starting raises `OSError`. Port 30000 is often in use by other
programs; pick another.

`OutSim` and `OutGauge` take `errors="raise"` too, as [InSim](insim.md) does: the first error in
a handler stops it, and `run()` raises that error after closing the others.
