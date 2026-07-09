# AP LFS InSim

Framework modular en Python para desarrollar plugins de **LFS InSim v10** (Live for Speed). Permite crear módulos independientes con gestión automática de dependencias, ciclo de vida estandarizado y acceso al protocolo binario completo de LFS.

> Python 3.9+ · Sin dependencias externas · Pure stdlib

---

## Requisitos

- **Live for Speed** 0.7F o superior (probado en 0.8C) con InSim v10 activado
- **Python 3.9+**

---

## Instalación

```bash
git clone https://github.com/AdrianPascarella/AP_LFS_InSim
cd AP_LFS_InSim
pip install -e ".[dev]"
```

El extra `[dev]` añade lo necesario para tests y tooling. El core no tiene dependencias externas.

---

## Documentación

Guías de usuario en **[`docs/guia/`](docs/guia/)**:

| Guía | Para qué |
|---|---|
| **[Quickstart](docs/guia/quickstart.md)** | Tu primer InSim funcionando en 5 minutos. **Empieza aquí.** |
| **[Módulos y dependencias](docs/guia/modulos-y-deps.md)** | Manifiesto `insim.json`, dependencias entre módulos, comandos de chat, mixins. |
| **[Referencia de la API pública](docs/guia/api-publica.md)** | Clases, claves de config, utilidades y excepciones. |
| **[Arquitectura](docs/guia/arquitectura.md)** | Cómo funciona por dentro: ciclo del paquete, hilos, reconexión. |

Referencia del protocolo binario: **`docs/tutorial/`** (por paquete) y **`docs/InSim.txt`** (fuente de verdad).

Cambios entre versiones: **[`CHANGELOG.md`](CHANGELOG.md)**.

---

## CLI

```bash
# Ejecutar un InSim por nombre
lfs-insim run ai_control

# Listar InSims disponibles
lfs-insim list

# Ver metadatos de un InSim
lfs-insim info users_management

# Crear un nuevo InSim (scaffold --full por defecto; --minimal para el mínimo)
lfs-insim init mi_modulo

# Regenerar los stubs de tipo (.pyi)
lfs-insim stubs

# Regenerar todos los artefactos generados (stubs + lista de InSims del README)
lfs-insim update-all
```

---

## Configuración

La conexión a LFS se configura en `config/settings.py` (`INSIM_CONFIG`). Los valores
por máquina (contraseña de admin, ruta de LFS, nombre de usuario) van en
`config/settings_local.py` (no versionado):

```bash
cp config/settings_local.example.py config/settings_local.py
```

El [quickstart](docs/guia/quickstart.md#2-configurar-la-conexión) explica el flujo
completo; la lista de claves está en la
[referencia de la API](docs/guia/api-publica.md#config).

---

## Módulos incluidos

| Módulo | Descripción |
|--------|-------------|
| `users_management` | Rastrea en tiempo real conexiones, jugadores e IAs. Mapea UCID ↔ PLID ↔ username. Expone posición y velocidad. |
| `ai_control` | Controla coches IA mediante PID. Soporta **RouteMode** (waypoints grabados) y **FreeroamMode** (grafo de calles con FSM). Depende de `users_management`. |
| `test_insim` | Módulo de demostración y prueba del protocolo. Cubre todas las categorías de handler mediante comandos de chat. Útil como plantilla de referencia. |

---

## Telemetría (OutSim / OutGauge)

La telemetría UDP se activa de forma declarativa con el hook `set_outsim()`, igual
que `set_isi_packet()` gestiona los flags ISF. El socket UDP solo se abre si algún
módulo lo requiere.

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import OSO, SMALL

class MiInsim(InSimApp):

    def set_outsim(self):
        super().set_outsim()
        self.outsim_opts |= OSO.TIME | OSO.MAIN | OSO.INPUTS | OSO.DRIVE

    def on_connect(self):
        # OutGauge: activar vía SMALL.SSG (cada 50 ms)
        self.send_ISP_SMALL(SubT=SMALL.SSG, UVal=50)

    def on_OutSimPack2(self, packet):
        vx, vy, vz = packet.OSMain.Vel
        speed_kmh = (vx**2 + vy**2 + vz**2) ** 0.5 * 3.6

    def on_OutGaugePack(self, packet):
        print(f"{packet.RPM:.0f} RPM | {packet.Speed * 3.6:.0f} km/h")
```

Al arrancar, el log indica qué poner en el `cfg.txt` de LFS (opts, IP y puerto).
Referencia de campos y bloques OSO en `docs/tutorial/out/`.

---

## Documentación del protocolo

`docs/tutorial/` contiene **73 archivos Markdown** organizados en 4 carpetas:

| Carpeta | Paquetes | Descripción |
|---------|----------|-------------|
| `recibir/` | 43 | Paquetes que solo se reciben de LFS |
| `enviar/` | 16 | Paquetes que solo se envían a LFS |
| `ambos/` | 11 | Paquetes bidireccionales (TINY, SMALL, CPP, REO…) |
| `out/` | 3 | Telemetría UDP: OutSimPack, OutSimPack2, OutGaugePack |

Cada archivo incluye: descripción y dirección del paquete, tabla de campos con tipos enum correctos, y ejemplo de uso con el framework. La fuente de verdad del protocolo binario es `docs/InSim.txt`.

---

## Tests

```bash
# Ejecutar toda la suite
pytest

# Un archivo concreto
pytest tests/test_utils.py

# Un test específico
pytest tests/test_utils.py::TestPIDController::test_zero_dt_returns_zero -v
```

---

## Protocolo LFS InSim v10

- Conexión TCP en el puerto **29999**, protocolo little-endian
- Strings en latin-1, terminadas en null; `Size` en la cabecera = bytes totales / 4
- OutSim/OutGauge vía UDP (puerto `udp_port`, por defecto 30000) — solo activo si algún módulo declara `outsim_opts` en `set_outsim()`
- Documentación oficial del protocolo en `docs/InSim.txt`
