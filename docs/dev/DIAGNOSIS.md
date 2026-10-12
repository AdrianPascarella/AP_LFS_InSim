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
### P1 — No hay comando de verificación   [ABIERTO]
- **Evidencia:** la rama `main` nació vacía en S1; no hay tests, ni lint, ni CI.
- **Impacto:** hasta que exista un comando que pueda fallar, las reglas de la red de seguridad
  (§5) no se pueden aplicar y cada cambio es una afirmación, no un resultado.
- **Acción:** W1.2 (comando de verificación) y W1.3 (CI con Python 3.11–3.14).

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
### P2 — Una copia fija de la especificación se queda desfasada   [ABIERTO: lo resuelve W1.4]
- **Evidencia:** `docs/InSim.txt` del proyecto anterior (copiado el 03/07) frente a
  https://www.lfs.net/programmer/insim el 12/10: 41 líneas distintas. Falta la versión 0.8C27, que
  añade la página de códigos de los mensajes (`MSOData` en `IS_MSO`) y el enum `LID_*`.
- **Impacto:** paquetes que no coinciden con lo que envía LFS, sin que nada avise.
- **Acción:** W1.4: descargar la especificación oficial con un script, apuntar en git la versión
  comprobada y avisar cuando lfs.net cambie.

### P3 — OutSimPack2 no se publica en la web   [ABIERTO]
- **Evidencia:** la página de InSim remite a `docs\OutSimPack.txt`, que solo viene con la
  instalación de LFS (`C:\LFS\docs\OutSimPack.txt`, fechado el 27/02/2021). No hay página en lfs.net.
- **Impacto:** el CI no puede descargar esa parte de la especificación; solo se puede comprobar en un
  equipo con LFS instalado.
- **Acción:** el código generado se guarda en git (así nadie necesita la especificación para
  instalar la biblioteca), y la comprobación contra `OutSimPack.txt` se hace solo donde exista ese
  archivo. Se decide en W1.4 / W2.

### P5 — Este equipo no tiene Python 3.11, 3.12 ni 3.13   [ABIERTO]
- **Evidencia:** `py -0p` en S1: solo 3.14 y un 3.9 antiguo.
- **Impacto:** código que use algo de 3.12 o posterior pasaría la verificación local y rompería a
  los usuarios de 3.11.
- **Acción:** el CI comprueba de 3.11 a 3.14 (W1.3), y ruff se configura con `target-version`
  3.11 para avisar en local de la sintaxis demasiado nueva.
