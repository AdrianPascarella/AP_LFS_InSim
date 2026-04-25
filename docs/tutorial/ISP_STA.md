# ISP_STA — State Info

## Descripción
LFS envía este paquete automáticamente cada vez que cambia el estado del juego. También puede solicitarse en cualquier momento con `TINY_SST`. Contiene información sobre el estado general de LFS: carrera, réplica, cámara, track, etc.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 28 |
| Type | byte | ISP_STA |
| ReqI | byte | ReqI si es respuesta a una solicitud |
| Zero | byte | 0 |
| ReplaySpeed | float | Velocidad del replay (1.0 = normal) |
| Flags | word | Flags de estado ISS_x |
| InGameCam | byte | Tipo de cámara seleccionada (VIEW_x) |
| ViewPLID | byte | PLID del jugador visto (0 = ninguno) |
| NumP | byte | Número de jugadores en carrera |
| NumConns | byte | Número de conexiones incluyendo host |
| NumFinished | byte | Número que terminó o calificó |
| RaceInProg | byte | 0 = sin carrera / 1 = carrera / 2 = calificación |
| QualMins | byte | Minutos de calificación |
| RaceLaps | byte | Laps de carrera (ver RaceLaps encoding) |
| Sp2 | byte | Reservado |
| ServerStatus | byte | 0 = desconocido / 1 = OK / >1 = error |
| Track | char[6] | Nombre corto del track, ej: "FE2R" |
| Weather | WEATHER | Condición climática (CLEAR/CLOUDY/RAIN) |
| Wind | WIND | Viento: OFF / WEAK / STRONG |

### Flags ISS (estado del juego)
| Flag | Valor | Descripción |
|------|-------|-------------|
| ISS_GAME | 1 | En partida (o MPR) |
| ISS_REPLAY | 2 | En SPR (replay single player) |
| ISS_PAUSED | 4 | En pausa |
| ISS_SHIFTU | 8 | Modo free view |
| ISS_DIALOG | 16 | En un diálogo |
| ISS_SHIFTU_FOLLOW | 32 | Vista FOLLOW en free view |
| ISS_SHIFTU_NO_OPT | 64 | Botones de free view ocultos |
| ISS_SHOW_2D | 128 | Mostrando pantalla 2D |
| ISS_FRONT_END | 256 | En pantalla de entrada |
| ISS_MULTI | 512 | Modo multijugador |
| ISS_MPSPEEDUP | 1024 | Opción de aceleración multijugador |
| ISS_WINDOWED | 2048 | LFS en ventana |
| ISS_SOUND_MUTE | 4096 | Sonido silenciado |
| ISS_VIEW_OVERRIDE | 8192 | Override de vista del usuario |
| ISS_VISIBLE | 16384 | Botones InSim visibles |
| ISS_TEXT_ENTRY | 32768 | En diálogo de texto |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_STA
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar estado actual al conectar
        self.send_ISP_TINY(ReqI=1, SubT=TINY.SST)

    def on_ISP_STA(self, packet: ISP_STA):
        en_carrera = bool(packet.Flags & 1)   # ISS_GAME
        en_pausa = bool(packet.Flags & 4)      # ISS_PAUSED
        print(f"Track: {packet.Track}  Jugadores: {packet.NumP}")
        print(f"En carrera: {en_carrera}  Pausado: {en_pausa}")
        if packet.RaceInProg == 2:
            print(f"Calificación: {packet.QualMins} minutos")
```
