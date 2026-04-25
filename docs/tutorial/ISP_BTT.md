# ISP_BTT — Button Type

## Descripción
LFS envía este paquete cuando un usuario termina de escribir en un botón de entrada de texto (botón con `TypeIn` distinto de cero). Se envía al presionar ENTER. No se envía IS_BTC en este caso.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 104 |
| Type | byte | ISP_BTT |
| ReqI | byte | ReqI del IS_BTN original |
| UCID | byte | Conexión que escribió (0 si es local) |
| ClickID | byte | ID del botón (como en IS_BTN) |
| Inst | byte | Usado internamente por InSim |
| TypeIn | byte | Valor TypeIn del IS_BTN original |
| Sp3 | byte | Reservado |
| Text | char[96] | Texto escrito (hasta TypeIn caracteres especificados en IS_BTN) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_BTT

ISB_CLICK = 8
ISB_DARK  = 32

BTN_INPUT_NOMBRE = 20
BTN_INPUT_SPEED  = 21

class MiInsim(InSimApp):
    def mostrar_input_nombre(self, ucid: int):
        # TypeIn=20 permite hasta 20 caracteres; bit 7 inicializa con texto del botón
        self.send_ISP_BTN(
            ReqI=5, UCID=ucid, ClickID=BTN_INPUT_NOMBRE,
            BStyle=ISB_DARK, TypeIn=20,
            L=10, T=60, W=60, H=8,
            Text="Escribe tu nombre"
        )

    def on_ISP_BTT(self, packet: ISP_BTT):
        texto = packet.Text
        if packet.ClickID == BTN_INPUT_NOMBRE:
            print(f"UCID {packet.UCID} escribió su nombre: '{texto}'")
            # Responder actualizando el botón con el nombre recibido
            self.send_ISP_BTN(
                ReqI=5, UCID=packet.UCID, ClickID=BTN_INPUT_NOMBRE,
                BStyle=ISB_DARK, TypeIn=0,
                L=10, T=60, W=60, H=8,
                Text=f"^3{texto}"
            )
```
