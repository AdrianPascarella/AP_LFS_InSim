# ISP_TINY — Paquete multipropósito de 4 bytes

## Descripción
Paquete de propósito general usado en ambas direcciones cuando no se necesita más dato que el subtipo `SubT`. Se usa para solicitudes de información, notificaciones de eventos, keep-alive y comandos simples.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 |
| Type | byte | ISP_TINY |
| ReqI | byte | 0 salvo que sea una solicitud de info o respuesta a una |
| SubT | byte | Subtipo del enumerado TINY_ |

## SubT values (enumerado TINY_)

| Valor | Nombre | Dirección | Descripción |
|-------|--------|-----------|-------------|
| 0 | TINY_NONE | Ambos | Keep-alive (LFS envía cada 30s; responder con otro TINY_NONE) |
| 1 | TINY_VER | InSim→LFS | Solicitar IS_VER |
| 2 | TINY_CLOSE | InSim→LFS | Cerrar conexión InSim |
| 3 | TINY_PING | InSim→LFS | Solicitar respuesta de ping |
| 4 | TINY_REPLY | LFS→InSim | Respuesta a ping |
| 5 | TINY_VTC | Ambos | Cancelar voto en curso |
| 6 | TINY_SCP | InSim→LFS | Solicitar posición de cámara (IS_CPP) |
| 7 | TINY_SST | InSim→LFS | Solicitar estado del juego (IS_STA) |
| 8 | TINY_GTM | InSim→LFS | Obtener tiempo de carrera en ms (responde SMALL_RTP) |
| 9 | TINY_MPE | LFS→InSim | Fin de partida multijugador |
| 10 | TINY_ISM | InSim→LFS | Solicitar info multijugador (IS_ISM) |
| 11 | TINY_REN | LFS→InSim | Fin de carrera (vuelve a pantalla de setup) |
| 12 | TINY_CLR | LFS→InSim | Todos los jugadores eliminados de la carrera |
| 13 | TINY_NCN | InSim→LFS | Solicitar IS_NCN de todas las conexiones |
| 14 | TINY_NPL | InSim→LFS | Solicitar IS_NPL de todos los jugadores |
| 15 | TINY_RES | InSim→LFS | Solicitar todos los resultados |
| 16 | TINY_NLP | InSim→LFS | Solicitar un IS_NLP inmediato |
| 17 | TINY_MCI | InSim→LFS | Solicitar un IS_MCI inmediato |
| 18 | TINY_REO | InSim→LFS | Solicitar IS_REO (orden de salida) |
| 19 | TINY_RST | InSim→LFS | Solicitar IS_RST (inicio de carrera) |
| 20 | TINY_AXI | InSim→LFS | Solicitar IS_AXI (info de autocross) |
| 21 | TINY_AXC | LFS→InSim | Layout de autocross borrado |
| 22 | TINY_RIP | InSim→LFS | Solicitar IS_RIP (info de replay) |
| 23 | TINY_NCI | InSim→LFS | Solicitar NCI de todos los guests (solo host) |
| 24 | TINY_ALC | InSim→LFS | Solicitar SMALL_ALC (coches permitidos) |
| 25 | TINY_AXM | InSim→LFS | Solicitar IS_AXM de todo el layout |
| 26 | TINY_SLC | InSim→LFS | Solicitar IS_SLC de todas las conexiones |
| 27 | TINY_MAL | InSim→LFS | Solicitar IS_MAL (mods permitidos) |
| 28 | TINY_PLH | InSim→LFS | Solicitar IS_PLH (hándicaps de jugadores) |
| 29 | TINY_IPB | InSim→LFS | Solicitar IS_IPB (lista de IPs baneadas) |
| 30 | TINY_LCL | InSim→LFS | Solicitar SMALL_LCL (luces del coche local) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_TINY
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar estado inicial: conexiones y jugadores activos
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)

    def on_ISP_TINY(self, packet: ISP_TINY):
        if packet.SubT == TINY.NONE:
            # Responder al keep-alive de LFS
            self.send_ISP_TINY(ReqI=0, SubT=TINY.NONE)
        elif packet.SubT == TINY.REN:
            print("La carrera terminó")
        elif packet.SubT == TINY.CLR:
            print("Todos los jugadores eliminados de la carrera")
```
