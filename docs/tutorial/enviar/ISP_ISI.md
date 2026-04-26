# ISP_ISI — InSim Init

## Descripción
Paquete de inicialización que el programa InSim envía a LFS para establecer la conexión. Es siempre el primer paquete que se envía. Si `ReqI` es distinto de cero, LFS responde con un `IS_VER`.

## Dirección
**InSim → LFS**

## Flags requeridos (si aplica)
No requiere flags previos. Este paquete *define* los flags ISF que activarán otras funciones (NLP, MCI, CON, OBH, HLV, AXM_LOAD, AXM_EDIT, REQ_JOIN, LOCAL).

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 44 |
| Type | byte | ISP_ISI |
| ReqI | byte | Si no es cero, LFS responde con IS_VER |
| Zero | byte | 0 |
| UDPPort | word | Puerto UDP para respuestas de LFS (0-65535) |
| Flags | ISF | Bits de opciones (ISF_x) |
| InSimVer | byte | Versión INSIM_VERSION del programa (actualmente 10) |
| Prefix | byte | Carácter prefijo para mensajes de host |
| Interval | word | Intervalo en ms entre NLP o MCI (0 = ninguno) |
| Admin | char[16] | Contraseña de admin (si está configurada en LFS) |
| IName | char[16] | Nombre corto del programa |

### Flags ISF disponibles
| Flag | Valor | Descripción |
|------|-------|-------------|
| ISF_LOCAL | 4 | Guest o jugador individual (usar para programas locales) |
| ISF_MSO_COLS | 8 | Conservar colores en texto MSO |
| ISF_NLP | 16 | Recibir paquetes NLP |
| ISF_MCI | 32 | Recibir paquetes MCI |
| ISF_CON | 64 | Recibir paquetes CON (colisiones coche-coche) |
| ISF_OBH | 128 | Recibir paquetes OBH (colisiones coche-objeto) |
| ISF_HLV | 256 | Recibir paquetes HLV (violaciones HLVC) |
| ISF_AXM_LOAD | 512 | Recibir AXM al cargar un layout |
| ISF_AXM_EDIT | 1024 | Recibir AXM al editar objetos |
| ISF_REQ_JOIN | 2048 | Procesar solicitudes de unión al servidor |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import ISF

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        # Activar flags según las necesidades del módulo
        self.isi.Flags |= ISF.MCI | ISF.CON | ISF.LOCAL
        self.isi.Prefix = ord('!')   # mensajes con ! van al InSim
        self.isi.Interval = 100      # MCI cada 100 ms

    def on_connect(self):
        # La conexión ya fue inicializada; aquí se solicita el estado inicial
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)
```
