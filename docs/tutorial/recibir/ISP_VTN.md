# ISP_VTN — Vote Notify

## Descripción
LFS envía este paquete cuando un jugador inicia una votación (finalizar carrera, reiniciar, o calificar). El InSim puede cancelar votos con `TINY_VTC` o responder cuando se completan via `SMALL_VTA`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_VTN |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| UCID | byte | ID de conexión que inició el voto |
| Action | VOTE | Acción de voto (VOTE_x) |
| Spare2 | byte | Reservado |
| Spare3 | byte | Reservado |

### Valores VOTE_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | VOTE_NONE | Sin voto |
| 1 | VOTE_END | Fin de carrera |
| 2 | VOTE_RESTART | Reiniciar |
| 3 | VOTE_QUALIFY | Calificar |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_VTN, ISP_SMALL
from lfs_insim.insim_enums import TINY, SMALL, VOTE

class MiInsim(InSimApp):
    def on_ISP_VTN(self, packet: ISP_VTN):
        try:
            accion = VOTE(packet.Action).name.lower().replace('_', ' ')
        except ValueError:
            accion = "desconocido"
        print(f"UCID {packet.UCID} votó: {accion}")

    def on_ISP_SMALL(self, packet: ISP_SMALL):
        if packet.SubT == SMALL.VTA:
            try:
                accion = VOTE(packet.UVal).name.lower().replace('_', ' ')
            except ValueError:
                accion = "desconocido"
            print(f"Voto aprobado: {accion}")

    def cancelar_voto(self):
        self.send_ISP_TINY(ReqI=0, SubT=TINY.VTC)
```
