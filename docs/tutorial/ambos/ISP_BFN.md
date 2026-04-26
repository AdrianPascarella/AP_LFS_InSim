# ISP_BFN — Button Function

## Descripción
Paquete de doble uso para gestionar botones InSim. El InSim lo envía para borrar uno o varios botones, o para borrar todos. LFS lo envía cuando el usuario solicita los botones (SHIFT+B o SHIFT+I) o cuando el usuario borra los botones del InSim.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_BFN |
| ReqI | byte | 0 |
| SubT | BFN | Subtipo (BFN_x) |
| UCID | byte | Conexión destino / origen (0 = local / 255 = todas) |
| ClickID | byte | ID del botón a borrar (o primero del rango si BFN_DEL_BTN) |
| ClickMax | byte | ID del último botón del rango (si > ClickID borra el rango) |
| Inst | byte | Usado internamente por InSim |

### Valores BFN_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | BFN_DEL_BTN | Instrucción: borrar un botón o rango de botones |
| 1 | BFN_CLEAR | Instrucción: borrar todos los botones de esta instancia |
| 2 | BFN_USER_CLEAR | Info: el usuario borró los botones de esta instancia |
| 3 | BFN_REQUEST | Info: SHIFT+B o SHIFT+I — el usuario solicita los botones |

**SHIFT+I**: borra botones del host si hay alguno, o envía BFN_REQUEST a instancias del host.
**SHIFT+B**: lo mismo pero para botones locales e instancias locales.

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_BFN
from lfs_insim.insim_enums import BFN

class MiInsim(InSimApp):
    def on_ISP_BFN(self, packet: ISP_BFN):
        if packet.SubT == BFN.REQUEST:
            # El usuario presionó SHIFT+B/I — mostrar botones
            self._mostrar_interfaz(packet.UCID)
        elif packet.SubT == BFN.USER_CLEAR:
            print(f"UCID {packet.UCID} borró los botones")

    def borrar_boton(self, click_id: int, ucid: int = 0):
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=ucid,
                          ClickID=click_id, ClickMax=click_id)

    def borrar_rango(self, desde: int, hasta: int, ucid: int = 0):
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=ucid,
                          ClickID=desde, ClickMax=hasta)

    def borrar_todos(self, ucid: int = 255):
        self.send_ISP_BFN(SubT=BFN.CLEAR, UCID=ucid,
                          ClickID=0, ClickMax=0)

    def _mostrar_interfaz(self, ucid: int):
        pass  # enviar IS_BTN packets aquí
```
