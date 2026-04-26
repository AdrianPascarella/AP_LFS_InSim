# ISP_PSF — Pit Stop Finish

## Descripción
LFS envía este paquete cuando un jugador termina su parada en pits y sale del box. Contiene el tiempo total que pasó detenido.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 12 |
| Type | byte | ISP_PSF |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| STime | unsigned | Tiempo de parada en ms |
| Spare | unsigned | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PSF

class MiInsim(InSimApp):
    def on_ISP_PSF(self, packet: ISP_PSF):
        segundos = packet.STime / 1000.0
        print(f"PLID {packet.PLID} salió del pit — tiempo en box: {segundos:.2f}s")
```
