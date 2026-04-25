# ISP_SFP — State Flags Pack

## Descripción
Permite al InSim activar o desactivar ciertos flags de estado de LFS. Solo un subconjunto de los flags ISS puede controlarse con este paquete; el resto se deben cambiar mediante comandos de texto.

## Dirección
**InSim → LFS**

## Flags controlables
Solo los siguientes flags ISS pueden establecerse con IS_SFP:
- `ISS_SHIFTU_NO_OPT` (64) — Ocultar botones de free view
- `ISS_SHOW_2D` (128) — Mostrar display 2D
- `ISS_MPSPEEDUP` (1024) — Opción de aceleración multijugador
- `ISS_SOUND_MUTE` (4096) — Silenciar sonido

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_SFP |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| Flag | word | El flag de estado a cambiar (ISS_x) |
| OffOn | byte | 0 = desactivar / 1 = activar |
| Sp3 | byte | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp

# Valores de flags ISS (hardcodeados ya que son constantes del protocolo)
ISS_SOUND_MUTE = 4096
ISS_SHOW_2D    = 128

class MiInsim(InSimApp):
    def silenciar_sonido(self, activar: bool):
        self.send_ISP_SFP(Flag=ISS_SOUND_MUTE, OffOn=1 if activar else 0)

    def mostrar_display_2d(self, activar: bool):
        self.send_ISP_SFP(Flag=ISS_SHOW_2D, OffOn=1 if activar else 0)
```
