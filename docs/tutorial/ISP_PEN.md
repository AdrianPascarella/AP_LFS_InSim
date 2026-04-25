# ISP_PEN — Penalty

## Descripción
LFS envía este paquete cuando a un jugador se le da o se le borra una penalización. También se envía en casos de autocross (falsa salida, ruta incorrecta, área restringida).

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_PEN |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| OldPen | byte | Penalización anterior (PENALTY_x) |
| NewPen | byte | Nueva penalización (PENALTY_x) |
| Reason | byte | Motivo de la penalización (PENR_x) |
| Sp3 | byte | Reservado |

### Valores PENALTY_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | PENALTY_NONE | Sin penalización |
| 1 | PENALTY_DT | Drive-through |
| 2 | PENALTY_DT_VALID | Drive-through (puede cumplirse) |
| 3 | PENALTY_SG | Stop-go |
| 4 | PENALTY_SG_VALID | Stop-go (puede cumplirse) |
| 5 | PENALTY_30 | 30 segundos |
| 6 | PENALTY_45 | 45 segundos |

### Valores PENR_x (motivos)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | PENR_UNKNOWN | Desconocido o borrado |
| 1 | PENR_ADMIN | Por admin |
| 2 | PENR_WRONG_WAY | Conducción en sentido contrario |
| 3 | PENR_FALSE_START | Salida anticipada |
| 4 | PENR_SPEEDING | Exceso de velocidad en pit lane |
| 5 | PENR_STOP_SHORT | Stop-go demasiado corto |
| 6 | PENR_STOP_LATE | Parada obligatoria demasiado tarde |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PEN

PENALTY_NONE = 0
PENR_WRONG_WAY = 2
PENR_FALSE_START = 3

class MiInsim(InSimApp):
    def on_ISP_PEN(self, packet: ISP_PEN):
        if packet.NewPen == PENALTY_NONE:
            print(f"PLID {packet.PLID}: penalización borrada")
        else:
            razones = {2: "sentido contrario", 3: "falsa salida",
                       4: "velocidad en pit", 1: "admin"}
            razon = razones.get(packet.Reason, f"cod:{packet.Reason}")
            print(f"PLID {packet.PLID}: penalización {packet.NewPen} por {razon}")
```
