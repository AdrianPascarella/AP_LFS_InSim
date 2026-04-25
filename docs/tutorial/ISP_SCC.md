# ISP_SCC — Set Car Camera

## Descripción
Instrucción simplificada para cambiar el coche visto y la cámara seleccionada en juego. Equivale a los estados que normalmente se cambian con TAB y V. Para control de cámara más avanzado (posición libre, angulo, FOV), usar `IS_CPP`.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_SCC |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| ViewPLID | byte | PLID del jugador a ver (255 = sin cambio) |
| InGameCam | byte | Cámara en juego VIEW_x (255 = sin cambio) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |

### Valores VIEW_x (cámaras)
| Valor | Nombre |
|-------|--------|
| 0 | VIEW_FOLLOW (arcade) |
| 1 | VIEW_HELI (helicóptero) |
| 2 | VIEW_CAM (TV) |
| 3 | VIEW_DRIVER (cockpit) |
| 4 | VIEW_CUSTOM (personalizada) |
| 255 | Sin cambio |

## Ejemplo de uso

```python
from lfs_insim import InSimApp

VIEW_DRIVER = 3
VIEW_HELI   = 1

class MiInsim(InSimApp):
    def ver_jugador_en_cockpit(self, plid: int):
        self.send_ISP_SCC(ViewPLID=plid, InGameCam=VIEW_DRIVER)

    def cambiar_solo_camara(self, camara: int):
        # ViewPLID=255 deja el jugador visto sin cambiar
        self.send_ISP_SCC(ViewPLID=255, InGameCam=camara)

    def ver_lider(self):
        # Se necesita conocer el PLID del líder previamente via MCI
        pass
```
