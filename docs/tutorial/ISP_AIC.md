# ISP_AIC — AI Control

## Descripción
Instrucción para controlar los inputs de un coche AI. Permite establecer valores de acelerador, freno, dirección, cambios de marcha, luces, etc. Cada entrada puede tener un tiempo de duración (`Time`) después del cual vuelve al valor por defecto. Para solicitar info del AI: enviar `SMALL_AII` con el PLID. Para recibir info regularmente: enviar `CS_REPEAT_AI_INFO` en un AIC.

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
| Input | byte | Selección de entrada (CS_x o especial) |
| Time | byte | Duración en centésimas de segundo (0 = hasta siguiente paquete) |
| Value | word | Valor a establecer |

### Valores de Input (CS_x)
| Valor | Nombre | Rango | Descripción |
|-------|--------|-------|-------------|
| 0 | CS_MSX | 1-65535 | Dirección: 1=izq máx / 32768=centro / 65535=der máx |
| 1 | CS_THROTTLE | 0-65535 | Acelerador |
| 2 | CS_BRAKE | 0-65535 | Freno |
| 3 | CS_CHUP | hold | Palanca de subida de marcha |
| 4 | CS_CHDN | hold | Palanca de bajada de marcha |
| 5 | CS_IGNITION | toggle | Encendido |
| 6 | CS_EXTRALIGHT | toggle | Luz extra |
| 7 | CS_HEADLIGHTS | 1-4 | Luces: 1=off/2=posición/3=cruce/4=largo |
| 8 | CS_SIREN | hold | Sirena: 1=rápida/2=lenta |
| 9 | CS_HORN | hold | Bocina: 1-5 |
| 10 | CS_FLASH | hold | Flash: 1=on |
| 11 | CS_CLUTCH | 0-65535 | Embrague |
| 12 | CS_HANDBRAKE | 0-65535 | Freno de mano |
| 13 | CS_INDICATORS | 1-4 | Intermitentes: 1=cancelar/2=izq/3=der/4=hazard |
| 14 | CS_GEAR | 0-255 | Marcha directa (255=control secuencial) |
| 15 | CS_LOOK | 0-7 | Mirar: 0=ninguno/4=izq/5=izq+/6=der/7=der+ |
| 16 | CS_PITSPEED | toggle | Limitador de velocidad pit |
| 17 | CS_TCDISABLE | toggle | Desactivar TC |
| 18 | CS_FOGREAR | toggle | Antiniebla trasero |
| 19 | CS_FOGFRONT | toggle | Antiniebla delantero |

### Valores especiales de Input
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 240 | CS_SEND_AI_INFO | Enviar un IS_AII inmediato |
| 241 | CS_REPEAT_AI_INFO | Iniciar/parar envío regular de IS_AII (Time=intervalo en cs, 0=parar) |
| 253 | CS_SET_HELP_FLAGS | Establecer flags de ayuda (PIF_AUTOGEARS/PIF_HELP_B/PIF_AUTOCLUTCH) |
| 254 | CS_RESET_INPUTS | Resetear todos los inputs a defaults |
| 255 | CS_STOP_CONTROL | El AI detiene el coche |

Valores toggle: 1=toggle / 2=apagar / 3=encender

## Ejemplo de uso

```python
from lfs_insim import InSimApp

CS_MSX      = 0
CS_THROTTLE = 1
CS_BRAKE    = 2
CS_CHUP     = 3
CS_STOP_CONTROL = 255

class MiInsim(InSimApp):
    def acelerar_ai(self, plid: int, steer: float, throttle: float):
        # steer: -1.0 (izquierda) a 1.0 (derecha) -> 1 a 65535
        steer_val = int((steer + 1) / 2 * 65534) + 1
        throttle_val = int(throttle * 65535)
        self.send_ISP_AIC(PLID=plid, Inputs=[
            {'Input': CS_MSX,      'Time': 0, 'Value': steer_val},
            {'Input': CS_THROTTLE, 'Time': 0, 'Value': throttle_val},
            {'Input': CS_BRAKE,    'Time': 0, 'Value': 0},
        ])

    def cambiar_marcha_arriba(self, plid: int):
        # hold por 0.1s (10 centésimas)
        self.send_ISP_AIC(PLID=plid, Inputs=[
            {'Input': CS_CHUP, 'Time': 10, 'Value': 1},
        ])

    def detener_ai(self, plid: int):
        self.send_ISP_AIC(PLID=plid, Inputs=[
            {'Input': CS_STOP_CONTROL, 'Time': 0, 'Value': 0},
        ])
```
