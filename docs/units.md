# Units

LFS sends positions, speeds and angles as whole numbers with scales of its own. The packets have
properties that give them in metres, m/s, km/h and degrees, with the scales of InSim.txt:

```python
from lfs_insim import InSim, received
from lfs_insim.packets import ISF

insim = InSim(name="speeds", flags=ISF.MCI, interval_ms=500)


@insim.on.IS_MCI
def cars(packet: received.IS_MCI) -> None:
    for car in packet.Info:
        print(car.PLID, f"{car.speed_kmh:.0f} km/h", f"heading {car.heading_deg:.0f}",
              f"at ({car.x_m:.1f}, {car.y_m:.1f}) m")
```

| Where | Properties |
| --- | --- |
| `CompCar` (in `IS_MCI`) | `x_m`, `y_m`, `z_m`, `speed_mps`, `speed_kmh`, `direction_deg`, `heading_deg`, `angvel_dps` |
| `Vec` (positions: `IS_CPP.Pos`, OutSim) | `x_m`, `y_m`, `z_m`; `Vec.from_metres(x, y, z)` to send one |
| `CarContact`, `CarContOBJ` (in `IS_CON`, `IS_OBH`, `IS_HLV`) | `x_m`, `y_m`, `speed_kmh`, `direction_deg`, `heading_deg` |
| `IS_CON`, `IS_OBH` | `closing_speed_mps` |
| `OutGaugePack` | `speed_kmh`, `speed_mph` |

Angles go from 0 to 360, anticlockwise seen from above, with 0 along the world's Y axis. The
fields themselves (`car.Speed`, `car.X`...) are still LFS's numbers, and are what is sent.

`lfs_insim.units` has the conversions as functions, both ways, for values that are not in a
packet yet:

```python
from lfs_insim import units

units.to_metres(65536)          # 1.0
units.from_metres(1.0)          # 65536
units.speed_to_mps(32768)       # 100.0
units.angle_to_degrees(32768)   # 180.0
units.degrees_to_angle(-90)     # 49152 (wrapped to 0-65535)
units.mps_to_kmh(10.0)          # 36.0
units.mps_to_mph(10.0)          # 22.37
```
