# ISP_RIP — Replay Information Packet

## Descripción
Paquete de doble uso para controlar replays. El InSim puede enviarlo para cargar un replay o posicionarse en un punto específico. LFS responde con otro IS_RIP indicando el resultado. Puede solicitarse el estado actual con `TINY_RIP`. Los tiempos se expresan en ms.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 80 |
| Type | byte | ISP_RIP |
| ReqI | byte | solicitud: distinto de cero / respuesta: mismo valor |
| Error | RIP | RIP.OK=0 / RIP.ALREADY=1 / otros=error |
| MPR | SMPR | SMPR.SPR=0 / SMPR.MPR=1 |
| Paused | OFFON | OFFON.OFF=0 / OFFON.ON=1 |
| Options | RIPOPT | Opciones (RIPOPT_x) |
| Sp3 | byte | Reservado |
| CTime | unsigned | (ms) solicitud: destino / respuesta: posición actual |
| TTime | unsigned | (ms) solicitud: 0 / respuesta: duración del replay |
| RName | char[64] | nombre del replay (cero para usar el actual) — último byte = 0 |

### Códigos de error (RIP_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | RIP_OK | OK: instrucción completada |
| 1 | RIP_ALREADY | OK: ya estaba en el destino |
| 2 | RIP_DEDICATED | No se puede reproducir en host dedicado |
| 3 | RIP_WRONG_MODE | Modo no adecuado para replay |
| 4 | RIP_NOT_REPLAY | RName vacío y no hay replay cargado |
| 5 | RIP_CORRUPTED | IS_RIP corrupto |
| 6 | RIP_NOT_FOUND | Archivo de replay no encontrado |
| 7 | RIP_UNLOADABLE | Obsoleto / futuro / corrupto |
| 8 | RIP_DEST_OOB | Destino más allá de la duración del replay |
| 9 | RIP_UNKNOWN | Error desconocido |
| 10 | RIP_USER | Búsqueda terminada por el usuario |
| 11 | RIP_OOS | No se puede alcanzar destino (SPR fuera de sync) |

### Flags RIPOPT_x
| Flag | Valor | Descripción |
|------|-------|-------------|
| RIPOPT_LOOP | 1 | El replay se repite en bucle |
| RIPOPT_SKINS | 2 | Descargar skins faltantes |
| RIPOPT_FULL_PHYS | 4 | Física completa en búsqueda MPR (más lento) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_RIP
from lfs_insim.insim_enums import TINY, RIP as RIP_ERR, SMPR, OFFON, RIPOPT

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.RIP)

    def on_ISP_RIP(self, packet: ISP_RIP):
        if packet.Error not in (RIP_ERR.OK, RIP_ERR.ALREADY):
            print(f"Error al cargar replay: {RIP_ERR(packet.Error).name}")
            return
        nombre = packet.RName
        if nombre:
            pos_s = packet.CTime / 1000
            dur_s = packet.TTime / 1000
            print(f"Replay '{nombre}': {pos_s:.1f}s / {dur_s:.1f}s")

    def cargar_replay(self, nombre: str, tiempo_ms: int = 0):
        self.send_ISP_RIP(
            ReqI=1, Error=RIP_ERR.OK, MPR=SMPR.SPR, Paused=OFFON.ON,
            Options=0, CTime=tiempo_ms, TTime=0,
            RName=nombre
        )
```
