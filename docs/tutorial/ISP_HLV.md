# ISP_HLV — Hot Lap Validity

## Descripción
LFS envía este paquete cuando ocurre un incidente que violaría la validez de un hot lap: salida de pista, golpe contra pared, exceso de velocidad en pits, o fuera de límites. Útil para sistemas de control de validez de vueltas.

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Requiere `ISF.HLV` en `set_isi_packet()`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 20 |
| Type | byte | ISP_HLV |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| HLVC | byte | Tipo de incidente: 0=suelo / 1=pared / 4=velocidad en pit / 5=fuera de límites |
| Sp1 | byte | Reservado |
| SpW | word | Reservado |
| Time | unsigned | Timestamp en ms |
| C | CarContOBJ | Info del coche en el momento del incidente |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_HLV
from lfs_insim.insim_enums import ISF

HLVC_NOMBRES = {0: "fuera de pista", 1: "golpe de pared",
                4: "velocidad en pit", 5: "fuera de límites"}

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.HLV

    def on_ISP_HLV(self, packet: ISP_HLV):
        incidente = HLVC_NOMBRES.get(packet.HLVC, f"tipo {packet.HLVC}")
        print(f"PLID {packet.PLID}: vuelta invalidada por {incidente} "
              f"(t={packet.Time}ms)")
        # Registrar para invalidar el tiempo de vuelta en curso
```
