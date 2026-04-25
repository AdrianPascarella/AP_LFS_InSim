# ISP_HCP — HandiCaPs

## Descripción
Instrucción para añadir masa y restricciones de admisión a cada modelo de coche. La restricción aplica a todos los jugadores que usen ese modelo. Útil para crear hosts multi-clase. El array tiene 32 entradas, una por modelo (XF GTI = índice 0, XR GT = índice 1, etc.).

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 68 |
| Type | byte | ISP_HCP |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| Info | CarHCP[32] | Array de hándicaps por modelo de coche |

### Estructura CarHCP (2 bytes por entrada)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| H_Mass | byte | 0 a 200 — masa añadida en kg |
| H_TRes | byte | 0 a 50 — restricción de admisión |

El orden del array sigue el mismo orden que la bitmask CARS (ver ISP_PLC): índice 0 = XF GTI, índice 1 = XR GT, etc.

## Ejemplo de uso

```python
from lfs_insim import InSimApp

class MiInsim(InSimApp):
    def aplicar_handicaps(self):
        # Array de 32 pares (H_Mass, H_TRes)
        # Índices: 0=XF GTI, 1=XR GT, 2=XR GT TURBO, ...
        info = [(0, 0)] * 32

        # Añadir 50 kg al XF GTI (índice 0)
        info[0] = (50, 0)
        # Restricción de 20 al XR GT TURBO (índice 2)
        info[2] = (0, 20)

        # Aplanar la lista en bytes alternados
        hcp_flat = []
        for masa, res in info:
            hcp_flat.append(masa)
            hcp_flat.append(res)

        self.send_ISP_HCP(Info=hcp_flat)
```
