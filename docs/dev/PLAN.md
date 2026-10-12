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

## W2 — El protocolo, generado desde la especificación   ⏳ ACTIVA · detallada con el usuario en S4
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
- [ ] **W2.5** — **OutSim y OutGauge generados**, OutSimPack2 incluido según sus opciones.
- [ ] **W2.6** — **Tests:** ida y vuelta de todos los paquetes; tamaño contra el `// N` de la
  especificación; unos cuantos paquetes byte a byte escritos a mano; visto en rojo.
- [ ] **W2.7** — **Control «código generado al día»**: regenerar en memoria y comparar con git,
  en `verify.py` (si existe `spec/cache/`) y en el workflow `spec`. Visto en rojo.
- [ ] **W2.8** — **Segunda opinión:** comparar formatos y tamaños con el proyecto anterior con un
  script de un solo uso; las diferencias se revisan y se anotan en `LOG.md`. Incluye comprobar si
  `CName` lleva un SkinID binario (no texto) cuando el coche es un mod (anotado en S4).
- [ ] **W2.9** — **Texto de LFS ↔ `str`**: páginas de códigos (`^L`, `^E`…) y `MSOData`/`LID_*`
  de 0.8C27. Que funcione en el LFS real es punto ciego: se valida en W3.1.

## W3 — La conexión   📋 ESBOZADA
**Objetivo:** hablar con LFS: TCP (y UDP para OutSim/OutGauge), saludo `IS_ISI`, mantener viva la
conexión, reconexión, errores de un manejador que no tumban a los demás, y un **LFS falso** para
probar todo sin el juego. Primera prueba en el LFS real (punto ciego).

- [ ] **W3.1** — **Prueba en vivo del protocolo** (es un test de la biblioteca, no un InSim): un script junto a los tests que, con LFS abierto, conecta, pide información (versión, conexiones, jugadores, estado), envía mensajes y botones, comprueba que cada paquete recibido se lee bien y deja un informe de lo que vio. Con él se validan en LFS las tarjetas del punto ciego. Sustituye al `test_insim` del proyecto anterior, que cubría ~50 paquetes recibidos y ~16 enviados con comandos de chat          bloqueado por: W2 y el resto de W3

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

## W4 — La API de alto nivel y los ejemplos   📋 ESBOZADA
**Objetivo:** la forma de uso acordada en W1.5: eventos, envío cómodo de paquetes, el estado
opcional (conexiones, jugadores, UCID ↔ PLID ↔ nombre) y `examples/` con programas cortos que
funcionan.

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
