# 📚 Legado — qué rescatar del proyecto anterior (S14)

> Revisión a fondo de `origin/refactor/estabilizacion` (framework 0.2.0 sin publicar: núcleo en
> `src/lfs_insim/`, módulos en `insims/`, guías en `docs/guia/`, diagnóstico en `docs/dev/`).
> Solo se consulta, nunca se copia (CLAUDE.md). Esto es una **lista de propuestas del agente, sin
> decidir**: cada punto se decide con el usuario antes de entrar en `PLAN.md`.
> Leído: README, `docs/guia/*`, `insim_app/client/transport/loader/state`, `utils.py`, `config.py`,
> `configuration.py`, `cli.py`, `packet_sender_mixin.py`, `users_management`, `ai_control/app.py`,
> `map_ui.py` (solo su estructura), `DIAGNOSTICO.md`, `AUDITORIA_HOTLOOP.md`, `CHANGELOG.md`.

## 1. Cómo funcionaba el anterior, en una página
- **Framework de plugins:** cada módulo es una carpeta `insims/<nombre>/` con `insim.json`
  (versión, dependencias con restricciones de versión) y una clase que hereda de `InSimApp`.
  `lfs-insim run <nombre>` lo carga. Un **único cliente** compartía la conexión entre N apps; el
  orden de despacho seguía el de las dependencias.
- **Handlers por nombre de método:** `on_ISP_MSO(self, packet)`, más hooks `on_connect`,
  `on_disconnect`, `on_reconnect` y `on_tick` (cada 0,1 s por defecto).
- **Hilos:** un hilo por socket, una cola y un *worker* de despacho; `send()` seguro desde cualquier
  hilo. **Registro de paquetes activos:** solo se decodifican los tipos que algún módulo maneja.
- **Configuración:** un diccionario en capas (`DEFAULT_CONFIG` → `config/settings.py` →
  `settings_local.py` → variables de entorno), con claves de reconexión, `handler_errors`, etc.
- **Utilidades:** `CMDManager` (árbol de comandos), `TextColors`, `strip_lfs_colors`, conversiones de
  unidades, `PIDController`, `LFSConfigManager` (lee y escribe `cfg.txt` con copia de seguridad).
- **Aplicaciones dentro del repositorio:** `users_management` (quién es quién), `ai_control` (IA por
  PID, rutas y calles con grafo; `map_ui.py` solo tiene ~3.000 líneas de botones), `prueba_botones`,
  `test_insim` (plantilla). Lo que se rompió fue `ai_control`: ficheros gigantes, mixins acoplados,
  parches matemáticos y 36 commits sobre `map_ui.py`.

## 2. Qué hacía el anterior que la versión actual NO hace

### A. Alto valor, coste bajo o medio — propongo plantearlos
| # | Idea | Anterior | Hoy | Propuesta |
|---|---|---|---|---|
| A1 | **Comandos con tipos, ayuda y grupos** | `CMDManager`: argumentos tipados (`("kmh", int)`) que se validan y convierten, mensaje de error con sonido, ayuda automática (`!um` lista, `!um cmd ?`), grupos (`!aic start`) | `Command.args` son cadenas sin validar; sin ayuda ni grupos | Usar anotaciones de tipo: `def speed(cmd: Command, kmh: int)`; grupos con `insim.group("aic")`; ayuda sacada de la docstring |
| A2 | **Permisos de comando** | Lista blanca de usuarios (`user_autorized_cmd`), comprobando el UCID | Nada; hay `Connection.admin` | `on_command("x", admin=True)` o `users={...}`: lo peligroso (kick, ban) no debería depender de que cada app se acuerde |
| A3 | **`on_disconnect` y saber si es una reconexión** | Hooks `on_disconnect` / `on_reconnect` (los usaron las apps de IA: parar bucles, redibujar botones) | Solo `on_connect` | `@insim.on_disconnect`, y un argumento que diga si es la primera conexión o una reconexión |
| A4 | **Ayudante de botones** | Nada reutilizable: cada pantalla hecha a mano → `map_ui.py` de 3.000 líneas. Es el dolor mayor del legado | Idea aparcada en S12 (`PLAN.md`, «Ideas») | **Subirla de prioridad.** Reparto automático de `ClickID`, botones/etiquetas/cuadros de texto, paneles y pestañas, clic → función, redibujo, limpieza por conexión y **redibujo tras reconectar** (LFS borra los botones al caer la conexión) |
| A5 | **Unidades** | `lfs_pos_to_meters`, `lfs_speed_to_kmh`, `lfs_angle_to_degrees`, `lfs_angvel_…` (con `rev=True` para ir al revés) y objetos `Coordinates`/`Speed`/`Angle`/`CCIFlags` con propiedades (`x_m`, `speed_kmh`, `degrees`) | Paquetes con valores crudos de LFS | Módulo `lfs_insim.units` con funciones puras; propiedades sobre los paquetes por el mecanismo de `packets/_extras.py` (como `IS_MSO.text`) |
| A6 | **Modo de desarrollo que no se traga errores** | `handler_errors="raise"`: el primer error detiene el cliente y se relanza | Siempre se registra y se sigue | `InSim(errors="raise")` (o `debug=True`) |
| A7 | **Enviar color** | `TextColors.RED…` | `text.plain` / `strip_colours` solo quitan | Constantes y una función (`colour("x", RED)`) en `lfs_insim.text` |

### B. Valor medio — decidir después de A
| # | Idea | Detalle |
|---|---|---|
| B1 | **Roster con movimiento y datos propios** | `users_management` guardaba posición/velocidad desde `MCI` y limpiaba al terminar la carrera (`TINY.MPE`). Hoy `Roster` no sigue `MCI`. Opcional: `Roster(insim, motion=True)`. Y un `Player.data` / `Connection.data` (el anterior tenía `ai.extra["aic"]`): datos por jugador que se borran solos al irse |
| B2 | **Handlers lentos** | Hoy todo va en un solo hilo de asyncio: un `def` lento retrasa la lectura de TODO. El anterior movió el despacho a un hilo propio para que el *keepalive* nunca esperase. Con `MCI` a 100 Hz y una app de IA, importa. Mínimo: documentarlo y ofrecer `run_in_executor` / `on(..., threaded=True)` |
| B3 | **Decodificar solo lo que se usa** | El «registro de paquetes activos» descartaba los tipos sin handler antes de decodificar. Hoy `unpack_insim` los decodifica todos. **Medir antes** (con `MCI` a 100 Hz y 20 coches) y decidir |
| B4 | **Traza de lo enviado y recibido** | `mute_send_logs("ISP_AIC")`: trazar cada paquete enviado pero silenciando los muy frecuentes. Hoy, nada. Un `insim.trace(...)` con filtro por tipo ayudaría a depurar apps |
| B5 | **Ayudante para `cfg.txt`** | `LFSConfigManager` + `tools/setup_lfs.py`: leer, comparar con lo deseado y escribir con copia de seguridad (así se activan OutSim/OutGauge). **Cuidado:** LFS reescribe `cfg.txt` al cerrarse, y la regla de §13 (CRLF). Solo con LFS cerrado y con permiso |
| B6 | **Cookbook por paquete** | `docs/tutorial/` tiene 73 fichas («cuándo llega, qué responder, ejemplo») en castellano, por categorías enviar/recibir/ambos/out. La especificación no explica el *cómo*. Rescatar como guía en inglés, con ejemplos comprobados por test (`tests/test_docs.py`) |
| B7 | **Consola de Windows (QuickEdit)** | P23 del anterior: un clic en la consola congela el proceso (y el log). Lo mitigaban desactivándolo al arrancar. Aplicable a `insim.run()` en Windows, o al menos documentarlo |

### C. Descartar o aparcar (con el motivo)
- **Cargador de módulos, `insim.json`, dependencias con versiones, CLI `lfs-insim run/init/list`.**
  Es justo lo que se descartó en S1 («biblioteca, no framework»). Si una aplicación real lo pide,
  mejor un paquete aparte (`lfs-insim-apps`). Lo único útil: *varias apps compartiendo UNA
  conexión*. Hoy se resuelve pasando `insim` a cada una (`Roster(insim)`). Mini-convención opcional:
  `def setup(insim)` + `insim.load(modulo)`.
- **`send_ISP_XXX(**campos)` mágico** (`__getattr__`) y los stubs `.pyi` generados para suplirlo: el
  `insim.send(IS_MSL(...))` tipado de hoy es más claro y el editor lo entiende sin generar nada.
  Los atajos útiles ya existen (`say`, `command`); se añadirán los que pidan las aplicaciones.
- **Configuración en capas con diccionario** (`self.config.get("clave")`), `settings_local.py`,
  variables de entorno: hoy son argumentos con nombre y la biblioteca no lee archivos del proyecto.
  Mejor así (P14 del anterior era justo el problema contrario).
- **`on_tick` impreciso:** `every()` de hoy lo mejora (sin solapes ni ráfagas).
- **Hilos propios y cola:** asyncio de un solo hilo es más simple y de momento suficiente (ver B2).
- **`PIDController`, geometría de IA (rumbos, radar, grafo), mapas:** son de la aplicación de control
  de IA, que vive aparte (`PLAN.md`, «Aplicaciones aparte»). Solo `calc_dist_3d` era genérico.

## 3. Lecciones del anterior que conviene comprobar en la versión nueva
1. **P21 — enviar `IS_REO`, `IS_HCP` e `IS_IPB` con baneos fallaba siempre** (listas de longitud fija
   y tuplas anidadas); nadie lo notó hasta usarlo en vivo. **En la nueva no hay ningún test que
   nombre esos tres paquetes.** Comprobar que el round-trip genérico los cubre; si no, añadirlos.
2. **P22 — orden en la reconexión:** limpiar el estado ANTES de volver a pedirlo (si no, la respuesta
   rápida de LFS se borraba). Comprobar que `Roster` lo respeta (hoy se pide en cada conexión).
3. **P24 — tormenta de reconexión:** un ISI rechazado (contraseña) reiniciaba la espera y dio ~250
   conexiones en 25 s hasta que LFS contestó `InSim - TCP excess`. La nueva solo reinicia la espera
   cuando LFS contesta `IS_VER`, y avisa «wrong admin password?»: **bien**; vale un test que lo fije.
4. **P23:** ver B7.
5. **Rendimiento de `MCI`:** la auditoría del anterior midió ~1,2 µs por coche en el volcado y
   presupuestó 0,6 ms por tick con 16 IA. Es un buen punto de partida para un benchmark de la nueva.
6. **Proceso:** el proyecto anterior se estropeó por un módulo que creció sin partirse
   (`map_ui.py`, `traffic.py`). El aviso de tamaño de `_connection.py` (~405 líneas) y de
   `_codec.py` (525) ya es el equivalente.

## 4. Orden que propongo
1. A6, A7, A3 (pequeños, de golpe).
2. A1 + A2 (comandos), porque cualquier aplicación los usa.
3. A5 (unidades), porque la cámara libre y la IA los necesitan.
4. A4 (botones), el más grande: diseñarlo con la aplicación de botones delante, no a ciegas.
5. Lo de la sección 3 (tests) en paralelo; B-x según lo pida la primera aplicación (W6).

## 5. Decidido con el usuario (S14)
- Aprobado «prácticamente todo» de las secciones 2 y 4. Se plantea como **W7** (generador: dirección y
  atajos) y **W8** (el resto de mejoras), en `PLAN.md`.
- **Dirección de los paquetes:** sale de la especificación (el `enum` ISP ya marca `info` /
  `instruction` / `both ways`). No se recupera el `.pyi` del anterior: servía para los `send_ISP_*`
  mágicos, que no vuelven; ahora son métodos reales generados.
- **Todas las formas, canónica `on_IS_XXX`:** `@insim.on_IS_NPL`, `@insim.on(IS_NPL)` y
  `@insim.on(received.IS_NPL)`; y lo mismo para enviar (`send_IS_XXX`, `send(...)`, `sent.`).
  Incluye OutSim y OutGauge. Condiciones: una sola fuente, test de equivalencia, una forma en la
  guía, sin más variantes.
- **Plugins:** `Roster` ya es un plugin; no se recupera el cargador, los manifiestos ni el CLI. Primero
  hacer pública su puerta (`order="before"`); una convención de clase con métodos decorados solo si
  el ayudante de botones o la primera aplicación (W6) la piden.
- Pendiente de decidir: forma de las anotaciones de los comandos (A1), y si la tabla de direcciones
  va en la documentación pública (propuesta: sí).
