# 🧪 Cobertura en el LFS real — AP_LFS_InSim (lfs_insim)
> Fase W11 (S23; grupos A, E y H probados en S24 con `tests/live/group_a.py`, `group_e.py` y `group_h.py`; el H como invitado admin (S24) y contra el InSim del propio servidor alojado en lfs.net (S25): en LFS 0.8C32 «Crear servidor nuevo» lo aloja en el servicio de hosting y el juego entra como invitado). Qué paquete se ha visto funcionar en el LFS real, cómo se provoca y qué falta. Se actualiza
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
| IS_ACR | ⬇ | ✔ | S24, S25 | A/H | en Un Jugador, cada comando; en el InSim del servidor, el de un invitado admin (`Result` 1, y 2 = rechazado con `/rstend` sin valor) y el del propio InSim (S25) |
| IS_AIC | ⬆ | ✔ | S24 | A | **le quita el coche a la IA** (cualquier `IS_AIC`, incluso `CS_SEND_AI_INFO`): sin acelerador frena; `CS_MSX` gira; `CS_STOP_CONTROL` la para y no devuelve el control (W11.9) |
| IS_AII | ⬇ | ✔ | S24 | A | por `SMALL_AII` (no quita el control) y por `CS_SEND_AI_INFO`; marcha, rpm, posición y velocidad con sentido |
| IS_AXI | ⬇ | ✔ | S12, S24 | E | `TINY_AXI`; `NumO` cuenta un cono añadido; un checkpoint de InSim (índice 252) no cuenta ni en `NumO` ni en `NumCP` (S24) |
| IS_AXM | ⬍ | ✔ | S24 | E | `PMO_ADD_OBJECTS` / `DEL_OBJECTS` / `CLEAR_ALL` (eco con `ISF_AXM_EDIT`), `TINY_AXM` con `FILE_END`, `PMO_SELECTION`, `PMO_TTC_SEL`; **`PMO_GET_Z` necesita `ReqI`** (sin él no contesta) |
| IS_AXO | ⬇ | ✖ | — | E | no salió al tocar un cono en una carrera normal (S24); falta en un autocross |
| IS_BFN | ⬍ | ✔ | S12, S24 | A | `CLEAR`; `DEL_BTN` de un rango (captura, S24); falta recibir `BFN` (el usuario pulsa Shift+I / Shift+B) |
| IS_BTC | ⬇ | ✔ | S12 | A | clic en un botón |
| IS_BTN | ⬆ | ✔ | S12, S24 | A | `Caption` y `TypeIn` (S12); estilos `LIGHT`, `DARK`, `LEFT`, `RIGHT`, `C1` (captura, S24); faltan `Inst` y botones de otra conexión |
| IS_BTT | ⬇ | ✔ | S12 | A | texto escrito en un botón (`TypeIn`) |
| IS_CCH | ⬇ | ◐ | S23, S24 | A/R | cambio de cámara; con `IS_SCH` «V» llegó una vez y otra no (la vista sí cambió, S24) |
| IS_CIM | ⬇ | ✔ | S12, S24 | A/E | Shift+U por `IS_SCH` → `SHIFTU` (6); la salida de la vista libre → `NORMAL` (S24) |
| IS_CNL | ⬇ | ◐ | S23 | R/P | alguien se va (en repetición, sus conexiones); falta con una persona real |
| IS_CON | ⬇ | ◐ | S12 | A | contacto entre coches (IA) |
| IS_CPP | ⬍ | ✔ | S12, S23 | A/R | `TINY_SCP`; enviado: cámara libre, movimiento suave, salir de ella (S23) |
| IS_CPR | ⬇ | ◐ | S23 | R/P | cambio de nombre |
| IS_CRS | ⬇ | ◐ | S23 | A | reiniciar el coche |
| IS_CSC | ⬇ | ✔ | S23, S24 | A | `CSC.START` de cada coche al salir (S24) |
| IS_FIN | ⬇ | ✔ | S12, S24 | A | `TTime` igual al de `IS_RES` (S24) |
| IS_FLG | ⬇ | ◐ | S12 | A | bandera azul / amarilla (IA lenta o parada) |
| IS_HCP | ⬆ | ◐ | S25 | H | enviado (XF GTI 20 kg, 5 %) y quitado, sin aviso; falta ver su efecto |
| IS_HLV | ⬇ | ◐ | S12 | A | salirse de pista, golpe contra muro (`ISF.HLV`) |
| IS_III | ⬇ | ✔ | S25 | H/P | un invitado escribe `/i hola` → `IS_III` (UCID 1, `Msg`) en el InSim del servidor |
| IS_IPB | ⬍ | ✔ | S25 | H | `TINY_IPB` y enviado (ban de 192.0.2.1, releído y quitado) en el InSim del servidor; como invitado admin, sin respuesta (S24) |
| IS_ISI | ⬆ | ✔ | todas | A | conectar (flags, `Interval`, prefijo, contraseña de admin) |
| IS_ISM | ⬇ | ✔ | S12, S19, S24, S25 | H/G | `Host` 1 en el InSim del servidor alojado (S25); `Host` 0 en el del juego, invitado admin (S24) |
| IS_JRR | ⬆ | ✖ | — | P | `ISF.REQ_JOIN`: aceptar o rechazar a alguien que quiere entrar |
| IS_LAP | ⬇ | ✔ | S12, S24 | A | `LTime` ~1:40 en BL1, `LapsDone` (S24; también la registra streamer-project, S21) |
| IS_MAL | ⬍ | ✔ | S12, S24, S25 | H | enviado como invitado admin (S24) y como anfitrión (S25): cambia la lista, releída y restaurada |
| IS_MCI | ⬇ | ✔ | S12, S18 | A | `ISF.MCI`; unidades de velocidad y posición comprobadas (S18) |
| IS_MOD | ⬆ | ✖ | — | A | cambiar resolución / ventana (cuidado: cambia la pantalla del usuario) |
| IS_MSL | ⬆ | ✔ | S12, S19 | A | vuelve como `IS_MSO`; solo lo ve este ordenador (S19) |
| IS_MSO | ⬇ | ✔ | S12, S19 | A/G | chat; `USER`, `O`, `PREFIX`; falta `ISF.MSO_COLS` |
| IS_MST | ⬆ | ✔ | S12, S18 | A | mensaje y comando (`/ai`, `/end`, `/mpr`) |
| IS_MSX | ⬆ | ✔ | S12 | A | mensaje largo |
| IS_MTC | ⬆ | ✔ | S18, S19, S24, S25 | H/P | desde el InSim del servidor: a todos (255, visto en el juego) y a una conexión (S25); como invitado, «only for multiplayer hosts» |
| IS_NCI | ⬇ | ✔ | S25 | H | `TINY_NCI` en un servidor alojado con contraseña de admin: `Language` 9, `License` 3, `UserID`; `IPAddress` 0 (el servidor tiene «Show IP addresses» en No) |
| IS_NCN | ⬇ | ✔ | S12, S19 | A/G | `TINY_NCN`; flags de remoto y admin (S19) |
| IS_NLP | ⬇ | ✔ | S12, S24 | A | `ISF.NLP` / `TINY_NLP`; vuelta y posición; ritmo de `SMALL_NLI` (S24) |
| IS_NPL | ⬇ | ✔ | S12, S23 | A/R | entra un coche; `PType` de IA, `CName` de mod (S12) |
| IS_OBH | ⬇ | ✔ | S24 | A/E | una IA golpea un cono añadido: `Index` 20, `LAYOUT \| CAN_MOVE \| ON_SPOT` (otra pasada no lo tocó) |
| IS_OCO | ⬆ | ◐ | S24 | A | semáforos de salida enviados sin error; falta ver el efecto (captura en el momento) |
| IS_PEN | ⬇ | ◐ | S23 | A | penalización dada o quitada |
| IS_PFL | ⬇ | ◐ | S23 | A | cambiar ayudas del jugador |
| IS_PIT | ⬇ | ◐ | S23 | A | parada en boxes |
| IS_PLA | ⬇ | ◐ | S21, S23, S24 | A | entrar o salir del pit lane (una IA tras la meta, S24) |
| IS_PLC | ⬆ | ◐ | S24, S25 | H | aceptado por el servidor (sin aviso) pero sin respuesta que comprobar; falta ver su efecto (un invitado elige coche) |
| IS_PLH | ⬍ | ✔ | S12, S25 | H | enviado a una IA (50 kg, 10 %) → `IS_PLH` de salida y `TINY_PLH` lo lee (S25) |
| IS_PLL | ⬇ | ◐ | S23 | A | un jugador se va a espectador |
| IS_PLP | ⬇ | ◐ | S23 | A | un jugador va a boxes (garaje) |
| IS_PSF | ⬇ | ◐ | S23 | A | termina una parada en boxes |
| IS_REO | ⬍ | ✔ | S12, S24 | A | enviado en la preparación, cambia la parrilla y `TINY_REO` lo devuelve (LFS tarda un momento en aplicarlo, S24) |
| IS_RES | ⬇ | ✔ | S12, S24 | A | al acabar cada coche y con `TINY_RES` (S24: sí responde en carrera) |
| IS_RIP | ⬍ | ✔ | S12, S21, S23 | R | cargar, saltar, pausa, errores; `ReqI = 0` lo ignora LFS (S23) |
| IS_RST | ⬇ | ✔ | S12, S24 | A | `RaceLaps`, `Track`, `NumNodes`, parciales; también con `TINY_RST` (S24). En Un Jugador `/restart` no arranca: hay que pulsar GO |
| IS_SCC | ⬆ | ✔ | S23 | A/R | coche y vista; no saca de la cámara libre (S23) |
| IS_SCH | ⬆ | ✔ | S24 | A | «V» cambia la vista (`IS_STA.InGameCam`); falta con SHIFT / CTRL |
| IS_SET | ⬇ | ✖ | — | H/P | `ISF.SET`: un invitado manda su setup (¿también el anfitrión? por ver) |
| IS_SFP | ⬆ | ✔ | S24 | A | ocultar y mostrar el 2D (`ISS.SHOW_2D` en `IS_STA`) |
| IS_SLC | ⬇ | ✔ | S25 | H | `TINY_SLC` en el InSim del servidor: `XFG` del host y vacío del invitado sin coche |
| IS_SMALL | ⬍ | ◐ | S12 | A | ver la tabla de `SMALL` |
| IS_SPX | ⬇ | ✔ | S12, S24 | A | paso por un parcial (`STime`, `Split`) |
| IS_SSH | ⬍ | ✔ | S24 | A | `instruct.IS_SSH(Name=...)` → `SSH.OK` y el archivo en `C:\LFS\data\shots` |
| IS_STA | ⬇ | ✔ | S12, S23 | A | `TINY_SST`; flags de estado (cámara libre, pausa) en S23 |
| IS_TINY | ⬍ | ◐ | varias | A | ver la tabla de `TINY` |
| IS_TOC | ⬇ | ◐ | S23 | R/P | alguien toma el coche de otro |
| IS_TTC | ⬆ | ✔ | S24 | E | ver la tabla de `TTC`; **todos necesitan `ReqI`** («IS_TTC with no ReqI») |
| IS_UCO | ⬇ | ✔ | S23, S24 | E/R | una IA cruza un checkpoint de InSim añadido: `CP_FWD`, `ObjectInfo` igual al enviado (S24) |
| IS_VER | ⬇ | ✔ | todas | A | respuesta al `IS_ISI` y a `TINY_VER` |
| IS_VTN | ⬇ | ◐ | S24 | A/P | también en Un Jugador al mandar `/end`; falta alguien que vote |

## Subtipos de `IS_TINY`, `IS_SMALL` e `IS_TTC`

| Subtipo | Sentido | Estado | Visto | Grupo | Cómo / qué falta |
|---|---|---|---|---|---|
| TINY_NONE | ⬍ | ✔ | S10, S17 | A | keepalive: LFS lo manda y se le devuelve |
| TINY_VER | ⬆ | ✔ | S12 | A | → `IS_VER` |
| TINY_CLOSE | ⬆ | ✔ | S9 | A | cerrar la conexión |
| TINY_PING / TINY_REPLY | ⬍ | ✔ | S12 | A | ping → `TINY_REPLY` |
| TINY_VTC | ⬍ | ◐ | S24 | A/P | llega tras `/end` en Un Jugador; falta cancelar una votación |
| TINY_SCP | ⬆ | ✔ | S12, S23 | A | → `IS_CPP` |
| TINY_SST | ⬆ | ✔ | S12, S23 | A | → `IS_STA` |
| TINY_GTM | ⬆ | ◐ | S12 | A | → `SMALL_RTP` |
| TINY_MPE | ⬇ | ✔ | S24 | H/G | `/leave` del servidor |
| TINY_ISM | ⬆ | ✔ | S19, S23 | H/G | → `IS_ISM` (en una MPR también contesta, S23) |
| TINY_REN | ⬇ | ✔ | S24 | A | `/end` |
| TINY_CLR | ⬇ | ✔ | S24 | A | `/clear` |
| TINY_NCN | ⬆ | ✔ | S12, S19 | A | → `IS_NCN` |
| TINY_NPL | ⬆ | ✔ | S12, S21 | A | → `IS_NPL` |
| TINY_RES | ⬆ | ✔ | S24 | A | → `IS_RES` en carrera (lo pendiente de S12) |
| TINY_NLP | ⬆ | ✔ | S12, S24 | A | → `IS_NLP` (en carrera) |
| TINY_MCI | ⬆ | ✔ | S23 | A/R | → `IS_MCI` (`request_all.IS_MCI`, S23) |
| TINY_REO | ⬆ | ✔ | S12, S24 | A | → `IS_REO` |
| TINY_RST | ⬆ | ✔ | S12, S24 | A | → `IS_RST` (en carrera) |
| TINY_AXI | ⬆ | ✔ | S12, S24 | E | → `IS_AXI` |
| TINY_AXC | ⬇ | ✔ | S24 | E | `IS_AXM` `PMO_CLEAR_ALL` |
| TINY_RIP | ⬆ | ✔ | S12, S23 | R | → `IS_RIP` |
| TINY_NCI | ⬆ | ✔ | S25 | H | → `IS_NCI` (servidor con contraseña de admin) |
| TINY_ALC | ⬆ | ◐ | S12 | A | → `SMALL_ALC` |
| TINY_AXM | ⬆ | ✔ | S12, S24 | E | → `IS_AXM` hasta `PMO_FILE_END` |
| TINY_SLC | ⬆ | ✔ | S25 | H | → `IS_SLC` de cada conexión |
| TINY_MAL | ⬆ | ◐ | S12 | H | → `IS_MAL` |
| TINY_PLH | ⬆ | ✔ | S12, S25 | H | → `IS_PLH` |
| TINY_IPB | ⬆ | ✔ | S25 | H | → `IS_IPB` en el InSim del servidor |
| TINY_LCL | ⬆ | ◐ | S12 | A | → `SMALL_LCL` |
| SMALL_SSP | ⬆ | ✔ | S24 | A | OutSim al `UDPPort` del `IS_ISI` (que `InSim()` no deja poner, W11.8); **`UVal` en centésimas** (10 → 10 por segundo); 0 lo para |
| SMALL_SSG | ⬆ | ✔ | S24 | A | OutGauge igual que `SSP`: `UDPPort`, `UVal` en centésimas, 0 lo para |
| SMALL_VTA | ⬇ | ◐ | S24 | A/P | llega tras `/end` en Un Jugador |
| SMALL_TMS | ⬆ | — | — | — | la especificación dice «currently unavailable» |
| SMALL_STP | ⬆ | — | — | — | la especificación dice «currently unavailable» |
| SMALL_RTP | ⬇ | ◐ | S12 | A | respuesta a `TINY_GTM` |
| SMALL_NLI | ⬆ | ✔ | S24 | A | 1000 ms → ~1 `IS_NLP` por segundo (tarda un momento en aplicarse) |
| SMALL_ALC | ⬍ | ✔ | S12, S24, S25 | A/H | enviado desde el InSim del servidor: aplicado, releído y restaurado (S25); como invitado admin, rechazado (S24) |
| SMALL_LCS | ⬆ | ✖ | — | A | luces, bocina, sirena del coche local |
| SMALL_LCL | ⬍ | ◐ | S12 | A | leído; falta poner luces |
| SMALL_AII | ⬆ | ✔ | S24 | A | → `IS_AII` de una IA, sin quitarle el control |
| TTC_SEL | ⬆ | ✔ | S24 | E | → `IS_AXM` `PMO_TTC_SEL` con la selección puesta por `PMO_SELECTION` |
| TTC_SEL_START / STOP | ⬆ | ✔ | S24 | E | `IS_AXM` al cambiar la selección (con el `ReqI` del START); STOP solo con `ReqI` |

## Fuera de InSim (UDP)

| Qué | Estado | Visto | Cómo / qué falta |
|---|---|---|---|
| OutGauge | ✔ | S12, S16, S24 | `cfg.txt` (con permiso y copia); por `SMALL_SSG` sin tocar `cfg.txt` (S24) |
| OutSim (`OutSimPack`) | ✔ | S12 | `cfg.txt`, Opts 0 |
| OutSim (`OutSimPack2`) | ✔ | S16 | `cfg.txt`, Opts con partes; falta por `SMALL_SSP` |
| InSim por UDP (`UDPPort` de `IS_ISI`) | ✖ | — | `IS_NLP` / `IS_MCI` por UDP (idea aparcada en `PLAN.md`) |
