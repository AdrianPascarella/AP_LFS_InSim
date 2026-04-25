# ISP_SMALL — Paquete multipropósito de 8 bytes

## Descripción
Paquete de propósito general usado en ambas direcciones cuando se necesita un subtipo `SubT` más un valor entero `UVal`. Se usa para instrucciones simples y reportes con un valor numérico.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_SMALL |
| ReqI | byte | 0 salvo que sea solicitud/respuesta |
| SubT | byte | Subtipo del enumerado SMALL_ |
| UVal | unsigned | Valor asociado al subtipo |

## SubT values (enumerado SMALL_)

| Valor | Nombre | Dirección | Descripción |
|-------|--------|-----------|-------------|
| 0 | SMALL_NONE | — | No usado |
| 1 | SMALL_SSP | InSim→LFS | Iniciar envío de posiciones OutSim (UVal = intervalo ms; 0 = detener) |
| 2 | SMALL_SSG | InSim→LFS | Iniciar envío de gauges OutGauge (UVal = intervalo ms; 0 = detener) |
| 3 | SMALL_VTA | LFS→InSim | Acción de voto ejecutada (UVal = VOTE_x) |
| 4 | SMALL_TMS | InSim→LFS | Detener/reanudar tiempo (actualmente no disponible) |
| 5 | SMALL_STP | InSim→LFS | Avanzar tiempo un paso en ms (actualmente no disponible) |
| 6 | SMALL_RTP | LFS→InSim | Tiempo de carrera en ms (respuesta a TINY_GTM) |
| 7 | SMALL_NLI | InSim→LFS | Cambiar intervalo de NLP/MCI (UVal = ms; 0 = detener) |
| 8 | SMALL_ALC | Ambos | Coches permitidos (set/get; respuesta a TINY_ALC; UVal = bitmask CARS) |
| 9 | SMALL_LCS | InSim→LFS | Controlar switches del coche local (flash, horn, siren; UVal = bitmask LCS_x) |
| 10 | SMALL_LCL | Ambos | Controlar luces del coche local (respuesta a TINY_LCL; UVal = bitmask LCL_x) |
| 11 | SMALL_AII | InSim→LFS | Solicitar info del AI local (UVal = PLID del AI) |

### Bitmask LCS_x (SMALL_LCS - Car Switches)
| Flag | Bit | Descripción |
|------|-----|-------------|
| LCS_SET_SIGNALS | 0 (1) | Activar control de señales (obsoleto, usar LCL) |
| LCS_SET_FLASH | 1 (2) | Activar control de flash |
| LCS_SET_HEADLIGHTS | 2 (4) | Activar control de faros (obsoleto, usar LCL) |
| LCS_SET_HORN | 3 (8) | Activar control de bocina |
| LCS_SET_SIREN | 4 (0x10) | Activar control de sirena |

### Bitmask LCL_x (SMALL_LCL - Car Lights)
| Flag | Bit | Descripción |
|------|-----|-------------|
| LCL_SET_SIGNALS | 0 (1) | Controlar intermitentes |
| LCL_SET_LIGHTS | 2 (4) | Controlar faros |
| LCL_SET_FOG_REAR | 4 (0x10) | Controlar antiniebla trasero |
| LCL_SET_FOG_FRONT | 5 (0x20) | Controlar antiniebla delantero |
| LCL_SET_EXTRA | 6 (0x40) | Controlar luz extra |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_SMALL
from lfs_insim.insim_enums import SMALL, TINY

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar coches permitidos
        self.send_ISP_TINY(ReqI=1, SubT=TINY.ALC)

    def on_ISP_SMALL(self, packet: ISP_SMALL):
        if packet.SubT == SMALL.VTA:
            print(f"Acción de voto: {packet.UVal}")
        elif packet.SubT == SMALL.RTP:
            print(f"Tiempo de carrera: {packet.UVal} ms")
        elif packet.SubT == SMALL.ALC:
            print(f"Coches permitidos (bitmask): {hex(packet.UVal)}")

    def activar_sirena(self):
        # Activar sirena del coche local
        # Bit 4 (LCS_SET_SIREN=0x10) + bits 20-21 para tipo siren=1 (fast)
        switches = 0x10 | (1 << 20)
        self.send_ISP_SMALL(SubT=SMALL.LCS, UVal=switches)

    def cambiar_intervalo_mci(self, ms: int):
        # Cambiar intervalo de NLP/MCI en tiempo real
        self.send_ISP_SMALL(SubT=SMALL.NLI, UVal=ms)
```
