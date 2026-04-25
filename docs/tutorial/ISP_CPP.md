# ISP_CPP — Cam Pos Pack

## Descripción
Paquete de posición de cámara completo que funciona en ambas direcciones. LFS lo envía como respuesta a `TINY_SCP` describiendo la posición actual de la cámara. El InSim puede enviarlo para posicionar la cámara en modo in-car o free view. Soporta transiciones suaves con el campo `Time`.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 32 |
| Type | byte | ISP_CPP |
| ReqI | byte | instrucción: 0 / respuesta: ReqI de TINY_SCP |
| Zero | byte | 0 |
| Pos | Vec (3 ints) | Vector de posición (65536 = 1 metro) |
| H | word | Heading — 0 apunta al eje Y del mundo |
| P | word | Pitch |
| R | word | Roll |
| ViewPLID | byte | PLID del jugador visto (0 = ninguno; 255 = sin cambio) |
| InGameCam | byte | Cámara en juego VIEW_x (255 = sin cambio) |
| FOV | float | Campo de visión en grados |
| Time | word | Tiempo en ms para llegar allí (0 = instantáneo) |
| Flags | word | Flags ISS (ISS_SHIFTU, ISS_SHIFTU_FOLLOW, ISS_VIEW_OVERRIDE) |

### Flags ISS aplicables
| Flag | Valor | Descripción |
|------|-------|-------------|
| ISS_SHIFTU | 8 | Modo free view |
| ISS_SHIFTU_FOLLOW | 32 | Vista FOLLOW (posición relativa al coche) |
| ISS_VIEW_OVERRIDE | 8192 | Override de Heading/Pitch/Roll/FOV en vista in-car |

## Ejemplo de uso

**Solicitar posición actual:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CPP
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self._cam_guardada = None

    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.SCP)

    def on_ISP_CPP(self, packet: ISP_CPP):
        if packet.ReqI:  # es respuesta a TINY_SCP
            self._cam_guardada = packet
            print(f"Cámara en Pos=({packet.Pos}), FOV={packet.FOV:.1f}°")

    def restaurar_camara(self):
        if self._cam_guardada:
            # Enviar el mismo paquete de vuelta para restaurar posición
            self.send(self._cam_guardada)

    def mover_camara_suave(self, x: int, y: int, z: int, tiempo_ms: int):
        ISS_SHIFTU = 8
        self.send_ISP_CPP(
            Pos=[x, y, z], H=0, P=0, R=0,
            ViewPLID=255, InGameCam=255,
            FOV=60.0, Time=tiempo_ms,
            Flags=ISS_SHIFTU
        )
```
