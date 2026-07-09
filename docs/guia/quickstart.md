# Quickstart — tu primer InSim en 5 minutos

De cero a un módulo respondiendo en el chat de LFS. Asume que ya tienes **Live for
Speed** y **Python 3.9+** instalados.

---

## 1. Instalar el framework

```bash
git clone https://github.com/AdrianPascarella/AP_LFS_InSim
cd AP_LFS_InSim
pip install -e ".[dev]"
```

El extra `[dev]` añade lo necesario para tests y tooling. El core en sí no tiene
dependencias externas.

---

## 2. Configurar la conexión

Copia la plantilla de config local (no se versiona: es por máquina) y ajústala:

```bash
cp config/settings_local.example.py config/settings_local.py
```

```python
# config/settings_local.py
LFS_DIR = "C:/LFS"                       # tu instalación de LFS

INSIM_CONFIG_OVERRIDES = {
    "admin_pass": "",       # la contraseña "Game Admin" de tu LFS (vacío si no tiene)
    "user_name": "TuUsuario",
}
```

> **`admin_pass` importa.** Debe coincidir con la contraseña "Game Admin" de tu
> LFS. Si no cuadra, LFS acepta el socket TCP y lo cierra justo después, sin dar
> ningún error — el framework lo detecta y te deja una pista en el log
> (`ISI likely rejected — check admin_pass`). En single-player local suele poder
> quedar vacía. (También puedes usar las variables de entorno `LFS_ADMIN_PASS` y
> `LFS_DIR` en lugar del archivo.)

---

## 3. Abrir el puerto InSim en LFS

Arranca LFS, entra a una pista y en el chat del juego escribe:

```
/insim 29999
```

Esto abre el puerto InSim en el 29999 (el que espera el framework por defecto).

---

## 4. Crear tu módulo

```bash
lfs-insim init mi_primer_insim --minimal
```

> **Perfiles.** Sin flag, `init` usa el scaffold **`--full`**: un módulo listo
> para un bot real, con comando de cierre protegido por admin, validación de
> permisos por UCID, `on_reconnect` (reconexión, P12) y petición de estado
> inicial (`TINY.NCN/NPL`). Aquí usamos **`--minimal`** para empezar con lo
> esencial y ver cada pieza; para un bot de verdad, omite el flag.

Esto genera un scaffold en `insims/mi_primer_insim/`:

```
insims/
└── mi_primer_insim/
    ├── insim.json        manifiesto (nombre, versión, dependencias)
    ├── __init__.py
    └── main.py           tu código
```

El `main.py` generado (perfil mínimo) es un módulo pequeño y funcional:

```python
from lfs_insim import InSimApp
from lfs_insim.packets import *
from lfs_insim.insim_enums import ISF
from lfs_insim.utils import CMDManager, separate_command_args, TextColors as c


class MiPrimerInsim(InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_prefix: str = self.config.get("prefix", "!")
        self.cmd_base: str = "mi_primer_insim"
        self.cmds: CMDManager
        self.logger.info(f"Modulo {self.name} inicializado.")

    def set_isi_packet(self):
        super().set_isi_packet()
        # Añade aqui los flags ISF que necesites, por ejemplo:
        # self.isi.Flags |= ISF.LOCAL | ISF.MCI

    def on_connect(self):
        self.cmds = (
            CMDManager(self.cmd_prefix, self.cmd_base)
            .add_cmd(
                name="hola",
                description="Saluda al servidor",
                args=None,
                funct=self._cmd_hola,
                is_mso_required=False,
            )
            .submit()
        )
        self.send_ISP_MSL(Msg=f"{c.GREEN}{self.name} {c.WHITE}conectado")

    def on_ISP_MSO(self, packet: ISP_MSO):
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if cmd == self.cmd_base:
            self.cmds.handle_commands(packet, args)

    def _cmd_hola(self):
        self.send_ISP_MSL(Msg=f"{c.GREEN}Hola desde mi_primer_insim!")

    def on_disconnect(self):
        self.logger.info(f"Modulo {self.name} desconectado.")
```

Lo que hace, de arriba abajo:

- **`set_isi_packet()`** — declara qué flags ISF necesita tu módulo (aquí, ninguno
  todavía). El cliente fusiona los flags de todas las apps antes de enviar el ISI.
- **`on_connect()`** — se ejecuta al conectar. Registra un árbol de comandos con
  `CMDManager` (un subcomando `hola`) y saluda por el chat.
- **`on_ISP_MSO(packet)`** — recibe cada mensaje del chat; si empieza por tu
  comando base, lo despacha al `CMDManager`.
- **`_cmd_hola()`** — el handler del subcomando `hola`.

---

## 5. Ejecutar

Con LFS abierto y el puerto InSim escuchando:

```bash
lfs-insim run mi_primer_insim
```

Deberías ver en el chat de LFS el mensaje **"mi_primer_insim conectado"**. Ahora
escribe en el chat del juego:

```
!mi_primer_insim hola
```

y el módulo responderá **"Hola desde mi_primer_insim!"**.

> El comando es `!` (prefijo) + `mi_primer_insim` (base, = nombre del módulo) +
> `hola` (subcomando). Puedes cambiar `self.cmd_base` en `main.py` por algo más
> corto. Escribir `!mi_primer_insim hola ?` muestra la ayuda del subcomando.

Para parar el InSim, `Ctrl+C` en la terminal.

---

## Qué acabas de hacer

- Instalaste el framework y configuraste la conexión a LFS.
- Creaste un módulo (`InSimApp`) que el **loader** descubre por su `insim.json`.
- El módulo se registró en un `InSimClient`, que abrió la conexión, envió el ISI
  con tus flags y empezó a despachar paquetes a tus handlers `on_ISP_*`.
- Respondiste a un comando de chat con `send_ISP_MSL`.

---

## Siguientes pasos

- **[Módulos y dependencias](modulos-y-deps.md)** — cómo un módulo depende de otro
  (`insim_dependencies`, `get_insim`), el manifiesto completo, los mixins y el
  patrón de comandos.
- **[Referencia de la API pública](api-publica.md)** — clases, claves de config,
  utilidades y excepciones.
- **[Arquitectura](arquitectura.md)** — qué pasa por debajo (ciclo del paquete,
  hilos, reconexión).
- **Ejemplos reales** — mira el módulo `test_insim` (referencia mínima con todas
  las categorías de handler) y `users_management` (tracking de usuarios/jugadores)
  en `insims/`.
- **Protocolo** — la referencia por paquete está en `docs/tutorial/`; la fuente de
  verdad binaria, en `docs/InSim.txt`.
