# 🗺️ Plan — AP_LFS_InSim (lfs_insim)
> Fases con criterios de aceptación. `[x]` = hecho. `P<n>` remite a `DIAGNOSIS.md`. Cada tarea lleva
> su ID estable, `W<n>.<m>`: se asigna una vez, en orden, y nunca se reutiliza ni se renumera,
> aunque la tarea esté hecha o la fase cerrada.
>
> Borrador inicial de S1, sacado de la revisión del proyecto anterior. Solo W1 está detallada; las
> demás se detallan al abrirlas, con el usuario.

## W1 — Cimientos: el paquete vacío, su verificación y la especificación   ✅ CERRADA en S3
**Objetivo:** que exista un paquete `lfs_insim` instalable (aunque no haga nada), con un comando
que puede fallar, CI en las cuatro versiones de Python, la especificación oficial descargable y la
forma de la API acordada antes de escribir el código.

- [x] **W1.1** — Esqueleto del paquete: `src/lfs_insim/` con `py.typed`, `pyproject.toml` (nombre `lfs-insim`, Python ≥ 3.11, sin dependencias), README mínimo en inglés y `.venv`          hecho en S2 → LOG.md S2
- [x] **W1.2** — Comando de verificación (`scripts/verify.py`): lint, formato, tipos y tests, más un aviso de archivos demasiado grandes (P4); comprobado en rojo          hecho en S2 → LOG.md S2
- [x] **W1.3** — CI en GitHub Actions: el mismo comando en Python 3.11, 3.12, 3.13 y 3.14          hecho en S3 → LOG.md S3
- [x] **W1.4** — Script de la especificación: descarga https://www.lfs.net/programmer/insim, extrae el texto a una carpeta ignorada, lee `C:\LFS\docs\OutSimPack.txt` si existe, y guarda en git la versión comprobada (hoy 0.8C27) con su huella; un test avisa si lfs.net cambia          hecho en S3 → LOG.md S3
- [x] **W1.5** — Diseño de la API pública, escrito antes que el código: cómo se ve un programa con la biblioteca (conectar, recibir eventos, enviar paquetes, cerrar), síncrona o asíncrona, y qué entra en la biblioteca (por ejemplo, la gestión de usuarios). Se acuerda con el usuario con ejemplos de uso reales          hecho en S2 → LOG.md S2

**Criterios de aceptación:** `pip install -e .` funciona en un entorno limpio; el comando de
verificación pasa y se ha visto fallar; el CI está en verde en las cuatro versiones; el script baja
la especificación y detecta un cambio; el diseño de la API está escrito y el usuario lo ha aprobado.

## W2 — El protocolo, generado desde la especificación   ✅ HECHA en S8 · detallada con el usuario en S4
**Objetivo:** todos los paquetes y enums de InSim v10, OutSim y OutGauge, generados a partir de la
especificación oficial (los `struct` de C), con sus comentarios convertidos en documentación y
tests de ida y vuelta (empaquetar → desempaquetar). Las definiciones del proyecto anterior se usan
como segunda opinión para encontrar errores, no como fuente.

**Decidido en S4 (→ LOG.md S4):** enums y flags como clases (`TINY.NCN`, `ISF.MCI`); el código
generado va en git, con un control que comprueba que está al día (P3); los campos de texto son
`str`, con la codificación de LFS hecha en W2. Los campos que usan un enum quedan como `int`.

- [x] **W2.1** — **Lector de la especificación** (`scripts/spec_parser.py`): convierte
  `spec/cache/` en un modelo (structs, campos, enums, flags, constantes y sus comentarios). Falla
  con un mensaje claro ante cualquier construcción que no entienda y no esté en las excepciones.
  *Acepta:* lee los 81 `struct` de InSim.txt y los de OutSimPack.txt; tests con fragmentos.
  hecho en S4 → LOG.md S4
- [x] **W2.2** — **Excepciones escritas a mano, en un solo archivo:** qué campo da la longitud de
  cada paquete variable, el nombre de los enums sin nombre, los valores que no son identificadores
  válidos (`DL_18`) y las partes condicionales de OutSimPack2 (estas, con W2.5).
  hecho en S4 → LOG.md S4
- [x] **W2.3** — **Núcleo de empaquetado** escrito a mano (`_codec`): clase base, `pack()` y
  `unpack()`, `Size` (÷4) y `Type` automáticos, relleno a cero, texto al final rellenado a 4 bytes
  y arrays con longitud dada por un campo.
  hecho en S4 → LOG.md S4
- [x] **W2.4** — **Paquetes de InSim generados** (dataclasses con los nombres de la
  especificación y los comentarios de C como docstring) y sus enums y flags.
  hecho en S4 → LOG.md S4
- [x] **W2.5** — **OutSim y OutGauge generados**, OutSimPack2 incluido según sus opciones.
  hecho en S5 → LOG.md S5
- [x] **W2.6** — **Tests:** ida y vuelta de todos los paquetes; tamaño contra el `// N` de la
  especificación; unos cuantos paquetes byte a byte escritos a mano; visto en rojo.
  hecho en S4 (InSim) y S5 (OutSim/OutGauge) → LOG.md S4, S5
- [x] **W2.7** — **Control «código generado al día»**: regenerar en memoria y comparar con git,
  en `verify.py` (si existe `spec/cache/`) y en el workflow `spec`. Visto en rojo.
  hecho en S5 → LOG.md S5
- [x] **W2.8** — **Segunda opinión:** comparar formatos y tamaños con el proyecto anterior con un
  script de un solo uso; las diferencias se revisan y se anotan en `LOG.md`. Incluye comprobar si
  `CName` lleva un SkinID binario (no texto) cuando el coche es un mod (anotado en S4).
  hecho en S6 → LOG.md S6
- [x] **W2.9** — **Texto de LFS ↔ `str`**: páginas de códigos (`^L`, `^E`…) y `MSOData`/`LID_*`
  de 0.8C27. Que funcione en el LFS real es punto ciego: se valida en W3.1.
  hecho en S7 → LOG.md S7
- [x] **W2.10** — **Título del cuadro de texto en `IS_BTN`** (P7): campo `Caption` (U3).
  hecho en S8 → LOG.md S8
- [x] **W2.11** — **`IS_MSO.TextStart` en un `str`** (P8): índice en `Msg`, no bytes (U4).
  hecho en S8 → LOG.md S8

## W3 — La conexión   ✅ HECHA en S12 · detallada con el usuario en S9
**Objetivo:** hablar con LFS: TCP (y UDP para OutSim/OutGauge), saludo `IS_ISI`, mantener viva la
conexión, reconexión, errores de un manejador que no tumban a los demás, y un **LFS falso** para
probar todo sin el juego. Primera prueba en el LFS real (punto ciego).

**Decidido en S9 (→ LOG.md S9):** `@insim.every()` entra en W3; InSim por UDP y el relay, a
«Ideas». Las pruebas usan los dos LFS: el **falso** en los tests de cada push (el CI no tiene LFS;
casos raros fáciles de montar) y el **real**, que abre y cierra el agente, en W3.1. W3.1 deja de
ser una tarjeta del usuario: solo le queda lo que se ve en pantalla. Orden: W3.2 → W3.8, y W3.1 al
final.

- [x] **W3.2** — **Partir el flujo TCP en paquetes**, sin sockets (función pura): `Size` × 4, un
  paquete partido entre lecturas, varios en una lectura. Un tipo desconocido o un tamaño imposible
  se registra y se salta sin cortar la conexión. *Acepta:* tests unitarios con esos casos.
  hecho en S9 → LOG.md S9
- [x] **W3.3** — **El LFS falso** (en los tests): servidor asyncio que recibe el `IS_ISI`,
  contesta `IS_VER`, envía paquetes preparados y apunta lo que recibe. *Acepta:* lo usan los tests
  de W3.4–W3.6. hecho en S9 → LOG.md S9 (su aceptación se completa al usarlo en W3.4)
- [x] **W3.4** — **`InSim` básico (D1, D2):** conectar y enviar `IS_ISI` (nombre, contraseña,
  flags, intervalo, prefijo); `send()`; `@insim.on(...)` con `def` y `async def`; `run()` y
  `async with insim`. Un error en un manejador se registra con `logging` y no para a los demás.
  *Acepta:* los ejemplos 1 y 3 de `API_DESIGN.md` (sin OutGauge) funcionan contra el LFS falso.
  hecho en S10 → LOG.md S10 (de los ejemplos, lo que no es de W3.4 queda para su tarea:
  `packet.text` en W4, `every` en W3.8, `run(insim, gauge)` en W3.7)
- [x] **W3.5** — **Mantener viva la conexión:** contestar `TINY_NONE` a `TINY_NONE` (LFS lo manda
  cada 30 s y cierra tras 70 s sin recibir nada); sin datos durante ese tiempo, la conexión se da
  por muerta; al salir, `TINY_CLOSE`. *Acepta:* tests contra el LFS falso con el tiempo acortado.
  hecho en S10 → LOG.md S10
- [x] **W3.6** — **Reconexión:** si LFS no está o se cierra, reintentar con espera creciente y
  volver a enviar el `IS_ISI`; un evento de «(re)conectado» para que el `Roster` de W4 pida el
  estado. *Acepta:* tests con el LFS falso parado y vuelto a arrancar. hecho en S10 → LOG.md S10
- [x] **W3.7** — **UDP: `OutSim` y `OutGauge`** con la misma forma (D5) y `run(insim, gauge)` para
  varios a la vez. Nunca en el puerto 30000 (§13). *Acepta:* datagramas locales en los tests.
  hecho en S11 → LOG.md S11
- [x] **W3.8** — **Ritmo fijo `@insim.every(segundos)`** (el antiguo `on_tick`), `def` o
  `async def`. *Acepta:* test con el tiempo acortado; un error en él no lo detiene.
  hecho en S11 → LOG.md S11

- [x] **W3.1** — **Prueba en vivo del protocolo** (es un test de la biblioteca, no un InSim): un script junto a los tests que, con LFS abierto, conecta, pide información (versión, conexiones, jugadores, estado), envía mensajes y botones, comprueba que cada paquete recibido se lee bien y deja un informe de lo que vio. Incluye un
jugador con un mod, para ver su SkinID en `CName` (P6). Con él se validan en LFS las tarjetas del punto ciego. Sustituye al `test_insim` del proyecto anterior, que cubría ~50 paquetes recibidos y ~16 enviados con comandos de chat          bloqueado por: W2 y el resto de W3
  *Precisado en S9:* lo ejecuta el agente, que abre LFS y lo cierra con `/exit` por InSim (permisos
  en `PROTOCOL.md`). Se hace con el LFS recién reinstalado (U5). En el juego limpio InSim no
  escucha: hay que activarlo con `/insim=29999` (se escribe en LFS, o va en `autoexec.lfs`, que
  está en `C:\LFS` y pide permiso). Se comprueba si OutSim y montar una
  carrera con IA se pueden configurar con comandos durante la partida; si hace falta tocar
  `cfg.txt`, se pide permiso cambio a cambio.
  *Primera pasada en S12 → LOG.md S12:* `tests/live_lfs.py` hecho y ejecutado con LFS en el menú
  (un jugador, sin carrera): 0 paquetes ilegibles, 0 con el contenido cambiado al reescribirlos;
  texto con griego y `€` bien. *Segunda pasada en S12:* carrera de 3 vueltas con 2 IA y un coche
  mod: NPL, MCI, NLP, RST, SPX, LAP, CON, HLV, FLG, FIN, RES, CIM, AXI, BTC y BTT, todo bien;
  `CName` = SkinID del mod (`35D799`, P6 validado); `Caption` visible en LFS (U3).
  *Tercera pasada en S12:* OutGauge, OutSim clásico y `OutSimPack2` (Opts `1ff`), ~100 paquetes
  por segundo cada uno, todo bien; con permiso del usuario en `cfg.txt`, ya restaurado. Encontró
  un error: `OutGaugePack.Car` lleva el SkinID de un mod, como `CName` (arreglado).
  hecho en S12 → LOG.md S12
  **Preferencia del usuario (S12):** quedar fuera de la prueba. La activación de InSim la hace el
  agente: controlando la pantalla y/o con `autoexec.lfs` (este, con permiso, porque está en
  `C:\LFS`). En S12 aún la escribió el usuario.

## Aplicaciones aparte: lo que la biblioteca debe permitir (requisitos)
> Decidido con el usuario en S1. **Aquí solo hay texto: el código de estas aplicaciones vive en sus
> propios proyectos, nunca en este repositorio.** Sirven para comprobar que la biblioteca es cómoda
> (punto ciego) y para saber qué hace falta en cada fase. Los paquetes se dan sin prefijo (`MCI` =
> `IS_MCI`). Cuando una aplicación demuestre que falta algo, se añade aquí y como tarea en su fase.

| Aplicación | Para qué | Qué necesita de la biblioteca | Se puede escribir desde |
|---|---|---|---|
| **Gestión de usuarios** (antes `users_management`) | Saber en todo momento quién es quién: UCID ↔ PLID ↔ usuario/nombre, IA o humano, posición y velocidad | Recibir NCN, CNL, NPL, PLL, ISM, MCI, MSO y TINY; pedir el estado inicial (TINY NCN/NPL); rehacer el estado al reconectar. **Propuesta del agente:** que el estado sea parte opcional de la biblioteca (W1.5) | W3 |
| **Registrador de eventos** (lo necesita streamer-project) | Anotar lo que pasa en una sesión: adelantamientos, luchas, contactos, vueltas, boxes, banderas, resultados | Recibir VER, STA, RST, NCN, CNL, NPL, PLL, PLP, PLA, MCI, CON, HLV, CRS, LAP, SPX, PIT, PSF, PEN, FLG, FIN, RES y TINY; pedir estado (TINY NCN/NPL/SST/VER) | W3 (cómodo, W4) |
| **Cámara libre** (lo necesita streamer-project) | Mover la cámara del juego siguiendo la acción para grabar | Enviar CPP y SCC; recibir CPP y MCI (posiciones); quizás repeticiones (RIP) | W4 |
| **Botones** (antes `prueba_botones`) | Interfaz dentro de LFS: botones, cuadros de texto | Enviar BTN y BFN; recibir BTC, BTT y BFN; MSL/MSO para comandos de chat | W4 |
| **Control de IA** (antes `ai_control`) | Coches IA que conducen solos por rutas o calles | Enviar AIC, MST y botones; recibir MCI, CRS, RST, PLL, MSO, BTC y BTT; un ritmo fijo de actualización (`on_tick`) | W4 (la última: es la que hizo perder el control al proyecto anterior, P4) |

## W4 — La API de alto nivel y los ejemplos   ⏳ ACTIVA · detallada con el usuario en S12
**Objetivo:** la forma de uso acordada en W1.5: eventos, envío cómodo de paquetes, el estado
opcional (conexiones, jugadores, UCID ↔ PLID ↔ nombre) y `examples/` con programas cortos que
funcionan.

**Decidido en S12 (→ `API_DESIGN.md`, «Decidido en S12 para W4»):** el `Roster` guarda identidad
y estado, no posición ni velocidad; habrá `@insim.command`; los botones, solo como ejemplo (sin
ayudante hasta que una aplicación lo pida); habrá `await insim.request(...)`. Cada tarea se prueba
contra el LFS falso y, al final (W4.7), contra el LFS real, que maneja el agente.

- [x] **W4.1** — **`packet.text` en `IS_MSO`:** lo que escribió el usuario (`Msg[TextStart:]`),
  sin «Nombre : ». Los paquetes son generados: la propiedad va escrita a mano y el generador la
  engancha. *Acepta:* tests con los `IS_MSO` reales de S12 (usuario, sistema, prefijo).
  hecho en S12 → LOG.md S12 (`packets/_extras.py` + `spec_overrides.EXTRAS`)
- [x] **W4.2** — **`await insim.request(...)`:** envía el `IS_TINY` con un `ReqI` propio (nunca el 1
  del `IS_ISI`) y devuelve la respuesta; para las de varias partes (NCN, NPL, RES, SLC…), la lista,
  sabiendo cuándo acaba por sus contadores (`Total`, `NumP`, `NumRes`) o por un tiempo sin más.
  Con límite de tiempo (`TimeoutError`). Las respuestas siguen llegando también a `@insim.on`.
  Forma exacta (una función o `request` y `request_all`) se precisa al escribirla. *Acepta:* tests
  con el LFS falso: una respuesta, varias, ninguna (vence el plazo), dos peticiones a la vez.
  hecho en S12 → LOG.md S12 (`request(IS_X)` y `request_all(IS_X)`, por el tipo de la respuesta)
- [x] **W4.3** — **`Roster` (`lfs_insim.state`, D4):** `roster.connections[UCID]` y
  `roster.players[PLID]`, con usuario, nombre, coche, IA o humano, admin, en boxes, y el paso de
  uno a otro (`player.connection`, `connection.players`). Pide NCN y NPL en cada (re)conexión y
  rehace el estado. Sigue NCN, CNL, CPR, NPL, PLL, PLP, TOC, `TINY_CLR` y `TINY_MPE`. *Propuesta del
  agente, a confirmar al escribirlo:* el `Roster` se actualiza antes que los manejadores del
  usuario cuando alguien llega o cambia, y después cuando se va, para que en un manejador de
  `IS_CNL` o `IS_PLL` aún se pueda saber quién era. *Acepta:* tests de cada paquete, de una
  reconexión y de la IA (sin conexión propia: `UCID` 0), y el ejemplo 2 de `API_DESIGN.md`.
  hecho en S12 → LOG.md S12 (el ejemplo 2 se escribe y prueba en W4.6)
- [x] **W4.4** — **Enviar con comodidad:** `insim.say(texto)` (`IS_MST` o `IS_MSX` según los bytes
  ya codificados; `ValueError` si no cabe), `insim.say(texto, to=UCID)` (`IS_MTC`) e
  `insim.command("/restart")`. *Acepta:* tests de los límites de tamaño con texto no latino.
  hecho en S12 → LOG.md S12
- [x] **W4.5** — **`@insim.on_command("hello")`** (el `!hello` del ejemplo 1; se planificó como
  `@insim.command`, pero ese nombre ya lo usa W4.4): usa el `prefix` de
  `InSim` (sin prefijo, error al registrar), separa los argumentos y da quién lo escribió y una forma
  de contestarle. *Acepta:* tests con `IS_MSO` de prefijo, con argumentos, con un comando que no
  existe y con un error dentro del manejador. hecho en S12 → LOG.md S12
- [ ] **W4.6** — **`examples/`:** `hello.py`, `who.py`, `ai_and_gauge.py` (los ejemplos 1–3 de
  `API_DESIGN.md`, ajustados a lo que de verdad quedó) y `buttons.py` (`IS_BTN`, `IS_BTC`, `IS_BTT`
  tal cual). Si escribir `buttons.py` resulta incómodo, se anota como idea de ayudante. *Acepta:*
  un test por ejemplo que lo ejecuta contra el LFS falso.
- [ ] **W4.7** — **Los ejemplos en el LFS real**, ejecutados por el agente con `tests/lfs_screen.ps1`
  (OutGauge, solo con permiso para `cfg.txt`). *Acepta:* cada ejemplo hace lo que dice, visto en la
  captura de pantalla o en los paquetes.

## W5 — Publicación   📋 ESBOZADA
**Objetivo:** documentación pública, versión 0.1.0 en TestPyPI y después en PyPI, y prueba de
instalación en otro equipo (punto ciego).

## W6 — Primera aplicación aparte   📋 ESBOZADA
**Objetivo:** escribir, en un proyecto separado, la primera aplicación real con la biblioteca (la
cámara libre, que necesita streamer-project) y anotar cada incomodidad como tarea de la biblioteca.

## Ideas (aparcadas, sin compromiso)
- Rescatar del proyecto anterior los 73 tutoriales por paquete (`docs/tutorial/`) como base de la
  documentación pública — solo si la generación de W2 no da algo mejor a partir de los comentarios
  de la especificación.
- Las demás aplicaciones (control de IA, registrador de eventos) — después de W6, cada una en su
  proyecto (sus requisitos, en «Aplicaciones aparte»).
- **InSim por UDP** (aparcado en S9 para pensarlo con calma). El usuario cree que debería ser
  configurable, con TCP por defecto y `MCI`/`NLP` por UDP (`UDPPort` del `IS_ISI`). Ninguna
  aplicación de la lista lo necesita hoy.
- **Relay de InSim** (`isrelay.lfs.net`, paquetes `IR_*`) para conectar a servidores remotos
  (aparcado en S9): ninguna aplicación de la lista lo usa.
