# ISP_OCO — Object Control

## Descripción
Instrucción para controlar objetos del layout desde InSim. Actualmente se usa principalmente para controlar luces de semáforos de salida (start lights), permitiendo crear secuencias de salida personalizadas.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_OCO |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| OCOAction | OCO | Acción (OCO_x) |
| Index | AXO_INDEX | Índice del objeto de luces (AXO_x o OCO_INDEX_MAIN=240) |
| Identifier | byte | ID de luces temporales (0-63 o 255=todas) |
| Data | byte | Datos según la acción (bitmask de bombillas) |

### Valores OCOAction (OCO_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 4 | OCO_LIGHTS_RESET | Ceder control de todas las luces |
| 5 | OCO_LIGHTS_SET | Usar byte Data para configurar bombillas |
| 6 | OCO_LIGHTS_UNSET | Ceder control de luces específicas |

### Index values
- `AXO_START_LIGHTS1` = 149 (layout)
- `AXO_START_LIGHTS2` = 150 (layout)
- `AXO_START_LIGHTS3` = 151 (layout)
- `OCO_INDEX_MAIN` = 240 (luces de salida principales)

### Byte Data (bombillas)
**Para OCO_INDEX_MAIN:** bit 0=red1, bit 1=red2, bit 2=red3, bit 3=green

**Para AXO_START_LIGHTS:** bit 0=red, bit 1=amber, bit 3=green

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import OCO
import time
import threading

OCO_INDEX_MAIN = 240  # luces principales de salida (no es un AXO_INDEX estándar)

class MiInsim(InSimApp):
    def secuencia_salida(self):
        # Simulación de semáforo de F1
        def _run():
            # Rojo 1
            self.send_ISP_OCO(OCOAction=OCO.LIGHTS_SET,
                              Index=OCO_INDEX_MAIN, Identifier=255, Data=0b0001)
            time.sleep(0.5)
            # Rojo 2
            self.send_ISP_OCO(OCOAction=OCO.LIGHTS_SET,
                              Index=OCO_INDEX_MAIN, Identifier=255, Data=0b0011)
            time.sleep(0.5)
            # Rojo 3
            self.send_ISP_OCO(OCOAction=OCO.LIGHTS_SET,
                              Index=OCO_INDEX_MAIN, Identifier=255, Data=0b0111)
            time.sleep(2.0)
            # Verde — ¡go!
            self.send_ISP_OCO(OCOAction=OCO.LIGHTS_SET,
                              Index=OCO_INDEX_MAIN, Identifier=255, Data=0b1000)
            time.sleep(1.0)
            # Ceder control
            self.send_ISP_OCO(OCOAction=OCO.LIGHTS_RESET,
                              Index=OCO_INDEX_MAIN, Identifier=255, Data=0)
        threading.Thread(target=_run, daemon=True).start()
```
