# ISP_JRR — Join Request Reply

## Descripción
Paquete de respuesta que el InSim debe enviar a LFS en respuesta a una solicitud de unión (IS_NPL con NumP=0). También puede usarse para mover un coche existente a una posición específica del track. La respuesta debe enviarse en aproximadamente 1 segundo.

## Dirección
**InSim → LFS**

## Flags requeridos (si aplica)
Para recibir solicitudes de unión: `ISF.REQ_JOIN` en `set_isi_packet()`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 16 |
| Type | byte | ISP_JRR |
| ReqI | byte | 0 |
| PLID | byte | 0 al responder una solicitud / PLID del coche a mover |
| UCID | byte | UCID al responder solicitud / ignorado al mover |
| JRRAction | JRR | Acción (JRR_x) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| StartPos | ObjectInfo | Posición de inicio (0 = usar por defecto / Flags=0x80: usar posición) |

### Valores JRRAction (JRR_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | JRR_REJECT | Rechazar la solicitud de unión |
| 1 | JRR_SPAWN | Permitir la unión |
| 4 | JRR_RESET | Mover/resetear coche existente |
| 5 | JRR_RESET_NO_REPAIR | Mover sin reparar |

### Estructura ObjectInfo para StartPos
Para usar posición por defecto: llenar con ceros.
Para especificar posición: X, Y, Zbyte, Heading como en autocross; Flags=0x80; Index=0.

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_NPL
from lfs_insim.insim_enums import ISF, JRR
from lfs_insim.packets.structures import ObjectInfo

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.REQ_JOIN

    def on_ISP_NPL(self, packet: ISP_NPL):
        if packet.NumP != 0:
            return  # jugador normal, no solicitud de unión

        coche = packet.CName
        coches_permitidos = ['XFG', 'XRG', 'FXO']

        if coche in coches_permitidos:
            self.send_ISP_JRR(
                PLID=0, UCID=packet.UCID,
                JRRAction=JRR.SPAWN,
                StartPos=ObjectInfo()  # posición por defecto (ceros)
            )
        else:
            self.send_ISP_JRR(PLID=0, UCID=packet.UCID, JRRAction=JRR.REJECT,
                              StartPos=ObjectInfo())
            self.send_ISP_MTC(UCID=packet.UCID,
                              Msg=f"Solo se permiten: {', '.join(coches_permitidos)}")
```
