# ISP_REO — Reorder

## Descripción
Paquete de doble uso para el orden de salida de la carrera. LFS lo envía al inicio de cada carrera o calificación con el orden de salida. El InSim puede enviarlo para especificar el orden: (1) en la pantalla de configuración de carrera para reordenar la parrilla de inmediato, (2) en juego justo antes de un reinicio (debe enviarse al recibir `SMALL_VTA`). Puede solicitarse con `TINY_REO`.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 52 |
| Type | byte | ISP_REO |
| ReqI | byte | 0, o el ReqI de TINY_REO |
| NumP | byte | Número de jugadores en la carrera |
| PLID | byte[48] | Todos los PLIDs en el nuevo orden (REO_MAX_PLAYERS=48) |

## Ejemplo de uso

**Recibir y reordenar:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_REO, ISP_SMALL
from lfs_insim.insim_enums import TINY, SMALL

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self._orden_actual = []

    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.REO)

    def on_ISP_REO(self, packet: ISP_REO):
        self._orden_actual = list(packet.PLID[:packet.NumP])
        print(f"Orden de salida: {self._orden_actual}")

    def on_ISP_SMALL(self, packet: ISP_SMALL):
        if packet.SubT == SMALL.VTA:
            # Voto aprobado — enviar nuevo orden justo antes del reinicio
            orden_invertido = list(reversed(self._orden_actual))
            self.send_ISP_REO(NumP=len(orden_invertido), PLID=orden_invertido)
```
