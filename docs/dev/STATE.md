# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-28 (S31), equipo principal. **S31: protocolo actualizado a la plantilla v4** (sin tocar
> código): `DECISIONS.md` (D1–D23; D1–D6 son las de `API_DESIGN.md`), `ARCHITECTURE.md`, `factory.json` con el
> comando de verificación, párrafo para hilos sin sesión en `CLAUDE.md` y scripts del protocolo v4. El plugin
> `agentic-protocol@software-factory` está en `.claude/settings.json`. El siguiente paso no cambia: lo de S30.
> Antes, S30 (2026-10-18). **S30: W14 aceptada y W14.1 hecha** (P12: un `on_connect`
> registrado con la conexión abierta se llama al momento; un `Roster` hecho tarde ya queda listo). Sin publicar:
> **▶️ SIGUIENTE aquí: W14.2** (0.9.1, con permiso del usuario) y decidir W14.3 (P13, `every()` tarde). Antes: **S29: U11 y U14 cerradas, W11 cerrada** (con dos cuentas
> del usuario en su servidor; nuevo `tests/live/group_p.py`; ninguna acción pendiente). **S28: W13 cerrada y `lfs-insim` 0.9.0 publicada**
> (`Arg` para argumentos de tipo propio en los comandos, `float` finito), fijada en `lfs-ai-control`.
> **▶️ SIGUIENTE aquí:** nada propio; se sigue en `lfs-ai-control`. Lo de S27 sigue debajo. **S27: W12 cerrada y `lfs-insim` 0.8.1 publicada:** nombres
> para los valores de `IS_AIC` (`STEER`, `TOGGLE`, `HEADLIGHTS`, `SIREN`, `INDICATORS`, `LOOK` generados de
> `InSim.txt` con `LISTED_VALUES`; `GEAR` a mano, `HAND_VALUES`), vistos en LFS 0.8C32 con
> `tests/live/aic_values.py --admin admin` (24 PASS, 4 SKIP). Aviso dejado en `lfs-ai-control` (su W3.9).
> **▶️ SIGUIENTE aquí:** nada propio; se trabaja en `lfs-ai-control` (clonado también en este equipo:
> `C:\Users\pasca\proyectos\lfs-ai-control`, sin `.venv` todavía). **El LFS de este equipo tiene
> `Game Admin admin` en `cfg.txt`:** su InSim solo acepta conexiones con esa contraseña (`--admin admin`).
> Antes, S26 (segundo equipo): siguiente fase elegida, el control de IA, en el repositorio aparte (privado,
> `AdrianPascarella/lfs-ai-control`, allí en `C:\Users\Adrian\Projects\lfs-ai-control`, con su propio
> protocolo; plan W1–W7 allí). Lo que le falte a la biblioteca entra en este `PLAN.md` como tarea.
> W11 en pausa: solo falta W11.6 (U14).
> Antes, S25 (equipo principal): **`lfs-insim` 0.8.0 publicada (S24)**: `InSim(udp_port=...)`
> (probado en real), notas de lo visto en LFS en los docstrings, docs de «Create new host». **W11.2 hecha (S24):** batería en vivo en `tests/live/`
> (`harness.py`: `Session` con `expect` / `check` / `screen` e informe con lo visto en cada sentido;
> `group_a.py`: secciones `requests setup race sends udp finish`, `--only`; `probe.py`, antes `tests/live_lfs.py`).
> Se lanza con `.venv/Scripts/python tests/live/group_a.py` con LFS en la pantalla de preparación de Un Jugador.
> **W11.3 hecha (S24):** grupo A en el LFS real (0.8C32, en ventana): pasada final 41 PASS + carrera extra 30 PASS,
> **0 paquetes mal leídos o mal escritos**; `COVERAGE.md` al día. **W11.8 y W11.9 hechas (S24), sin publicar
> («Unreleased»):** `InSim(udp_port=...)` (con `ISF.MCI`/`NLP` da `ValueError`) y notas de lo visto en el juego en
> los docstrings generados (`NOTES` de `spec_overrides.py`: `IS_AIC` quita el coche a la IA; `UVal` de
> `SSP`/`SSG` en centésimas). `generate_packets.py` va por 501 líneas (aviso de `verify`): lo siguiente que crezca
> ahí, partirlo. Lo que queda del grupo A necesita un coche en pista (W11.10).
> Antes, en S23: **W6 cerrada y `lfs-insim` 0.7.0 publicada** (W6.4, con
> permiso). 0.7.0 trae W6.1 y W6.5–W6.10: `request.IS_X()` / `request_all.IS_X()` / `instruct.IS_RIP(...)`,
> `unpack_insim` pública, enums de comentarios (`PTYPE`, `NCNF`, `SCHF`, `PLHF`, `RACING`, `WIND`, `OFFON`, `ACR`,
> `ISM`, `FLG`, `HLVC`, `REPLAY`) y `connect()` que llama a `on_connect`/`on_disconnect` (W6.10). **W6.3 hecha:**
> `FreeCam` en streamer-project (`tools/freecam`, su W9.1), probada en real, con 0.7.0 de PyPI fijada allí.
> **Avisos rojos de LFS** («sending to one but ReqI is not set»): salen al saltar hacia atrás en una MPR, también
> con un cliente mínimo propio; no los causa la biblioteca (LOG S23).
> **Fase activa: W11, pruebas intensivas contra el LFS real** (propuesta del usuario, plan aceptado en S23).
> W11.1 hecha: `docs/dev/COVERAGE.md` (estado de cada paquete y subtipo en real, por grupos A/R/E/H/P/G).
> **W11.4 (grupo E) hecha y W11.5 (grupo H) a medias (S24):** `group_e.py` y `group_h.py`; notas nuevas
> (`IS_TTC` y `PMO_GET_Z` necesitan `ReqI`). En LFS 0.8C32 «Crear servidor nuevo» deja al juego como invitado admin:
> lo de anfitrión necesita un servidor dedicado (W11.11).
> **W11.5 y W11.11 cerradas (S25):** el servidor de «Crear servidor nuevo» corre en el hosting de lfs.net, con su
> InSim (IP/puerto en «Your hosts», IP permitidas en «Access control»; **no pararlo: se borra**); `group_h.py
> --host --admin` 23 PASS. **W11.10 hecha (S25):** `group_d.py`, el usuario conduce (12 PASS). Docs en
> «Unreleased». **W11.7 hecha (S25):** `COVERAGE.md` 97 ✔ / 13 ◐ / 5 ✖, ningún fallo de la biblioteca; sin
> versión nueva (solo un docstring desde 0.8.0). En S25 quedaba decidir la próxima fase (hecho en S26; W11 sigue
> abierta solo por W11.6, el grupo P: tarjeta U14, cuando el usuario tenga a otra persona). Antes de lanzar LFS con opciones, copia de `cfg.txt` (§13). El
> permiso del grupo A (S23) vale para repetir `group_a.py`; sin tocar `cfg.txt`. LFS quedó cerrado al final de
> S24 (lo abrió el agente; `/exit` por InSim). Los demás grupos, cada uno con su permiso; el grupo P, en una tarjeta. La
> > biblioteca tiene la API de alto nivel (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`,
> `request` / `request_all` / `instruct`, `say()` / `command()`, `text.plain()`), plugins (`insim.use()`,
> `Plugin`, `Commands`, `Roster`, `insim.need()`, `reserve_click_ids()`, `on_close`) y
> `lfs_insim.testing.FakeLFS`. LFS acepta hasta 8 programas InSim a la vez (W10.0).
> **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez; con permiso, el agente lo aprueba
> por la API: `gh api -X POST .../actions/runs/<id>/pending_deployments -F "environment_ids[]=<id>" -f state=approved`,
> con `GH_TOKEN` de `AdrianPascarella`). Una versión publicada
> no se puede resubir. `_connection.py` va por 454 líneas (aviso de `verify` en 500): lo que crezca, en un
> módulo propio (los comandos, en `_commands.py`; las peticiones, en `_asking.py`). Ver `USER_ACTIONS.md`.

## Dónde estamos
Sin fase activa propia: W13 cerrada en S28 (0.9.0, pedida desde `lfs-ai-control`). Antes: W12 cerrada
en S27 (0.8.1). W11 en pausa por W11.6 (U14; tabla en `COVERAGE.md`). W6 cerrada en S23 y publicada como 0.7.0.

- **Cómo se genera:** `.venv/Scripts/python scripts/generate_packets.py` lee
  `spec/cache/InSim.txt` y `spec/cache/OutSimPack.txt` (con `scripts/spec_parser.py`) y las
  excepciones de `scripts/spec_overrides.py`, y escribe en `src/lfs_insim/packets/` `_enums.py`,
  `_insim.py`, `_outsim.py`, `_outgauge.py` y `__init__.py`, que van en git y no se editan a mano.
  `--check` sale con 1 si no están al día. Los enums los construye `scripts/generate_enums.py`.
  El núcleo escrito a mano es `packets/_codec.py` (los codecs de campo) y `packets/_structure.py`
  (`Structure`, `InSimPacket`, `register`, `unpack_insim`; separado en W8.0).
- **Si la generación se para con un error**, es a propósito: algo de la especificación no está
  cubierto. Se añade la entrada que pide en `spec_overrides.py`, nunca se salta.
- `OutSimPack.txt` solo existe en este equipo (P3). Sin él, el generador salta `_outsim.py` y
  `__init__.py` y comprueba el resto: así funciona en el workflow `spec`.
- **OutSimPack2** se lee con `OutSimPack2.unpack(data, opciones OSO)`; las partes no enviadas son
  `None` (LOG S5).
- **Texto:** `packets/_text.py` (páginas de códigos; D3 precisada en S7). `CName` y
  `IS_MAL.SkinID` no son texto: tienen sus propios codecs (`CarName`, `SkinID`; P6).
- **Verificación:** `.venv/Scripts/python scripts/verify.py`; el CI (workflow `verify`) ejecuta lo
  mismo en cada push. Sin `spec/cache/` (como en el CI), los tests que comparan con la
  especificación y el paso `generated` se saltan; el workflow `spec` descarga InSim.txt y hace esa
  comprobación.
- **API:** `docs/dev/API_DESIGN.md` (D1–D6; D3 precisada en S4: `TINY.NCN`, texto como `str`).

El proyecto anterior está en la rama `refactor/estabilizacion` y en las etiquetas `archivo/*`. Se
consulta, no se copia.

## Lo que te espera
1 pendiente → `USER_ACTIONS.md`: U15 (decidir: publicar 0.9.1 y W14.3); bloquea W14.2.

## Tests inestables (arreglados en S14)
`tests/test_every.py` fallaba a veces solo en el Windows del CI (3.12 y 3.13). Causa comprobada: en
Windows con Python anterior a 3.13, `time.monotonic()` avanza a saltos de ~15 ms, así que dos marcas
seguidas podían salir iguales. Los tests miden ahora con `time.perf_counter()` y margen de 2 ms. Si
vuelve a fallar en el CI, reabrir con el log delante.

## Restricciones ahora mismo
- En este equipo solo hay Python 3.14. Las demás versiones las comprueba el CI.
- El `python` de la terminal es el de streamer-project: aquí siempre `.venv/Scripts/python` (§13).
- `ruff format` y `ruff check --fix` solo sobre las rutas de `CHECKED_PATHS`, nunca sobre `scripts`
  entera (§13).
- El repositorio es público.
