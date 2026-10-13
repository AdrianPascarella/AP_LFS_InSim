"""The examples in examples/ (W4.6), each one run against the fake LFS as a user would use it."""

import asyncio
import importlib.util
import socket
import sys
from pathlib import Path
from types import ModuleType

import pytest

from lfs_insim import InSim
from lfs_insim.packets import (
    BFN,
    IS_BFN,
    IS_BTC,
    IS_BTN,
    IS_BTT,
    IS_MSL,
    IS_MSO,
    IS_MTC,
    IS_NCN,
    IS_NPL,
    IS_PLL,
    IS_STA,
    MSO,
    TINY,
    OutGaugePack,
)
from lfs_insim.state import Roster
from lfs_insim.testing import FakeLFS

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def load(name: str) -> ModuleType:
    """Import an example afresh, without running its `if __name__ == "__main__"` part."""
    spec = importlib.util.spec_from_file_location(f"example_{name}", EXAMPLES / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def typed(text: str, ucid: int = 0) -> IS_MSO:
    name = "Driver : "
    return IS_MSO(UCID=ucid, UserType=MSO.PREFIX, TextStart=len(name), Msg=name + text)


async def _until(condition: object, timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():  # type: ignore[operator]
            await asyncio.sleep(0.01)


def test_every_example_is_tested() -> None:
    tested = {"hello", "who", "gauge", "buttons", "together"}
    assert {path.stem for path in EXAMPLES.glob("*.py")} == tested


def test_hello(capsys: pytest.CaptureFixture[str]) -> None:
    insim = InSim(prefix="!")
    insim.use(load("hello").hello)

    async def main() -> None:
        async with FakeLFS() as lfs:
            insim.port = lfs.port
            async with insim:
                await lfs.wait_connected()
                await lfs.send(typed("!hello", ucid=4))
                reply = await lfs.wait_for(IS_MTC)
        assert (reply.UCID, reply.Text) == (4, "Hello from Python")

    asyncio.run(main())
    assert "Connected to LFS 0.8C31, InSim 10" in capsys.readouterr().out


def test_who(capsys: pytest.CaptureFixture[str]) -> None:
    insim = InSim(prefix="!")
    insim.use(load("who").who)
    roster = insim.use(Roster)  # the plugin's own

    async def main() -> None:
        async with FakeLFS() as lfs:
            lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, Total=2), IS_NCN(UCID=2, UName="bob", Total=2)]
            lfs.replies[TINY.NPL] = [
                IS_NPL(PLID=1, UCID=2, PName="^1^h1 Bob", CName="XFG", NumP=2),
                IS_NPL(PLID=2, UCID=0, PType=2, PName="AI 1", CName="FBM", NumP=2),
            ]
            insim.port = lfs.port
            async with insim:
                await lfs.wait_connected()
                await _until(lambda: len(roster.players) == 2)
                await lfs.send(typed("!who"))
                replies = [(await lfs.wait_for(IS_MSL)).Msg for _ in range(2)]
                await lfs.send(IS_PLL(PLID=1))
                await _until(lambda: 1 not in roster.players)
        assert replies == ["^1^h1 Bob^8: XFG", "AI 1^8: FBM (AI)"]

    asyncio.run(main())
    out = capsys.readouterr().out
    assert "#1 Bob (human, XFG) is on track, from bob" in out  # plain(): ^h is #
    assert "AI 1 (AI, FBM) is on track, from this computer" in out
    assert "#1 Bob left the race" in out


def test_gauge() -> None:
    example = load("gauge")
    example.gauge.port = 0  # any free port
    example.insim._every = [(0.05, handler) for _, handler in example.insim._every]  # not 2 s

    async def main() -> None:
        async with FakeLFS() as lfs:
            lfs.replies[TINY.SST] = [IS_STA(NumP=3)]
            example.insim.port = lfs.port
            async with example.gauge, example.insim:
                await lfs.wait_connected()
                first = await lfs.wait_for(IS_MSL)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    data = OutGaugePack(Speed=25.0, RPM=4321.0).pack()
                    sock.sendto(data, ("127.0.0.1", example.gauge.port))
                await _until(lambda: example.latest is not None)
                while "km/h" not in (message := await lfs.wait_for(IS_MSL)).Msg:
                    pass
        assert first.Msg == "No OutGauge data yet: is a car on track? (3 in the race)"
        assert message.Msg == "90 km/h at 4321 rpm (3 in the race)"

    asyncio.run(main())


def test_buttons() -> None:
    insim = InSim(prefix="!")
    insim.reserve_click_ids(5)  # another plugin's: the example's buttons come after them
    insim.use(load("buttons").buttons)

    async def main() -> None:
        async with FakeLFS() as lfs:
            insim.port = lfs.port
            async with insim:
                await lfs.wait_connected()
                await lfs.send(typed("!buttons"))
                click_me, type_here = await lfs.wait_for(IS_BTN), await lfs.wait_for(IS_BTN)
                assert (click_me.ClickID, type_here.ClickID) == (5, 6)
                await lfs.send(IS_BTC(ReqI=1, ClickID=click_me.ClickID))
                updated = await lfs.wait_for(IS_BTN)
                await lfs.wait_for(IS_BTN)
                await lfs.send(IS_BTT(ReqI=1, ClickID=type_here.ClickID, Text="hola"))
                answer = await lfs.wait_for(IS_MSL)  # UCID 0: this computer
                await lfs.send(typed("!hide"))
                hidden = await lfs.wait_for(IS_BFN)
        assert click_me.ReqI and click_me.Text == "Clicked 0 times"
        assert (type_here.TypeIn, type_here.Caption) == (20, "Your text")
        assert updated.Text == "Clicked 1 times"
        assert answer.Msg == "You typed: hola"
        assert (hidden.SubT, hidden.ClickID, hidden.ClickMax) == (BFN.DEL_BTN, 5, 6)  # its own only

    asyncio.run(main())


def test_together(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(EXAMPLES))  # it imports hello, who and buttons, next to it
    for name in ("hello", "who", "buttons"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    example = load("together")

    async def main() -> None:
        async with FakeLFS() as lfs:
            lfs.replies[TINY.NCN] = [IS_NCN(UCID=0, Total=1)]
            example.insim.port = lfs.port
            async with example.insim:
                await lfs.wait_connected()
                await lfs.send(typed("!hello"))
                hello = await lfs.wait_for(IS_MSL)
                await lfs.send(typed("!who"))
                who = await lfs.wait_for(IS_MSL)
                await lfs.send(typed("!buttons"))
                button = await lfs.wait_for(IS_BTN)
        assert (hello.Msg, who.Msg, button.ClickID) == (
            "Hello from Python",
            "Nobody is in the race",
            0,
        )
        asked = [p for p in lfs.received if getattr(p, "SubT", None) == TINY.NCN]
        assert len(asked) == 1  # one Roster for the three

    asyncio.run(main())
