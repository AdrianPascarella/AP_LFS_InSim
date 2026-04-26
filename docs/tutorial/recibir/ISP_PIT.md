# ISP_PIT — Pit Stop Start

## Descripción
LFS envía este paquete cuando un jugador entra al garage para una parada en pits (detención completa en el box). Contiene información sobre el trabajo realizado, neumáticos cambiados y combustible añadido.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 24 |
| Type | byte | ISP_PIT |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| LapsDone | word | Laps completados |
| Flags | PIF | Flags de jugador (PIF_x) |
| FuelAdd | byte | Combustible añadido (% si /showfuel yes; 255 si no) |
| Penalty | PENALTY | Penalización actual (PENALTY_x) |
| NumStops | byte | Número de paradas en pits |
| Sp3 | byte | Reservado |
| Tyres | TYRE[4] | Neumáticos cambiados (TYRE_x; NOT_CHANGED=255) |
| Work | PSE | Trabajo realizado (bitmask PSE_x) |
| Spare | unsigned | Reservado |

### Bitmask PSE_x (Pit Work Flags)
`PSE_NOTHING`(0), `PSE_STOP`(1), `PSE_FR_DAM`(2/front repair), `PSE_FR_WHL`(3/front wheel), `PSE_LE_FR_DAM`(4), `PSE_LE_FR_WHL`(5), `PSE_RI_FR_DAM`(6), `PSE_RI_FR_WHL`(7), `PSE_RE_DAM`(8), `PSE_RE_WHL`(9), `PSE_LE_RE_DAM`(10), `PSE_LE_RE_WHL`(11), `PSE_RI_RE_DAM`(12), `PSE_RI_RE_WHL`(13), `PSE_BODY_MINOR`(14), `PSE_BODY_MAJOR`(15), `PSE_SETUP`(16), `PSE_REFUEL`(17)

### Valores TYRE_x (compuestos)
`TYRE_R1`(0), `TYRE_R2`(1), `TYRE_R3`(2), `TYRE_R4`(3), `TYRE_ROAD_SUPER`(4), `TYRE_ROAD_NORMAL`(5), `TYRE_HYBRID`(6), `TYRE_KNOBBLY`(7), `NOT_CHANGED`(255)

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PIT
from lfs_insim.insim_enums import PSE, TYRE, NOT_CHANGED

class MiInsim(InSimApp):
    def on_ISP_PIT(self, packet: ISP_PIT):
        repostaje = bool(packet.Work & PSE.REFUEL)
        neumaticos_cambiados = [TYRE(t).name for t in packet.Tyres if t != NOT_CHANGED]
        print(f"PLID {packet.PLID} - Pit #{packet.NumStops}")
        if repostaje and packet.FuelAdd != 255:
            print(f"  Combustible añadido: {packet.FuelAdd}%")
        if neumaticos_cambiados:
            print(f"  Neumáticos cambiados: {neumaticos_cambiados}")
```
