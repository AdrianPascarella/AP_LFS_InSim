# ISP_TTC — Target To Connection (multipropósito 8 bytes)

## Descripción
Paquete de instrucción de propósito general dirigido a una conexión específica. Actualmente usado para solicitar o controlar la selección del editor de layout de autocross de un guest o del jugador local.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_TTC |
| ReqI | byte | 0 o distinto de cero según el subtipo |
| SubT | byte | Subtipo del enumerado TTC_ |
| UCID | byte | ID único de la conexión destino (0 = local) |
| B1 | byte | Uso variable según SubT |
| B2 | byte | Uso variable según SubT |
| B3 | byte | Uso variable según SubT |

## SubT values (enumerado TTC_)

| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | TTC_NONE | No usado |
| 1 | TTC_SEL | Solicitar IS_AXM con la selección actual del editor de layout (ReqI != 0) |
| 2 | TTC_SEL_START | Empezar a enviar IS_AXM cada vez que cambie la selección |
| 3 | TTC_SEL_STOP | Detener el envío automático iniciado con TTC_SEL_START |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_AXM
from lfs_insim.insim_enums import TTC

class MiInsim(InSimApp):
    def solicitar_seleccion_guest(self, ucid: int):
        # Solicitar la selección actual del editor de un guest
        self.send_ISP_TTC(ReqI=1, SubT=TTC.SEL, UCID=ucid)

    def monitorear_seleccion(self, ucid: int):
        # Recibir IS_AXM automáticamente cuando cambie la selección
        self.send_ISP_TTC(ReqI=0, SubT=TTC.SEL_START, UCID=ucid)

    def detener_monitoreo(self, ucid: int):
        self.send_ISP_TTC(ReqI=0, SubT=TTC.SEL_STOP, UCID=ucid)

    def on_ISP_AXM(self, packet: ISP_AXM):
        # Respuesta a TTC_SEL o notificación de TTC_SEL_START
        from lfs_insim.insim_enums import PMO
        if packet.PMOAction == PMO.TTC_SEL:
            print(f"Selección recibida: {packet.NumO} objetos")
```
