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
| HLVC | HLVC | Tipo de incidente: GROUND / WALL / SPEEDING / OUT_OF_BOUNDS |
| Sp1 | byte | Reservado |
| SpW | word | Reservado |
| Time | unsigned | Timestamp en ms |
| C | CarContOBJ | Info del coche en el momento del incidente |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_HLV
from lfs_insim.insim_enums import ISF, HLVC

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.HLV

    def on_ISP_HLV(self, packet: ISP_HLV):
        nombre = HLVC(packet.HLVC).name.lower().replace('_', ' ')
        print(f"PLID {packet.PLID}: vuelta invalidada por {nombre} "
              f"(t={packet.Time}ms)")
        # Registrar para invalidar el tiempo de vuelta en curso
```
