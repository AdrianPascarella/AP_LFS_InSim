# 🧪 Cobertura en el LFS real — AP_LFS_InSim (lfs_insim)
> Fase W11 (S23). Qué paquete se ha visto funcionar en el LFS real, cómo se provoca y qué falta. Se actualiza
> al probar cada grupo; el detalle de cada prueba, en `LOG.md` (la sesión de la columna «Visto»).

**Estado** (lo más fuerte que se ha comprobado de cada uno):
- ✔ **comprobado**: se miraron sus valores (texto, unidades, flags) o su efecto en LFS (captura, respuesta).
- ◐ **leído**: llegó (o se envió) sin error de lectura, o salió igual al reescribirlo (S12), pero nadie miró sus
  valores.
- ✖ **nunca** en real. **—** LFS no lo manda ni lo acepta en ese sentido.

**Sentido:** ⬇ LFS lo manda, ⬆ lo mandamos, ⬍ los dos (de `InSim.txt`: info / instruction / both ways).

**Grupo** (lo que hace falta para provocarlo):
- **A** — tu LFS en Un Jugador, con IA. Lo puede hacer el agente solo, con permiso.
- **R** — tu LFS con una repetición.
- **E** — tu LFS en el editor de circuitos (layout / autocross).
- **H** — tu LFS como servidor (multijugador, aunque no entre nadie; algunos con contraseña de admin).
- **P** — otra persona conectada (tarjeta para el usuario).
- **G** — tu LFS como invitado en un servidor ajeno.

## Paquetes

| Paquete | Sentido | Estado | Visto | Grupo | Cómo se provoca / qué falta |
|---|---|---|---|---|---|
| IS_ACR | ⬇ | ✖ | — | H | alguien escribe un comando de admin en el servidor |
| IS_AIC | ⬆ | ✖ | — | A | mandar entradas a una IA (dirección, acelerador); ver que la obedece |
| IS_AII | ⬇ | ✖ | — | A | `SMALL_AII` a una IA local, o `AIC` con petición de info |
| IS_AXI | ⬇ | ◐ | S12 | E | `TINY_AXI`; falta con un layout cargado |
| IS_AXM | ⬍ | ◐ | S12 | E | `TINY_AXM` sin layout; falta añadir/quitar objetos y leerlos |
| IS_AXO | ⬇ | ✖ | — | E | un coche toca un objeto de autocross |
| IS_BFN | ⬍ | ◐ | S12 | A | `BFN.CLEAR` enviado; falta `DEL_BTN`, y recibir `BFN` (el usuario pulsa Shift+I / Shift+B) |
| IS_BTC | ⬇ | ✔ | S12 | A | clic en un botón |
| IS_BTN | ⬆ | ✔ | S12 | A | botón con `Caption` y `TypeIn`; faltan estilos, `Inst` y botones de otra conexión |
| IS_BTT | ⬇ | ✔ | S12 | A | texto escrito en un botón (`TypeIn`) |
| IS_CCH | ⬇ | ◐ | S23 | A/R | cambio de cámara |
| IS_CIM | ⬇ | ◐ | S12 | A/E | cambio de modo de la interfaz (garaje, Shift+U, editor…) |
| IS_CNL | ⬇ | ◐ | S23 | R/P | alguien se va (en repetición, sus conexiones); falta con una persona real |
| IS_CON | ⬇ | ◐ | S12 | A | contacto entre coches (IA) |
| IS_CPP | ⬍ | ✔ | S12, S23 | A/R | `TINY_SCP`; enviado: cámara libre, movimiento suave, salir de ella (S23) |
| IS_CPR | ⬇ | ◐ | S23 | R/P | cambio de nombre |
| IS_CRS | ⬇ | ◐ | S23 | A | reiniciar el coche |
| IS_CSC | ⬇ | ◐ | S23 | A | arranca o para un coche (`CSC.START` / `STOP`) |
| IS_FIN | ⬇ | ◐ | S12 | A | cruzar la meta al acabar la carrera |
| IS_FLG | ⬇ | ◐ | S12 | A | bandera azul / amarilla (IA lenta o parada) |
| IS_HCP | ⬆ | ✖ | — | H | handicaps por coche; ver `IS_PLH` o el efecto |
| IS_HLV | ⬇ | ◐ | S12 | A | salirse de pista, golpe contra muro (`ISF.HLV`) |
| IS_III | ⬇ | ✖ | — | H/P | alguien escribe `/i texto` al InSim del servidor |
| IS_IPB | ⬍ | ✖ | — | H | `TINY_IPB` («only for multiplayer hosts» en S12); poner y leer bans |
| IS_ISI | ⬆ | ✔ | todas | A | conectar (flags, `Interval`, prefijo, contraseña de admin) |
| IS_ISM | ⬇ | ✔ | S12, S19 | H/G | `TINY_ISM`; como invitado (S19); falta al empezar un servidor propio |
| IS_JRR | ⬆ | ✖ | — | P | `ISF.REQ_JOIN`: aceptar o rechazar a alguien que quiere entrar |
| IS_LAP | ⬇ | ◐ | S12 | A | completar una vuelta (también la registra streamer-project, S21) |
| IS_MAL | ⬍ | ◐ | S12 | H | `TINY_MAL`; falta enviar una lista y ver el efecto |
| IS_MCI | ⬇ | ✔ | S12, S18 | A | `ISF.MCI`; unidades de velocidad y posición comprobadas (S18) |
| IS_MOD | ⬆ | ✖ | — | A | cambiar resolución / ventana (cuidado: cambia la pantalla del usuario) |
| IS_MSL | ⬆ | ✔ | S12, S19 | A | vuelve como `IS_MSO`; solo lo ve este ordenador (S19) |
| IS_MSO | ⬇ | ✔ | S12, S19 | A/G | chat; `USER`, `O`, `PREFIX`; falta `ISF.MSO_COLS` |
| IS_MST | ⬆ | ✔ | S12, S18 | A | mensaje y comando (`/ai`, `/end`, `/mpr`) |
| IS_MSX | ⬆ | ✔ | S12 | A | mensaje largo |
| IS_MTC | ⬆ | ◐ | S18, S19 | H/P | como invitado LFS lo rechaza (S18, S19); falta como servidor, a una persona y a un jugador |
| IS_NCI | ⬇ | ✖ | — | H | `TINY_NCI` en un servidor con contraseña de admin |
| IS_NCN | ⬇ | ✔ | S12, S19 | A/G | `TINY_NCN`; flags de remoto y admin (S19) |
| IS_NLP | ⬇ | ◐ | S12 | A | `ISF.NLP` / `TINY_NLP` en carrera |
| IS_NPL | ⬇ | ✔ | S12, S23 | A/R | entra un coche; `PType` de IA, `CName` de mod (S12) |
| IS_OBH | ⬇ | ✖ | — | A/E | `ISF.OBH`: un coche golpea un objeto |
| IS_OCO | ⬆ | ✖ | — | A | semáforos de salida (Object COntrol); ver el efecto |
| IS_PEN | ⬇ | ◐ | S23 | A | penalización dada o quitada |
| IS_PFL | ⬇ | ◐ | S23 | A | cambiar ayudas del jugador |
| IS_PIT | ⬇ | ◐ | S23 | A | parada en boxes |
| IS_PLA | ⬇ | ◐ | S21, S23 | A | entrar o salir del pit lane |
| IS_PLC | ⬆ | ✖ | — | H | coches permitidos a una conexión |
| IS_PLH | ⬍ | ◐ | S12 | H | `TINY_PLH`; falta enviar handicaps y leerlos |
| IS_PLL | ⬇ | ◐ | S23 | A | un jugador se va a espectador |
| IS_PLP | ⬇ | ◐ | S23 | A | un jugador va a boxes (garaje) |
| IS_PSF | ⬇ | ◐ | S23 | A | termina una parada en boxes |
| IS_REO | ⬍ | ◐ | S12 | A | `TINY_REO`; falta enviar un orden de salida y verlo |
| IS_RES | ⬇ | ◐ | S12 | A | resultado; `TINY_RES` no respondió en S12 (pendiente de mirar) |
| IS_RIP | ⬍ | ✔ | S12, S21, S23 | R | cargar, saltar, pausa, errores; `ReqI = 0` lo ignora LFS (S23) |
| IS_RST | ⬇ | ◐ | S12 | A | empieza la carrera / `TINY_RST` |
| IS_SCC | ⬆ | ✔ | S23 | A/R | coche y vista; no saca de la cámara libre (S23) |
| IS_SCH | ⬆ | ✖ | — | A | pulsar una tecla en LFS (con SHIFT / CTRL) |
| IS_SET | ⬇ | ✖ | — | H/P | `ISF.SET`: un invitado manda su setup (¿también el anfitrión? por ver) |
| IS_SFP | ⬆ | ✖ | — | A | cambiar flags de estado (p. ej. ocultar el 2D); ver `IS_STA` |
| IS_SLC | ⬇ | ✖ | — | H | `TINY_SLC` («only for multiplayer hosts» en S12) / elegir coche |
| IS_SMALL | ⬍ | ◐ | S12 | A | ver la tabla de `SMALL` |
| IS_SPX | ⬇ | ◐ | S12 | A | paso por un parcial |
| IS_SSH | ⬍ | ✖ | — | A | `instruct.IS_SSH(Name=...)`; ver el archivo en `C:\LFS\data\shots` |
| IS_STA | ⬇ | ✔ | S12, S23 | A | `TINY_SST`; flags de estado (cámara libre, pausa) en S23 |
| IS_TINY | ⬍ | ◐ | varias | A | ver la tabla de `TINY` |
| IS_TOC | ⬇ | ◐ | S23 | R/P | alguien toma el coche de otro |
| IS_TTC | ⬆ | ✖ | — | E | ver la tabla de `TTC` |
| IS_UCO | ⬇ | ◐ | S23 | E/R | un coche cruza un control InSim (checkpoint / círculo) |
| IS_VER | ⬇ | ✔ | todas | A | respuesta al `IS_ISI` y a `TINY_VER` |
| IS_VTN | ⬇ | ✖ | — | P | alguien vota (reiniciar, terminar…) |

## Subtipos de `IS_TINY`, `IS_SMALL` e `IS_TTC`

| Subtipo | Sentido | Estado | Visto | Grupo | Cómo / qué falta |
|---|---|---|---|---|---|
| TINY_NONE | ⬍ | ✔ | S10, S17 | A | keepalive: LFS lo manda y se le devuelve |
| TINY_VER | ⬆ | ✔ | S12 | A | → `IS_VER` |
| TINY_CLOSE | ⬆ | ✔ | S9 | A | cerrar la conexión |
| TINY_PING / TINY_REPLY | ⬍ | ✔ | S12 | A | ping → `TINY_REPLY` |
| TINY_VTC | ⬍ | ✖ | — | P | cancelar una votación / LFS avisa |
| TINY_SCP | ⬆ | ✔ | S12, S23 | A | → `IS_CPP` |
| TINY_SST | ⬆ | ✔ | S12, S23 | A | → `IS_STA` |
| TINY_GTM | ⬆ | ◐ | S12 | A | → `SMALL_RTP` |
| TINY_MPE | ⬇ | ✖ | — | H/G | salir de un multijugador |
| TINY_ISM | ⬆ | ✔ | S19, S23 | H/G | → `IS_ISM` (en una MPR también contesta, S23) |
| TINY_REN | ⬇ | ✖ | — | A | terminar la carrera y volver a la pantalla de preparación |
| TINY_CLR | ⬇ | ✖ | — | A | quitar a todos de la carrera |
| TINY_NCN | ⬆ | ✔ | S12, S19 | A | → `IS_NCN` |
| TINY_NPL | ⬆ | ✔ | S12, S21 | A | → `IS_NPL` |
| TINY_RES | ⬆ | ✖ | — | A | no respondió en S12, ni en carrera: **pendiente** |
| TINY_NLP | ⬆ | ◐ | S12 | A | → `IS_NLP` (en carrera) |
| TINY_MCI | ⬆ | ✔ | S23 | A/R | → `IS_MCI` (`request_all.IS_MCI`, S23) |
| TINY_REO | ⬆ | ◐ | S12 | A | → `IS_REO` |
| TINY_RST | ⬆ | ◐ | S12 | A | → `IS_RST` (en carrera) |
| TINY_AXI | ⬆ | ◐ | S12 | E | → `IS_AXI` |
| TINY_AXC | ⬇ | ✖ | — | E | se borra el layout |
| TINY_RIP | ⬆ | ✔ | S12, S23 | R | → `IS_RIP` |
| TINY_NCI | ⬆ | ✖ | — | H | → `IS_NCI` (servidor con contraseña) |
| TINY_ALC | ⬆ | ◐ | S12 | A | → `SMALL_ALC` |
| TINY_AXM | ⬆ | ◐ | S12 | E | → `IS_AXM` |
| TINY_SLC | ⬆ | ✖ | — | H | → `IS_SLC` |
| TINY_MAL | ⬆ | ◐ | S12 | H | → `IS_MAL` |
| TINY_PLH | ⬆ | ◐ | S12 | H | → `IS_PLH` |
| TINY_IPB | ⬆ | ✖ | — | H | → `IS_IPB` |
| TINY_LCL | ⬆ | ◐ | S12 | A | → `SMALL_LCL` |
| SMALL_SSP | ⬆ | ✖ | — | A | empezar a mandar OutSim (sin tocar `cfg.txt`) |
| SMALL_SSG | ⬆ | ✖ | — | A | empezar a mandar OutGauge (sin tocar `cfg.txt`) |
| SMALL_VTA | ⬇ | ✖ | — | P | se ejecuta una votación |
| SMALL_TMS | ⬆ | ✖ | — | A | parar el tiempo |
| SMALL_STP | ⬆ | ✖ | — | A | avanzar el tiempo paso a paso |
| SMALL_RTP | ⬇ | ◐ | S12 | A | respuesta a `TINY_GTM` |
| SMALL_NLI | ⬆ | ✖ | — | A | intervalo de `IS_NLP`/`IS_MCI` por nodos |
| SMALL_ALC | ⬍ | ◐ | S12 | A/H | leído; falta poner coches permitidos |
| SMALL_LCS | ⬆ | ✖ | — | A | luces, bocina, sirena del coche local |
| SMALL_LCL | ⬍ | ◐ | S12 | A | leído; falta poner luces |
| SMALL_AII | ⬆ | ✖ | — | A | → `IS_AII` de una IA local |
| TTC_SEL | ⬆ | ✖ | — | E | → `IS_AXM` de la selección del editor |
| TTC_SEL_START / STOP | ⬆ | ✖ | — | E | `IS_AXM` cada vez que cambia la selección / dejar de mandarlos |

## Fuera de InSim (UDP)

| Qué | Estado | Visto | Cómo / qué falta |
|---|---|---|---|
| OutGauge | ✔ | S12, S16 | `cfg.txt` (con permiso y copia); falta por `SMALL_SSG`, sin tocar `cfg.txt` |
| OutSim (`OutSimPack`) | ✔ | S12 | `cfg.txt`, Opts 0 |
| OutSim (`OutSimPack2`) | ✔ | S16 | `cfg.txt`, Opts con partes; falta por `SMALL_SSP` |
| InSim por UDP (`UDPPort` de `IS_ISI`) | ✖ | — | `IS_NLP` / `IS_MCI` por UDP (idea aparcada en `PLAN.md`) |
