# ISP_BTC — Button Click

## Descripción
LFS envía este paquete cuando un usuario hace click en un botón clickeable (con `ISB_CLICK` en BStyle). El `ReqI` devuelto corresponde al enviado en el `IS_BTN` original.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_BTC |
| ReqI | byte | ReqI del IS_BTN original |
| UCID | byte | Conexión que hizo click (0 si es local) |
| ClickID | byte | ID del botón (como se especificó en IS_BTN) |
| Inst | byte | Usado internamente por InSim |
| CFlags | ISB_CLICK | Flags del click (LMB, RMB, CTRL, SHIFT) |
| Sp3 | byte | Reservado |

### Flags CFlags (tipo de click)
| Flag | Valor | Descripción |
|------|-------|-------------|
| ISB_LMB | 1 | Click izquierdo |
| ISB_RMB | 2 | Click derecho |
| ISB_CTRL | 4 | CTRL + click |
| ISB_SHIFT | 8 | SHIFT + click |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_BTC
from lfs_insim.insim_enums import ISB_CLICK, BFN

BTN_ESTADO   = 10
BTN_SALIR    = 11
BTN_OPCIONES = 12

class MiInsim(InSimApp):
    def on_ISP_BTC(self, packet: ISP_BTC):
        if packet.ClickID == BTN_SALIR:
            if packet.CFlags & ISB_CLICK.LMB:
                print(f"UCID {packet.UCID} presionó Salir")
                self.borrar_todos_los_botones(packet.UCID)
        elif packet.ClickID == BTN_OPCIONES:
            if packet.CFlags & ISB_CLICK.RMB:
                print("Click derecho en Opciones")

    def borrar_todos_los_botones(self, ucid: int):
        self.send_ISP_BFN(SubT=BFN.CLEAR, UCID=ucid, ClickID=0, ClickMax=0)
```
