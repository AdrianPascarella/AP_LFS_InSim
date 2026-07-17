# 📍 Estado actual

> Actualizado: **2026-07-17** — **S44**: **diseño del 8.6 CERRADO Y APROBADO** (sesión de diseño,
> sin código, como pedía S43). También se protegió el **remapeo de la zona S22** que había sin
> commitear (backup + `0140815` + push) y se re-basó el conteo de caracterización
> (lateral_links 40 → **43**). Suite **855/855**.
>
> **▶️ PRÓXIMO: IMPLEMENTAR el 8.6** — el diseño ya está cerrado en `PLAN.md § Fase 8, bloque 8.6`
> (léelo entero antes de tocar nada: es el contrato). **Red de tests primero**, como cada bloque.
> Al terminar → **ficha U nueva** de validación en LFS. Después: **8.7** migración de `test1` →
> **8.8** validación.
>
> **El diseño en una línea: DOS MECANISMOS ORTOGONALES que no se referencian jamás.** El **link**
> (`yield_type: NONE|YIELD|STOP` + **un** `yield_point`) gobierna al que hace la maniobra y vigila
> **todas las roads que su trazado pisa**; la **zona** (polígono ≥3 puntos + T + tabla de roads
> auto-poblada con el mismo toggle) gobierna al que **cruza de recto**. **`yield_zone_id`,
> `radius_m` y `priority_rules` se borran.** Detalle y por qué, en el PLAN.
>
> ⚠️ El diseño **se apartó bastante de lo que S43 recomendaba** (no hay matriz N×N, no hay modelo
> híbrido, la zona no gobierna links, `radius_m` no se rehabilita). El PLAN lo explica en "Qué
> cambió respecto a lo previsto" — no releas S43 como si siguiera vigente.
>
> ⚠️ Sigue siendo esperado que **en el juego no ceda nadie** hasta implementar el 8.6 y migrar
> `test1` (8.7).

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
  Solo quedaba abierta **W4** (ceda-el-paso en LFS), que se rehace en la Fase 8.
- **Fase 7 (robustez de conducción freeroam) COMPLETA Y VALIDADA** (código S34; **validada en LFS
  en S43**: U3–U7 todos OK). Cerrada.
- **Fase 8 (intersecciones) es la fase activa.** Bloques **8.1–8.5 hechos** (8.1/8.2 en S38, 8.3 en
  S39, 8.4 en S41, 8.5 en S42). El **8.6 (rediseño de la cesión)** tiene el **diseño cerrado y
  aprobado en S44** y espera implementación → 8.7 migración → 8.8 validación (checklist en
  `PLAN.md § Fase 8`), red de tests primero en cada bloque.
- ⚠️ **El 8.6 invalida parte de lo hecho en 8.1–8.5**, y es lo esperado, no una regresión: el
  modelo de datos cambia (`yield_line` polilínea → `yield_point`; `yield_zone_id`/`radius_m`/
  `priority_rules` fuera), así que el render del 8.5 y la UI del 8.4 se retocan al implementarlo.
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que te toca a ti

**0 acciones pendientes** → **[`ACCIONES_USUARIO.md`](ACCIONES_USUARIO.md)** (cola despejada en S43;
sigue a 0 tras S44). El próximo paso (implementar el 8.6) es código mío y **no te necesita**. Cuando
esté construido generará una **ficha U nueva** — validar la herramienta rediseñada en LFS. La
migración del 8.7 traerá otra: **regrabar `test1` como polígono** (su forma no se convierte sola).

## Bloqueos / restricciones ahora mismo

- **El diseño del 8.6 ya está aprobado (S44): se implementa, no se rediscute.** El contrato es
  `PLAN.md § Fase 8, bloque 8.6`. Si al implementar aparece algo que el diseño no previó, **parar y
  preguntar** en vez de improvisar una variante — el diseño costó una sesión entera de selector.
- La migración de `test1` (8.7) espera a que el 8.6 esté implementado.
- El **merge** espera a: Fase 8 hecha y validada + cola de `ACCIONES_USUARIO.md` despejada +
  pytest y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**855/855**; 838 de S41 + 17 del 8.5). El conteo
  de `south_city` en `test_map_persistencia.py` es de **caracterización**: se re-basa cuando el
  usuario amplía el mapa (S42 y S44) — que falle tras un remapeo es normal, no una regresión.
  Python 3.9 se verifica vía CI: `gh run list --branch refactor/estabilizacion`.
- Cierre de sesión: MODUS §2 — el último paso es `.venv\Scripts\python.exe scripts\close_check.py`
  (debe dar PASS) y pegar su salida.
- Presupuesto de lectura al arrancar: MODUS §1 (qué se lee entero, qué en parte y qué NO).
- La skill `ai-control-map-ui` ya documenta el patrón nuevo del 8.4 (sección por tipo en el
  detalle + sub-pantallas con fase en `current_recording`); usarla ANTES de abrir `map_ui.py`.
- Backlog offline sin fase (no bloquea el merge): desacople profundo de `base.py` (P4), tipado
  gradual, DX del connect fallido, splits post-merge de `map_ui`/`map_recorder` → `PLAN.md § Ideas`.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py` y
  `pip install -e ".[dev]"`.
