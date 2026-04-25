# ISP_RES — Result Confirmed

## Descripción
LFS envía este paquete con el resultado final confirmado de un jugador (al terminar carrera o al finalizar una sesión de calificación). Contiene nombre de usuario, nickname, tiempo total, mejor vuelta y posición. Puede solicitarse con `TINY_RES`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 84 |
| Type | byte | ISP_RES |
| ReqI | byte | 0, o el ReqI de TINY_RES |
| PLID | byte | ID único del jugador (0 si abandonó) |
| UName | char[24] | Nombre de usuario de LFS |
| PName | char[24] | Nickname |
| Plate | char[8] | Matrícula (sin terminador nulo) |
| CName | char[4] | Prefijo de skin |
| TTime | unsigned | (ms) tiempo de carrera / tiempo de sesión de calificación |
| BTime | unsigned | (ms) mejor vuelta |
| SpA | byte | Reservado |
| NumStops | byte | Número de paradas en pits |
| Confirm | CONF | Flags de confirmación (CONF_x) |
| SpB | byte | Reservado |
| LapsDone | word | Laps completados |
| Flags | PIF | Flags del jugador (PIF_x) |
| ResultNum | byte | Posición en resultados (0=1ro / 255=no en tabla) |
| NumRes | byte | Total de resultados |
| PSeconds | word | Tiempo de penalización en segundos (ya incluido en TTime) |

## Ejemplo de uso

**Solicitar y recibir resultados:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_RES
from lfs_insim.insim_enums import TINY

def ms_a_tiempo(ms: int) -> str:
    mins = ms // 60000
    secs = (ms % 60000) / 1000
    return f"{mins}:{secs:06.3f}"

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.RES)

    def on_ISP_RES(self, packet: ISP_RES):
        if packet.PLID == 0:
            return  # jugador abandonó antes del resultado
        nombre = packet.PName
        posicion = packet.ResultNum + 1  # 0-indexed -> 1-indexed
        print(f"P{posicion} {nombre}: {ms_a_tiempo(packet.TTime)} "
              f"(mejor vuelta: {ms_a_tiempo(packet.BTime)})")
```
