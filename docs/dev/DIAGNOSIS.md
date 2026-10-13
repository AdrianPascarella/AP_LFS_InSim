# 🩺 Diagnóstico — AP_LFS_InSim (lfs_insim)
> Revisión inicial: 2026-10-12 (S1). Se actualiza cada vez que se encuentra algo nuevo.

## Veredicto
El proyecto empieza de cero en una rama huérfana: todavía no hay código ni forma de verificarlo
(P1). El proyecto anterior (rama `refactor/estabilizacion`) funcionaba y tenía 914 tests en verde,
pero perdió el control por crecer sin límites (P4). Su copia de la especificación estaba desfasada
(P2). Lo que más vale de él son las definiciones del protocolo, que servirán para contrastar las
generadas, y las ideas de la conexión (reconexión, errores aislados por manejador).

## ✅ Sano (no tocar sin motivo)
- El archivo del proyecto anterior: rama `refactor/estabilizacion` y etiquetas `archivo/*`
  (ver «Lo que nunca se debe perder» en `PROTOCOL.md`).
- La identidad y las credenciales locales del repositorio, configuradas en S1.

## 🔴 Gravedad alta
### P1 — No hay comando de verificación   [RESUELTO en S2]
- **Evidencia:** la rama `main` nació vacía en S1; no hay tests, ni lint, ni CI.
- **Impacto:** hasta que exista un comando que pueda fallar, las reglas de la red de seguridad
  (§5) no se pueden aplicar y cada cambio es una afirmación, no un resultado.
- **Acción:** W1.2 (comando de verificación) y W1.3 (CI con Python 3.11–3.14).
- Resuelto (S2): `scripts/verify.py` (lint, formato, tipos, tests, entorno y aviso de tamaño), visto
  fallar en cada comprobación con defectos inyectados y en verde tras retirarlos. El CI sigue en W1.3.

### P4 — El proyecto anterior perdió el control por crecer sin límites   [ABIERTO: riesgo a vigilar]
- **Evidencia:** en `refactor/estabilizacion`, `insims/ai_control/map_ui.py` tiene 4.360 líneas y
  `nav_modes/freeroam/map_recorder.py` 2.753; los mapas JSON versionados suman unas 150.000 líneas;
  46 sesiones del protocolo antiguo y 358 commits en cinco meses. El usuario: «más pronto que tarde
  perdí el hilo y el control».
- **Impacto:** archivos que nadie, ni el agente, puede revisar enteros; arreglos que se apilan sin
  red; el usuario deja de entender su propio proyecto.
- **Acción:** que la verificación avise de los archivos que pasan de un tamaño razonable (W1.2), que
  la API pública sea pequeña y esté escrita antes que el código (W1.5), y que las aplicaciones vivan
  fuera del repositorio.

## 🟠 Gravedad media
### P2 — Una copia fija de la especificación se queda desfasada   [RESUELTO en S3]
- **Evidencia:** `docs/InSim.txt` del proyecto anterior (copiado el 03/07) frente a
  https://www.lfs.net/programmer/insim el 12/10: 41 líneas distintas. Falta la versión 0.8C27, que
  añade la página de códigos de los mensajes (`MSOData` en `IS_MSO`) y el enum `LID_*`.
- **Impacto:** paquetes que no coinciden con lo que envía LFS, sin que nada avise.
- **Acción:** W1.4: descargar la especificación oficial con un script, apuntar en git la versión
  comprobada y avisar cuando lfs.net cambie.
- Resuelto (S3): `scripts/fetch_spec.py` descarga la página, guarda el texto en `spec/cache/` y lo
  compara con `spec/checked.json` (0.8C27, INSIM_VERSION 10, huella SHA-256). Visto en rojo con
  una huella falseada (sale con 1 y falla el test de red) y sin conexión (sale con 2 y deja intacta
  la copia anterior). El workflow `spec` de GitHub lo comprueba cada lunes, aunque solo desde `main`.

### P3 — OutSimPack2 no se publica en la web   [ABIERTO]
- **Evidencia:** la página de InSim remite a `docs\OutSimPack.txt`, que solo viene con la
  instalación de LFS (`C:\LFS\docs\OutSimPack.txt`, fechado el 27/02/2021). No hay página en lfs.net.
- **Impacto:** el CI no puede descargar esa parte de la especificación; solo se puede comprobar en un
  equipo con LFS instalado.
- **Acción:** el código generado se guarda en git (así nadie necesita la especificación para
  instalar la biblioteca), y la comprobación contra `OutSimPack.txt` se hace solo donde exista ese
  archivo. Se decide en W1.4 / W2.
- Avance (S3): `fetch_spec.py` lee `OutSimPack.txt` si existe, guarda su huella en
  `spec/checked.json` y avisa si cambia; en el CI se salta. Que el código generado vaya en git se
  decide en W2.
- Avance (S4): decidido con el usuario que el código generado va en git, con un control que
  comprueba que está al día (W2.7).
- Avance (S5): el control existe. En este equipo, `verify.py` comprueba todo el código generado.
  En el workflow `spec` se comprueba lo que sale solo de InSim.txt, y `_outsim.py` y `__init__.py`
  se saltan avisando. Sigue abierto: si LFS cambiara `OutSimPack.txt`, solo se notaría en un equipo
  con LFS (`fetch_spec.py` avisa por la huella).

### P5 — Este equipo no tiene Python 3.11, 3.12 ni 3.13   [RESUELTO en S3]
- **Evidencia:** `py -0p` en S1: solo 3.14 y un 3.9 antiguo.
- **Impacto:** código que use algo de 3.12 o posterior pasaría la verificación local y rompería a
  los usuarios de 3.11.
- **Acción:** el CI comprueba de 3.11 a 3.14 (W1.3), y ruff se configura con `target-version`
  3.11 para avisar en local de la sintaxis demasiado nueva.
- Resuelto (S3): el workflow `verify` ejecuta `verify.py` en Python 3.11–3.14, en Linux y Windows,
  en cada push; las 8 combinaciones en verde. El equipo sigue sin esas versiones, pero ya no pasa
  nada sin que se note.

### P7 — `IS_BTN` con título de cuadro de texto pierde todo el texto   [RESUELTO en S8]
- **Evidencia:** S7. InSim.txt: si el primer carácter de `Text` es cero, LFS lee el título hasta el
  segundo cero y el texto del botón va después. `TailText` corta en el primer cero: lee `""` y
  no se puede enviar un título.
- **Acción:** W2.10, con la forma decidida por el usuario.
- Resuelto (S8): campo `IS_BTN.Caption` (U3); excepción `CAPTIONS`; codecs `TailText(caption=)` y `FilledIn`.

### P8 — `IS_MSO.TextStart` no sirve como índice del `str`   [RESUELTO en S8]
- **Evidencia:** S7. `TextStart` es una posición en bytes; el `str` ya no tiene los `^L`/`^J` y los
  caracteres de dos bytes cuentan uno, así que `Msg[TextStart:]` falla con nombres no latinos.
- **Acción:** W2.11.
- Resuelto (S8): `TextStart` es un índice en `Msg` (U4); excepción `TEXT_STARTS`; codec `TextOffset`.

### P6 — `CName` de un mod se perdía al leerlo como texto   [RESUELTO en S6, falta verlo en el LFS real]
- **Evidencia:** W2.8 (S6). InSim.txt solo dice «skin prefix», pero en el foro de lfs.net consta
  que, para un mod, LFS pone en `CName` el SkinID como entero de 32 bits, cuyo valor en
  hexadecimal es el ID del mod. Leído como texto cp1252, los SkinID 0x8D0A90, 0x100081 y 0x5A0012
  volvían como bytes distintos (huecos de cp1252, o un cero en medio que cortaba el texto), y los
  demás llegaban como un `str` sin sentido. El proyecto anterior también leía `CName` como texto
  y nunca trató los mods.
- **Impacto:** cualquier aplicación con mods (gestión de usuarios, registrador) no sabría qué
  coche lleva cada jugador, y al reenviar el `CName` mandaría otro coche.
- **Acción:** codec `CarName` (oficial `"XFG"`, mod `"5A1FB3"`, sin coche `""`) en los cuatro
  `CName`, y `IS_MAL.SkinID` como lista de `str` con el mismo formato (`API_DESIGN.md`, D3).
- Resuelto (S6): `_codec.CarName` y `_codec.SkinID`, y las excepciones `CAR_NAMES` y `SKIN_IDS`
  en `spec_overrides.py`. Tests con bytes de mods reales y ambiguos; red vista en rojo. Sigue
  pendiente comprobarlo con un mod en el LFS real (punto ciego, W3.1).
- Avance (S6): fuente leída entera, con la sesión del usuario en el foro: hilo «New InSim packet
  size byte and mod info» de lfs.net, primer post de Scawen (InSim 9). Confirma la regla de los
  tres bytes alfanuméricos y el orden de bytes de Intel. Su ejemplo (`_A3` = mod `33415F`; `XRZ` =
  coche oficial, quizá futuro) está ya en los tests.

### P9 — Dos paquetes en la misma lectura TCP se adelantaban al `after` del primero   [RESUELTO en S18]
- **Evidencia:** S18, prueba en LFS real (U8): 1 error de orden en `watch()` en ~5400 `IS_MCI`. `after` se
  programa con `call_soon`; `_read` despachaba seguidos todos los paquetes de un `read()`, así que el `before`
  y los manejadores del segundo corrían antes del `after` del primero. Con `Roster`: `IS_CNL(UCID=3)` + `IS_NCN`
  que reutiliza el UCID 3 en la misma lectura → el `before` del NCN tocaba la conexión vieja y el `after` del
  CNL la borraba: la conexión nueva desaparecía. Reproducido con el LFS falso (dos tests en rojo).
- **Impacto:** raro (hacen falta dos paquetes juntos), pero `watch()` iba a publicarse prometiendo ese orden.
- Resuelto (S18): `await asyncio.sleep(0)` tras cada paquete en `_read`; tests en `test_watch.py` y
  `test_roster.py`.

### P10 — Con comandos y un `Roster` propio hay dos `Roster`   [ABIERTO: se arregla en W10.1]
- **Evidencia:** S20, leyendo el código: los comandos crean su propio `Roster` a escondidas
  (`InSim._make_roster`, llamado por `Commands._need_roster`) y no ven el que crea el usuario con
  `Roster(insim)`. Resultado: dos instancias, y cada conexión pide `TINY_NCN`, `TINY_NPL` y `TINY_ISM` dos veces
  y guarda dos copias del mismo estado. Ningún test lo comprueba. Sin reproducir todavía con el LFS falso.
- **Impacto:** tráfico doble al conectar y estado duplicado; no da resultados erróneos (las dos copias siguen
  los mismos paquetes). Señal de que `InSim` depende de `Roster` sin que se vea.
- **Acción:** W10.1 (`insim.use()`: una instancia por tipo) y W10.2 (los comandos, plugin propio que usa
  `use(Roster)`); test en rojo primero.
