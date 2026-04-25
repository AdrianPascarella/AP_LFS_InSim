# ISP_AXM — AutoX Multiple Objects

## Descripción
Paquete de doble uso para gestionar objetos de autocross (layout). LFS lo envía como notificación cuando se cargan o editan objetos (si `ISF_AXM_LOAD` o `ISF_AXM_EDIT` están activos). El InSim puede enviarlo para añadir, borrar o limpiar objetos. También se usa para gestionar la selección del editor de layout.

## Dirección
**Ambos**

## Flags requeridos (si aplica)
- `ISF.AXM_LOAD`: recibir AXM al cargar un layout
- `ISF.AXM_EDIT`: recibir AXM al editar objetos

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 + NumO * 8 |
| Type | byte | ISP_AXM |
| ReqI | byte | 0, o el ReqI de TINY_AXM o TTC_SEL |
| NumO | byte | Número de objetos en el paquete |
| UCID | byte | ID de la conexión que envió el paquete |
| PMOAction | byte | Acción (PMO_x) |
| PMOFlags | byte | Flags (PMO_FILE_END, PMO_MOVE_MODIFY, etc.) |
| Sp3 | byte | Reservado |
| Info | ObjectInfo[60] | Info de cada objeto (hasta AXM_MAX_OBJECTS=60) |

### Estructura ObjectInfo (8 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| X | short | Posición X |
| Y | short | Posición Y |
| Zbyte | byte | Altitud |
| Flags | byte | Flags del objeto |
| Index | byte | Tipo de objeto (AXO_x) |
| Heading | byte | Orientación |

### Valores PMOAction (PMO_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | PMO_LOADING_FILE | Solo el sistema de carga de layout |
| 1 | PMO_ADD_OBJECTS | Añadir objetos (InSim o editor) |
| 2 | PMO_DEL_OBJECTS | Borrar objetos |
| 3 | PMO_CLEAR_ALL | Limpiar todos los objetos (NumO debe ser 0) |
| 4 | PMO_TINY_AXM | Respuesta a TINY_AXM |
| 5 | PMO_TTC_SEL | Respuesta a TTC_SEL |
| 6 | PMO_SELECTION | Establecer selección del editor de layout |
| 7 | PMO_POSITION | Usuario presionó O sin selección |
| 8 | PMO_GET_Z | Solicitar/responder valores Z |

### Flags PMO_x
| Flag | Valor | Descripción |
|------|-------|-------------|
| PMO_FILE_END | 1 | Último paquete al cargar layout |
| PMO_MOVE_MODIFY | 2 | Movimiento/modificación en editor |
| PMO_SELECTION_REAL | 4 | Selección real (no clipboard) |
| PMO_AVOID_CHECK | 8 | Evitar verificación de posición en guest |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_AXM
from lfs_insim.insim_enums import ISF, TINY

PMO_ADD_OBJECTS = 1
PMO_CLEAR_ALL   = 3

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.AXM_LOAD | ISF.AXM_EDIT

    def on_connect(self):
        # Solicitar todos los objetos del layout actual
        self.send_ISP_TINY(ReqI=1, SubT=TINY.AXM)

    def on_ISP_AXM(self, packet: ISP_AXM):
        print(f"AXM: {packet.NumO} objetos, acción={packet.PMOAction}")
        for i in range(packet.NumO):
            obj = packet.Info[i]
            print(f"  Objeto {obj.Index} en ({obj.X}, {obj.Y})")

    def limpiar_layout(self):
        self.send_ISP_AXM(NumO=0, UCID=0, PMOAction=PMO_CLEAR_ALL,
                          PMOFlags=0, Info=[])
```
