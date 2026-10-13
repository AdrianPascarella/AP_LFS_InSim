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
from lfs_insim import OutGauge
from lfs_insim.packets import OutGaugePack

gauge = OutGauge(port=30001)


@gauge.on(OutGaugePack)
def dashboard(packet: OutGaugePack) -> None:
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
from lfs_insim import OutSim
from lfs_insim.packets import OSO, OutSimPack2

outsim = OutSim(port=30002, options=OSO.MAIN | OSO.INPUTS)


@outsim.on(OutSimPack2)
def motion(packet: OutSimPack2) -> None:
    print(packet)  # the parts that were not sent are None
```

The options must match `OutSim Opts` in `cfg.txt`, written in hexadecimal there. If a datagram
cannot be read, the library logs one warning pointing at `cfg.txt` and skips it.

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
