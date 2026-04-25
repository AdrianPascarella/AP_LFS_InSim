# ISP_BTN — Button

## Descripción
Instrucción para mostrar un botón en la pantalla del host o de un guest. Soporta hasta 240 botones por instancia InSim (IDs 0-239). Los botones pueden ser clickeables (devuelven IS_BTC) o con campo de texto (devuelven IS_BTT). Se recomienda usar `ISF_LOCAL` para programas locales y evitar conflictos con botones del host.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 12 + TEXT_SIZE (múltiplo de 4) |
| Type | byte | ISP_BTN |
| ReqI | byte | distinto de cero (devuelto en IS_BTC e IS_BTT) |
| UCID | byte | Conexión donde mostrar el botón (0 = local / 255 = todos) |
| ClickID | byte | ID del botón (0 a 239) |
| Inst | byte | Flags extra (INST_ALWAYS_ON=128 para visible en todas las pantallas) |
| BStyle | byte | Flags de estilo (ISB_x) |
| TypeIn | byte | Si distinto de 0: máx caracteres a escribir (0-95) / bit 7: inicializar con texto del botón |
| L | byte | Izquierda: 0-200 |
| T | byte | Arriba: 0-200 |
| W | byte | Ancho: 0-200 (0 = actualizar solo el texto) |
| H | byte | Alto: 0-200 (0 = actualizar solo el texto) |
| Text | char[variable] | Texto del botón (0 a 240 caracteres) |

### Flags BStyle (ISB_x)
| Flag | Valor | Descripción |
|------|-------|-------------|
| ISB_C1 | 1 | Color 1 de la paleta estándar |
| ISB_C2 | 2 | Color 2 de la paleta estándar |
| ISB_C4 | 4 | Color 4 de la paleta estándar |
| ISB_CLICK | 8 | Botón clickeable (envía IS_BTC) |
| ISB_LIGHT | 16 | Botón claro |
| ISB_DARK | 32 | Botón oscuro |
| ISB_LEFT | 64 | Texto alineado a la izquierda |
| ISB_RIGHT | 128 | Texto alineado a la derecha |

### Área recomendada para botones
- X: 0-110, Y: 30-170 (LFS mantiene esta zona libre en pantallas principales)

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_BTN, ISP_BFN
from lfs_insim.insim_enums import ISF

ISB_CLICK = 8
ISB_DARK  = 32
ISB_LEFT  = 64

class MiInsim(InSimApp):
    BTN_MENU   = 0
    BTN_SALIR  = 1

    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.LOCAL  # botones locales, no del host

    def on_ISP_BFN(self, packet):
        # Usuario presionó SHIFT+B para ver botones
        if packet.SubT == 3:  # BFN_REQUEST
            self._mostrar_menu(packet.UCID)

    def _mostrar_menu(self, ucid: int):
        # Título
        self.send_ISP_BTN(
            ReqI=1, UCID=ucid, ClickID=self.BTN_MENU,
            BStyle=ISB_DARK | ISB_LEFT, TypeIn=0,
            L=10, T=40, W=50, H=10, Text="^3Mi InSim"
        )
        # Botón clickeable
        self.send_ISP_BTN(
            ReqI=2, UCID=ucid, ClickID=self.BTN_SALIR,
            BStyle=ISB_CLICK | ISB_DARK, TypeIn=0,
            L=10, T=55, W=50, H=8, Text="Salir"
        )
```
