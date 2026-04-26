# ISP_AIC — AI Control

## Descripción
Instrucción para controlar los inputs de un coche AI. Permite establecer valores de acelerador, freno, dirección, cambios de marcha, luces, etc. Cada entrada puede tener un tiempo de duración (`Time`) después del cual vuelve al valor por defecto. Para solicitar info del AI: enviar `SMALL_AII` con el PLID. Para recibir info regularmente: enviar `CS.REPEAT_AI_INFO` en un AIC.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 + 4 * (número de inputs) |
| Type | byte | ISP_AIC |
| ReqI | byte | Opcional — devuelto en respuestas inmediatas |
| PLID | byte | ID único del AI a controlar |
| Inputs | AIInputVal[20] | Array de entradas (hasta AIC_MAX_INPUTS=20) |

### Estructura AIInputVal (4 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Input | CS | Selección de entrada (CS enum o valor especial) |
| Time | byte | Duración en centésimas de segundo (0 = hasta siguiente paquete) |
| Value | word | Valor a establecer (ver CSVAL sub-enums abajo) |

### Valores de Input (enum CS)
| Valor | Nombre | Tipo Value | Descripción |
|-------|--------|------------|-------------|
| 0 | CS.STEER | MIN_MID_MAX / STEER | Dirección: MIN=1 / MID=32768 / MAX=65535 |
| 1 | CS.THROTTLE | 0–65535 | Acelerador |
| 2 | CS.BRAKE | 0–65535 | Freno |
| 3 | CS.CHUP | hold | Palanca de subida de marcha |
| 4 | CS.CHDN | hold | Palanca de bajada de marcha |
| 5 | CS.IGNITION | TOGGLE | Encendido: T=toggle / OFF=2 / ON=3 |
| 6 | CS.EXTRALIGHT | TOGGLE | Luz extra: T=toggle / OFF=2 / ON=3 |
| 7 | CS.HEADLIGHTS | HEADLIGHTS | OFF=1 / SIDE=2 / LOW=3 / HIGH=4 |
| 8 | CS.SIREN | SIREN | OFF=0 / FAST=1 / SLOW=2 |
| 9 | CS.HORN | 0–5 | Bocina: 1–5 intensidades |
| 10 | CS.FLASH | 1 | Flash: 1=on |
| 11 | CS.CLUTCH | 0–65535 | Embrague |
| 12 | CS.HANDBRAKE | 0–65535 | Freno de mano |
| 13 | CS.INDICATORS | INDICATORS | OFF=1 / LEFT=2 / RIGHT=3 / HAZARD=4 |
| 14 | CS.GEAR | GEAR | REVERSE=0 / NEUTRAL=1 / FIRST=2… EIGHTH=9 |
| 15 | CS.LOOK | LOOK | CENTRE=0 / LEFT=4 / LEFT_MAX=5 / RIGHT=6 / RIGHT_MAX=7 |
| 16 | CS.PITSPEED | TOGGLE | Limitador pit: T=toggle / OFF=2 / ON=3 |
| 17 | CS.TCDISABLE | TOGGLE | Desactivar TC: T=toggle / OFF=2 / ON=3 |
| 18 | CS.FOGREAR | TOGGLE | Antiniebla trasero: T=toggle / OFF=2 / ON=3 |
| 19 | CS.FOGFRONT | TOGGLE | Antiniebla delantero: T=toggle / OFF=2 / ON=3 |

### Valores especiales de Input
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 240 | CS.SEND_AI_INFO | Enviar un IS_AII inmediato |
| 241 | CS.REPEAT_AI_INFO | Iniciar/parar envío regular de IS_AII (Time=intervalo en cs, 0=parar) |
| 253 | CS.SET_HELP_FLAGS | Establecer flags de ayuda (Value = PIF.AUTOGEARS / PIF.HELP_B / PIF.AUTOCLUTCH) |
| 254 | CS.RESET_INPUTS | Resetear todos los inputs a defaults |
| 255 | CS.STOP_CONTROL | El AI detiene el coche |

Los sub-enums de Value están agrupados en `CSVAL`: `CSVAL.HEADLIGHTS`, `CSVAL.SIREN`, `CSVAL.LOOK`, `CSVAL.INDICATORS`, `CSVAL.TOGGLE`, `CSVAL.GEAR`, `CSVAL.STEER`, `CSVAL.MIN_MID_MAX`.

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import CS, CSVAL
from lfs_insim.packets.structures import AIInputVal

class MiInsim(InSimApp):
    def acelerar_ai(self, plid: int, steer: float, throttle: float):
        # steer: -1.0 (izquierda) a 1.0 (derecha)
        steer_val = int((steer + 1) / 2 * 65534) + 1
        throttle_val = int(throttle * 65535)
        self.send_ISP_AIC(PLID=plid, Inputs=[
            AIInputVal(Input=CS.STEER,    Time=0, Value=steer_val),
            AIInputVal(Input=CS.THROTTLE, Time=0, Value=throttle_val),
            AIInputVal(Input=CS.BRAKE,    Time=0, Value=0),
        ])

    def cambiar_marcha_arriba(self, plid: int):
        self.send_ISP_AIC(PLID=plid, Inputs=[
            AIInputVal(Input=CS.CHUP, Time=10, Value=1),  # hold 0.1s
        ])

    def poner_luces_largas(self, plid: int):
        self.send_ISP_AIC(PLID=plid, Inputs=[
            AIInputVal(Input=CS.HEADLIGHTS, Time=0, Value=CSVAL.HEADLIGHTS.HIGH),
        ])

    def activar_intermitente_izquierdo(self, plid: int):
        self.send_ISP_AIC(PLID=plid, Inputs=[
            AIInputVal(Input=CS.INDICATORS, Time=0, Value=CSVAL.INDICATORS.LEFT),
        ])

    def detener_ai(self, plid: int):
        self.send_ISP_AIC(PLID=plid, Inputs=[
            AIInputVal(Input=CS.STOP_CONTROL, Time=0, Value=0),
        ])
```
