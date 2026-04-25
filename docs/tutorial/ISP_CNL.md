# ISP_CNL — Connection Left

## Descripción
LFS envía este paquete cuando una conexión abandona el host. Incluye el motivo de la desconexión.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_CNL |
| ReqI | byte | 0 |
| UCID | byte | ID de la conexión que abandonó |
| Reason | byte | Motivo de abandono (LEAVR_x) |
| Total | byte | Número total de conexiones restantes (incluyendo host) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |

### Valores LEAVR_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | LEAVR_DISCO | Desconexión normal |
| 1 | LEAVR_TIMEOUT | Timeout |
| 2 | LEAVR_LOSTCONN | Conexión perdida |
| 3 | LEAVR_KICKED | Expulsado |
| 4 | LEAVR_BANNED | Baneado |
| 5 | LEAVR_SECURITY | Seguridad |
| 6 | LEAVR_CPW | Cheat protection wrong |
| 7 | LEAVR_OOS | Out of sync con el host |
| 8 | LEAVR_JOOS | Join OOS (fallo de sincronización inicial) |
| 9 | LEAVR_HACK | Paquete inválido |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CNL

RAZONES = {
    0: "desconexión normal", 1: "timeout", 2: "conexión perdida",
    3: "expulsado", 4: "baneado", 5: "seguridad",
    6: "cheat protection", 7: "out of sync", 8: "join OOS", 9: "hack"
}

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self.conexiones = {}

    def on_ISP_CNL(self, packet: ISP_CNL):
        razon = RAZONES.get(packet.Reason, f"desconocido ({packet.Reason})")
        nombre = self.conexiones.pop(packet.UCID, f"UCID {packet.UCID}")
        print(f"{nombre} desconectado: {razon} (quedan {packet.Total})")
```
