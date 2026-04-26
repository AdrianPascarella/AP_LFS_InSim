# OutSimPack — OutSim Legacy

## Descripción
Paquete de telemetría física del coche en formato legado. LFS lo envía por UDP al puerto configurado en `cfg.txt` cuando se activa mediante `SMALL.SSP`. Contiene posición, velocidad, aceleración, orientación y un ID de identificación. Para el formato moderno y configurable usar `OutSimPack2`.

## Dirección
**LFS → InSim (UDP)**

## Activación
Enviar `ISP_SMALL(SubT=SMALL.SSP, UVal=intervalo_ms)` desde `on_connect()`. `UVal=0` detiene el envío.

No requiere flags ISF ni configuración en `cfg.txt` (a diferencia de OutSimPack2).

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Time | unsigned | Timestamp en ms |
| AngVel | Vector (3 floats) | Velocidad angular (rad/s) |
| Heading | float | Antihorario desde arriba (Z) |
| Pitch | float | Antihorario desde la derecha (X) |
| Roll | float | Antihorario desde adelante (Y) |
| Accel | Vector (3 floats) | Aceleración X, Y, Z |
| Vel | Vector (3 floats) | Velocidad X, Y, Z |
| Pos | Vec (3 ints) | Posición X, Y, Z (1m = 65536) |
| ID | int | OutSim ID configurado en cfg.txt |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import SMALL
from lfs_insim.packets.outsim import OutSimPack
import math

class MiInsim(InSimApp):

    def on_connect(self):
        # Activar envío cada 100 ms
        self.send_ISP_SMALL(SubT=SMALL.SSP, UVal=100)

    def on_OutSimPack(self, packet: OutSimPack):
        vx, vy, vz = packet.Vel
        speed_kmh = math.sqrt(vx**2 + vy**2 + vz**2) * 3.6
        x = packet.Pos[0] / 65536
        y = packet.Pos[1] / 65536
        print(f"pos=({x:.1f}, {y:.1f}) vel={speed_kmh:.1f} km/h")
```
