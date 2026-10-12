# 🧩 Diseño de la API pública — lfs_insim (W1.5)
> Escrito en S2. **D1–D4 aprobadas por el usuario en S2**; D5 y D6 propuestas sin objeción. Es la referencia de cómo se usa la
> biblioteca: el código de W2–W4 se escribe para que estos ejemplos funcionen tal cual. Cada
> decisión lleva su `D<n>` estable, la alternativa descartada y el porqué. Los ejemplos están en
> inglés porque así los verá el usuario de la biblioteca.

## Lo que se busca
Que un programa corto se lea de arriba abajo sin conocer la biblioteca por dentro, que el editor
autocomplete cada paquete y cada campo, y que un error en un manejador nunca tumbe a los demás.
La referencia es FastAPI (que el usuario citó): **una sola forma de hacer cada cosa**, funciones
decoradas, y `def` o `async def` según lo que necesite cada manejador.

## Ejemplo 1 — Lo mínimo: conectar, responder a un comando de chat
```python
from lfs_insim import InSim
from lfs_insim.packets import IS_MSO, IS_MST, IS_VER

insim = InSim(name="hello", admin_password="secret")   # host 127.0.0.1, port 29999 by default


@insim.on(IS_VER)
def connected(packet: IS_VER) -> None:
    print(f"Connected to LFS {packet.Version}, InSim {packet.InSimVer}")


@insim.on(IS_MSO)
def chat(packet: IS_MSO) -> None:
    if packet.text == "!hello":
        insim.send(IS_MST(Msg="/msg Hello from Python"))


insim.run()   # blocks until Ctrl+C; reconnects on its own if LFS restarts
```

## Ejemplo 2 — Saber quién es quién (estado opcional)
```python
from lfs_insim import InSim
from lfs_insim.packets import IS_NPL
from lfs_insim.state import Roster

insim = InSim(name="who")
roster = Roster(insim)          # opt-in: tracks NCN/CNL/CPR/NPL/PLL/PLP/TOC... and asks for the
                                # initial state (TINY.NCN, TINY.NPL) on every (re)connection


@insim.on(IS_NPL)
def joined(packet: IS_NPL) -> None:
    player = roster.players[packet.PLID]
    kind = "AI" if player.is_ai else "human"
    print(f"{player.name} ({kind}) joined the race, driven by {player.connection.username}")


insim.run()
```

## Ejemplo 3 — Ritmo fijo, `async` y OutGauge a la vez
```python
import asyncio

from lfs_insim import InSim, OutGauge, run
from lfs_insim.packets import IS_MCI, ISF, OutGaugePack   # packets and enums live together

insim = InSim(name="ai", flags=ISF.MCI | ISF.LOCAL, interval_ms=100)
gauge = OutGauge(port=30001)    # UDP; 30000 is already in use on this machine


@insim.every(0.1)                # replaces the old on_tick
async def drive() -> None:
    ...                          # send IS_AIC packets here


@insim.on(IS_MCI)
async def cars(packet: IS_MCI) -> None:
    await asyncio.sleep(0)       # async handlers may await without blocking the others


@gauge.on(OutGaugePack)
def dashboard(packet: OutGaugePack) -> None:
    print(packet.RPM)


run(insim, gauge)                # one process, one event loop, every source at once
```

## Decisiones propuestas
**D1 — Por dentro, asyncio; por fuera, `def` o `async def` a elección.** `insim.run()` arranca el
bucle de eventos, así que quien no sabe `async` nunca lo ve. Un manejador `def` se ejecuta en el
bucle (debe ser rápido); uno `async def` puede esperar. Para quien ya tiene su propio bucle (por
ejemplo, streamer-project): `await insim.connect()` / `async with insim:`.
*Descartado:* hilos como en el proyecto anterior (cola de envío, locks y un hilo de despacho:
mucho de su complejidad venía de ahí) y solo `async` (obliga a todos a aprenderlo para un «hola»).

**D2 — Manejadores con decorador y el tipo del paquete: `@insim.on(IS_MSO)`.** El editor sabe
que `packet` es un `IS_MSO` y autocompleta sus campos; mypy detecta un manejador mal tipado. Un
mismo paquete admite varios manejadores, y un error en uno se registra y no para los demás.
*Descartado:* subclase con métodos `on_mso` (lo del proyecto anterior: un nombre mal escrito se
ignora en silencio y no hay tipos) y cadenas como `"MSO"`.

**D3 — Los paquetes, con los nombres de la especificación**: `IS_MST(Msg=...)`, `packet.PLID`,
`ISF.LOCAL`, `TINY.NCN`. Son dataclasses generadas (W2); `Size`, `Type` y los ceros de relleno
los pone la biblioteca. *Por qué:* quien lee `InSim.txt`, el foro de LFS o un ejemplo en C
encuentra lo mismo, y la generación es mecánica. *Descartado:* `snake_case` (`req_i`, `plid`):
más PEP 8, pero cada nombre necesita una traducción que hay que recordar y documentar. Lo pitónico
va en la capa de arriba: `packet.text` (texto ya decodificado de la página de códigos de LFS),
`roster.players`, `insim.say("...")`.
*Precisado en S4 (aprobado por el usuario):* los enums y flags son clases con el prefijo de C como
nombre y el resto como miembro (`TINY.NCN`, `ISF.MCI`), no constantes sueltas (`TINY_NCN`): el
editor los agrupa y mypy distingue un `TINY` de un `SMALL`. Los valores que no son identificadores
válidos (`DL_18`) reciben un nombre fijado en las excepciones de W2. Los campos de texto son `str`.
*Precisado en S6 (decidido por el usuario):* `CName` es un `str`: el coche oficial (`"XFG"`), el
SkinID de un mod en hexadecimal (`"5A1FB3"`), tal como lo enseñan LFS y lfs.net, o `""` si no hay
coche. `IS_MAL.SkinID` es una lista de `str` con el mismo formato, para que funcione
`npl.CName in mal.SkinID`. *Descartado:* `str` o `int` según el coche (obliga a usar `isinstance`)
y los bytes crudos (cada aplicación los interpretaría).

*Precisado en S7 (aprobado por el usuario):* en el `str` del texto no están los cambios de página
(`^L`, `^J`…), que se quitan al leer y se añaden al enviar; los demás códigos `^` (colores,
`^^`, `^v`…) se quedan tal cual. `lfs_insim.text.strip_colours()` quita los colores (amplía D6).
*Precisado en S8 (decidido por el usuario, U3 y U4):* `IS_BTN.Caption` es el título del cuadro de
texto (la biblioteca pone los ceros), e `IS_MSO.TextStart` es un índice en `Msg`, no bytes:
`mso.Msg[mso.TextStart:]` es lo que escribió el usuario.

**D4 — El estado de conexiones y jugadores, en la biblioteca y opcional (`Roster`).** Casi todas
las aplicaciones lo necesitan (la gestión de usuarios, el registrador, la IA) y es fácil hacerlo
mal (reconexiones, cambios de nombre, IA sin conexión propia). Quien no lo crea no paga nada.

**D5 — OutSim y OutGauge, con la misma forma** (`OutGauge(port=...)`, `@gauge.on(...)`) y
`run(...)` para varios a la vez. *Descartado:* meterlos dentro de `InSim` (en el proyecto anterior
venían mezclados; son protocolos UDP independientes y muchos programas solo usan uno).

**D6 — Una superficie pequeña.** Lo público es `InSim`, `OutSim`, `OutGauge`, `run`,
`lfs_insim.packets`, `lfs_insim.state` y las excepciones. Todo lo demás lleva `_` y puede cambiar
sin aviso. *Por qué:* P4; una API pequeña se puede revisar entera.

## Abierto (se decide más adelante, no ahora)
- Comandos de chat (`!hello`): ¿un ayudante en la biblioteca (`@insim.command("hello")`) o solo
  `IS_MSO`? Se decide en W4, cuando se escriba el ejemplo de botones.
- Agrupar manejadores en módulos (lo que hacía `InSimApp` con varias aplicaciones a la vez): si
  hiciera falta, algo como el `APIRouter` de FastAPI. Solo si una aplicación real lo pide.
