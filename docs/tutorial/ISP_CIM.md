# ISP_CIM — Connection Interface Mode

## Descripción
LFS envía este paquete cuando cambia el modo de interfaz de una conexión (pantalla en la que se encuentra el jugador). Permite saber si el jugador está en el garage, selección de coche, modo free view, etc.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_CIM |
| ReqI | byte | 0 |
| UCID | byte | ID de conexión (0 = local) |
| Mode | byte | Identificador de modo (CIM_x) |
| SubMode | byte | Submode según el modo (ver abajo) |
| SelType | byte | Tipo de objeto seleccionado (AXO_x o constante especial) |
| Sp3 | byte | Reservado |

### Valores Mode (CIM_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | CIM_NORMAL | En juego normal |
| 1 | CIM_OPTIONS | En opciones |
| 2 | CIM_HOST_OPTIONS | En opciones del host |
| 3 | CIM_GARAGE | En el garage |
| 4 | CIM_CAR_SELECT | Selección de coche |
| 5 | CIM_TRACK_SELECT | Selección de track |
| 6 | CIM_SHIFTU | Modo free view |

### SubMode para CIM_NORMAL
`NRM_NORMAL`(0), `NRM_WHEEL_TEMPS`(1/F9), `NRM_WHEEL_DAMAGE`(2/F10), `NRM_LIVE_SETTINGS`(3/F11), `NRM_PIT_INSTRUCTIONS`(4/F12)

### SubMode para CIM_GARAGE
`GRG_INFO`(0), `GRG_COLOURS`(1), `GRG_BRAKE_TC`(2), `GRG_SUSP`(3), `GRG_STEER`(4), `GRG_DRIVE`(5), `GRG_TYRES`(6), `GRG_AERO`(7), `GRG_PASS`(8)

### SubMode para CIM_SHIFTU
`FVM_PLAIN`(0), `FVM_BUTTONS`(1), `FVM_EDIT`(2)

### SelType especiales
`MARSH_IS_CP`=252 (checkpoint InSim), `MARSH_IS_AREA`=253 (círculo InSim), `MARSH_MARSHAL`=254 (área restringida), `MARSH_ROUTE`=255 (route checker)

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CIM

CIM_NORMAL = 0
CIM_GARAGE = 3
CIM_CAR_SELECT = 4

class MiInsim(InSimApp):
    def on_ISP_CIM(self, packet: ISP_CIM):
        if packet.Mode == CIM_CAR_SELECT:
            print(f"UCID {packet.UCID} está seleccionando coche")
        elif packet.Mode == CIM_GARAGE:
            print(f"UCID {packet.UCID} está en el garage (sub: {packet.SubMode})")
        elif packet.Mode == CIM_NORMAL:
            print(f"UCID {packet.UCID} está en juego")
```
