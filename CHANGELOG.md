# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) y
el proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

## Convención de versionado

- Versiones `MAJOR.MINOR.PATCH` (semver).
- **Pre-1.0 (0.x):** la API todavía puede cambiar en versiones `MINOR`. El
  refactor de estabilización **rompió deliberadamente la API de los insims**
  (ver _Cambiado_) — aceptable en 0.x.
- **Fuente única de versión:** `lfs_insim.__version__` (`pyproject.toml` la lee
  de ahí con `dynamic`). Tras subir la versión, **reinstala en editable**
  (`pip install -e ".[dev]"`) para que la metadata instalada coincida; hay un
  test que lo verifica y falla si no.

---

## [Sin publicar] — v0.2.0 en preparación

> Primera versión pública del framework. Recoge la estabilización completa
> (rama `refactor/estabilizacion`): un core **componible**, robusto en runtime y
> empaquetable. Aún sin tag ni release — el merge a `main` y la publicación en
> PyPI quedan pendientes. Al cortarla, esta sección pasa a `## [0.2.0] - fecha`.

### Añadido

- **Reconexión automática** con backoff exponencial: si LFS cierra la conexión,
  el cliente reconecta solo, reenvía el ISI y re-solicita el estado
  (`TINY.NCN`/`NPL`). Hooks nuevos `on_disconnect()` y `on_reconnect()` para que
  las apps reseteen su estado por-sesión. Configurable con las claves
  `reconnect*`. Ante un ISI rechazado deja una pista en el log.
- **Política de errores de handlers** configurable (`handler_errors`): `'log'`
  (aísla y continúa, producción) o `'raise'` (fail-fast, desarrollo).
- **Cadencia de `on_tick` configurable** (`tick_interval`, default 0.1 s),
  desacoplada del sondeo interno del bucle principal (fijo a ≤100 ms).
- **Defaults del paquete** (`DEFAULT_CONFIG` + `build_config`): el core funciona
  como paquete instalado sin archivos de proyecto alrededor.
- **API pública explícita** (`__all__` por módulo) con puntos de import
  recomendados: `lfs_insim`, `lfs_insim.packets`, `lfs_insim.insim_enums`,
  `lfs_insim.utils`.
- **Subcomandos del CLI** `lfs-insim stubs` y `lfs-insim update-all` (antes eran
  scripts globales sueltos en el PATH).
- **Documentación de usuario** en `docs/guia/` (quickstart, módulos y
  dependencias, referencia de la API, arquitectura).
- **Tooling y CI:** adopción de `ruff` (lint + format) y `mypy` (gradual sobre el
  core); GitHub Actions con pytest en matriz (Python 3.9/3.11/3.13 + Windows),
  lint y typecheck.
- **Protocolo actualizado a LFS 0.8C5** (Fase 0): `ISP_SET`, `ISF_SET`,
  `RIFlags`/`RIF`/`SAI`, `CCI_RETIRED`, `NLP_MAX_CARS=48`, nuevos `HOSTF`.

### Cambiado

- **[Rompe la API]** `InSimApp` **ya no hereda de `InSimClient`** — el framework
  pasa a **composición**: un cliente y N apps registradas con
  `client.register(app)` (lo hace el loader). El **orden de dispatch es el de
  dependencias**: una dependencia procesa cada paquete antes que sus dependientes
  (antes era al revés — un bug latente).
- **El despacho de paquetes salió del hilo de IO**: los `on_ISP_*` corren en un
  worker dedicado en orden FIFO estricto; el keep-alive se contesta en el acto.
  Contrato de hilos documentado para autores de módulos.
- **Transporte encapsulado** (`InSimTransport`, sockets/hilos por instancia):
  varios clientes pueden coexistir en un proceso.
- **El envío es siempre TCP** (LFS solo recibe InSim por TCP; el socket UDP es
  solo de bajada).
- **Una sola ruta de serialización de strings**: `validate_string_lengths` es la
  única autoridad del layout; el decoder ya no hace `.strip()` (conserva los
  espacios significativos previos al null).
- **Metadata del paquete saneada:** `readme = "README.md"`, licencia SPDX
  (`MIT`), URLs corregidas, keywords y classifiers (Python 3.9–3.14), versión de
  fuente única.

### Obsoleto

- **`lfs_insim.insim_packet_class`** es ahora una _facade deprecada_ (emite
  `DeprecationWarning`) que re-exporta paquetes + enums como el monolito
  original. Usa `lfs_insim.packets` (paquetes) y `lfs_insim.insim_enums` (enums).

### Eliminado

- El patrón **"coup d'état" / módulo Master** y el aplanado `modules[]` (lo
  reemplaza la composición).
- **`insim_packet_io.py`** y el `send_packet` global (lo reemplaza
  `InSimTransport`).
- Claves de config **`use_thread_pool` / `max_workers`** (el dispatch por pool no
  garantizaba orden y no tenía usuarios).
- Parámetro **`use_udp`** de `transport.send`.
- Scripts globales **`generate-stubs` / `update-all`** (plegados en subcomandos de
  `lfs-insim`); `lfs-insim` es el único console-script.
- **`requirements.txt`** (redundante) y un enum **`INST`** duplicado.

### Corregido

- **Tormenta de reconexión** ante un ISI rechazado por LFS (admin password que no
  cuadra): la reconexión es ahora **provisional** — una sesión que muere antes de
  `reconnect_stable_time` mantiene el backoff escalando en vez de reiniciarlo.
- **Apagado limpio y determinista**: resuelta la carrera de `InSimTransport.close()`
  (join de receptores + reemplazo del evento de stop) y `InSimClient.stop()` con
  check-and-set atómico (un solo apagado ante paradas concurrentes).
- Orden de restauración de sesión al reconectar: ISI → `on_reconnect` →
  `TINY.NCN`/`NPL`, para que las respuestas nunca corran contra la limpieza de
  estado.
- Serialización de `ISP_REO`/`ISP_HCP`/`ISP_IPB` con secuencias de formato fijo
  (rellenaban mal y `struct.error` al enviar).
- Mitigación del congelamiento por **QuickEdit** de la consola de Windows (el
  handler de archivo va antes que el de consola; el CLI desactiva QuickEdit).
- **Compatibilidad con Python 3.9**: uniones PEP 604 (`X | Y`) en anotaciones
  evaluadas en runtime → `Union`/`Optional`; campo self-shadow `HLVC` en
  `ISP_HLV`.
- Dos errores type-only del core que los stubs `.pyi` enmascaraban.

---

> Antes de la v0.2.0 no hubo versiones publicadas ni tags: el proyecto se
> desarrolló sin releases. Esta es la primera entrada del changelog.
