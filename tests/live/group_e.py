"""Live test, group E (W11.4): layout objects and the editor. Not collected by pytest.

    .venv/Scripts/python tests/live/group_e.py [--port 29999] [--only SECTION ...] [--laps 3]

Start as group A (single player race setup screen, InSim at 29999): the race with AI drivers is
set up the same way. Then, on the track where an AI car has just driven, the test adds a cone and
an InSim checkpoint with IS_AXM, so that the next car hits the cone (IS_OBH) and crosses the
checkpoint (IS_UCO). Sections, in order:

    requests  TINY_AXI / TINY_AXM with no layout
    setup     the race (group A's setup)
    objects   PMO_GET_Z, PMO_ADD_OBJECTS, read back with TINY_AXM / TINY_AXI; OBH, UCO, AXO
    editor    SHIFT+U (IS_SCH) -> IS_CIM; PMO_SELECTION and TTC_SEL / SEL_START / SEL_STOP
    clear     PMO_DEL_OBJECTS, PMO_CLEAR_ALL -> TINY_AXC; then /end and /clear

Object units are those of LFS's layout files (www.lfs.net/programmer/lyt): X, Y in 1/16 m,
Zbyte in 1/4 m, Heading = (degrees + 180) * 256 / 360.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from collections.abc import Callable

from group_a import GroupA
from harness import Session

from lfs_insim.packets import (
    BFN,
    CIM,
    IS_AXM,
    IS_AXO,
    IS_BFN,
    IS_CIM,
    IS_OBH,
    IS_SCH,
    IS_TINY,
    IS_TTC,
    IS_UCO,
    ISF,
    ISS,
    OBH,
    PMO,
    PMOF,
    SCHF,
    TINY,
    TTC,
    UCO,
    CompCar,
    ObjectInfo,
)

SECTIONS = ["requests", "setup", "objects", "editor", "clear"]
FLAGS = ISF.LOCAL | ISF.MCI | ISF.OBH | ISF.AXM_LOAD | ISF.AXM_EDIT
CONE = 20  # AXO_CONE1 in the layout file format
INSIM_CHECKPOINT = 252  # Flags bits 0-1: checkpoint index; bits 2-6: half width in metres
HALF_WIDTH = 10  # metres: wider than the track, so every car crosses it


def object_at(car: CompCar, index: int, flags: int = 0, zbyte: int = 0) -> ObjectInfo:
    """An object where a car is, facing the way it goes (MCI units to layout units)."""
    degrees = car.Heading * 360 / 65536
    return ObjectInfo(
        X=round(car.X / 65536 * 16),
        Y=round(car.Y / 65536 * 16),
        Zbyte=zbyte or max(0, min(255, round(car.Z / 65536 * 4))),
        Flags=flags,
        Index=index,
        Heading=round((degrees + 180) * 256 / 360) % 256,
    )


def subtype(sub: TINY) -> Callable[[IS_TINY], bool]:
    return lambda packet: packet.SubT == sub


def same_place(a: ObjectInfo, b: ObjectInfo) -> bool:
    return (a.X, a.Y, a.Index) == (b.X, b.Y, b.Index)


class GroupE:
    def __init__(self, s: Session, laps: int) -> None:
        self.s = s
        self.race = GroupA(s, laps)
        self.added: list[ObjectInfo] = []
        self.placed = 0  # mark: when the objects were added

    async def layout(self, reqi: int) -> list[ObjectInfo]:
        """Every object, with TINY_AXM (several IS_AXM, the last with PMO_FILE_END)."""
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=reqi, SubT=TINY.AXM))
        last = await self.s.expect(
            IS_AXM, lambda p: p.ReqI == reqi and bool(p.PMOFlags & PMOF.FILE_END), since=since
        )
        self.s.check(f"TINY_AXM -> IS_AXM ... FILE_END (ReqI {reqi})", last is not None)
        return [o for p in self.s.seen(IS_AXM, since) if p.ReqI == reqi for o in p.Info]

    async def requests(self) -> None:
        s = self.s
        axi = await s.insim.request.IS_AXI()
        s.check("TINY_AXI -> IS_AXI", True, f"NumO {axi.NumO}, NumCP {axi.NumCP}, {axi.LName!r}")
        objects = await self.layout(10)
        s.note(f"layout before the test: {len(objects)} objects")

    async def setup(self) -> None:
        await self.race.setup()

    async def objects(self) -> None:
        s = self.s
        if not self.race.racing:
            s.check("objects", None, "the race did not start")
            return
        await asyncio.sleep(20)  # the cars spread out a little
        cars = [c for mci in await s.insim.request_all.IS_MCI() for c in mci.Info]
        car = min(cars, key=lambda c: c.Position or 99)
        s.note(f"objects where PLID {car.PLID} is now (position {car.Position})")
        # PMO_GET_Z: the height of the ground there (Zbyte 240 = the highest point at X, Y).
        since = s.mark()
        probe = object_at(car, 0, zbyte=240)
        # S24: it needs a non-zero ReqI (with 0 there is no reply).
        s.insim.send(IS_AXM(ReqI=12, PMOAction=PMO.GET_Z, Info=[probe]))
        reply = await s.expect(IS_AXM, lambda p: p.ReqI == 12, since=since)
        zbyte = 0
        if reply is not None and reply.Info:
            zbyte = reply.Info[0].Zbyte
            s.check("PMO_GET_Z -> Zbyte", reply.Info[0].Flags == 0x80, f"Zbyte {zbyte}")
        else:
            s.check("PMO_GET_Z -> Zbyte", False, "no reply")
        cone = object_at(car, CONE, zbyte=zbyte)
        checkpoint = object_at(car, INSIM_CHECKPOINT, HALF_WIDTH << 2 | 1, zbyte)
        self.added = [cone, checkpoint]
        since = s.mark()
        self.placed = since
        s.insim.send(IS_AXM(PMOAction=PMO.ADD_OBJECTS, Info=self.added))
        echo = await s.expect(IS_AXM, lambda p: p.PMOAction == PMO.ADD_OBJECTS, since=since)
        s.check("IS_AXM PMO_ADD_OBJECTS -> IS_AXM back (ISF_AXM_EDIT)", True if echo else None)
        layout = await self.layout(11)
        for name, obj in (("cone", cone), ("InSim checkpoint", checkpoint)):
            s.check(f"TINY_AXM has the {name}", any(same_place(o, obj) for o in layout))
        axi = await s.insim.request.IS_AXI()
        # S24: NumO counts the cone; the InSim checkpoint is in neither NumO nor NumCP.
        s.check("IS_AXI counts the cone", axi.NumO >= 1, f"NumO {axi.NumO}, NumCP {axi.NumCP}")
        await s.screen()
        s.note("screenshot with the objects: tests/live_reports/screen.png")
        # The next cars come along the same line: up to a lap and a half.
        uco = await s.expect(IS_UCO, since=since, timeout=150)
        s.check(
            "a car crosses the InSim checkpoint -> IS_UCO",
            uco is not None,
            "" if uco is None else f"PLID {uco.PLID}, {UCO(uco.UCOAction).name}, {uco.Info}",
        )
        obh = s.seen(IS_OBH, since)
        hit = [p for p in obh if p.OBHFlags & OBH.LAYOUT]
        s.check(
            "a car hits the cone -> IS_OBH with OBH_LAYOUT",
            True if hit else None,
            f"{len(obh)} IS_OBH, {len(hit)} on layout objects"
            + (f"; first: Index {hit[0].Index}, {OBH(hit[0].OBHFlags)!r}" if hit else ""),
        )
        axo = s.seen(IS_AXO, since)
        s.check("IS_AXO (if LFS counts it as autocross)", True if axo else None, f"{len(axo)}")

    async def editor(self) -> None:
        s = self.s
        since = s.mark()
        s.insim.send(IS_SCH(CharB=ord("U"), Flags=SCHF.SHIFT))
        cim = await s.expect(IS_CIM, lambda p: p.Mode == CIM.SHIFTU, since=since)
        s.check("SHIFT+U (IS_SCH) -> IS_CIM SHIFTU", cim is not None, str(cim))
        if not self.added:
            s.check("editor selection", None, "no objects")
            return
        cone = self.added[0]
        s.insim.send(IS_AXM(PMOAction=PMO.SELECTION, PMOFlags=PMOF.SELECTION_REAL, Info=[cone]))
        await asyncio.sleep(0.5)
        since = s.mark()
        s.insim.send(IS_TTC(ReqI=20, SubT=TTC.SEL))
        sel = await s.expect(IS_AXM, lambda p: p.ReqI == 20, since=since)
        s.check(
            "PMO_SELECTION then TTC_SEL -> IS_AXM PMO_TTC_SEL with it",
            sel is not None and any(same_place(o, cone) for o in sel.Info),
            "" if sel is None else f"{PMO(sel.PMOAction).name}, {len(sel.Info)} objects",
        )
        s.insim.send(IS_TTC(ReqI=21, SubT=TTC.SEL_START))
        await asyncio.sleep(0.5)
        since = s.mark()
        s.insim.send(IS_AXM(PMOAction=PMO.SELECTION, PMOFlags=PMOF.SELECTION_REAL, Info=self.added))
        change = await s.expect(IS_AXM, lambda p: p.PMOAction == PMO.TTC_SEL, since=since)
        s.check(
            "TTC_SEL_START -> IS_AXM when the selection changes",
            change is not None,
            "" if change is None else f"{len(change.Info)} objects",
        )
        s.insim.send(IS_TTC(ReqI=22, SubT=TTC.SEL_STOP))  # S24: with ReqI 0, LFS ignores it
        await asyncio.sleep(0.5)
        since = s.mark()
        s.insim.send(IS_AXM(PMOAction=PMO.SELECTION, PMOFlags=PMOF.SELECTION_REAL, Info=[cone]))
        after = await s.expect(IS_AXM, lambda p: p.PMOAction == PMO.TTC_SEL, since=since, timeout=3)
        s.check("TTC_SEL_STOP -> no more", after is None)
        await s.screen()
        s.note("screenshot of free view with the selection: tests/live_reports/screen.png")
        s.insim.send(IS_AXM(PMOAction=PMO.SELECTION))  # nothing selected
        since = s.mark()
        s.insim.send(IS_SCH(CharB=ord("U"), Flags=SCHF.SHIFT))
        back = await s.expect(IS_CIM, lambda p: p.Mode != CIM.SHIFTU, since=since, timeout=5)
        # S24, twice: SHIFT+U sent by IS_SCH enters free view but does not leave it.
        s.check("SHIFT+U again -> IS_CIM out of free view", True if back else None, str(back))
        if back is None:  # S23: an IS_CPP without ISS.SHIFTU leaves free view
            cpp = await s.insim.request.IS_CPP()
            cpp.Flags &= ~ISS.SHIFTU
            since = s.mark()
            s.insim.send(cpp)
            back = await s.expect(IS_CIM, lambda p: p.Mode != CIM.SHIFTU, since=since, timeout=5)
            s.check("IS_CPP without SHIFTU -> IS_CIM out of free view", back is not None, str(back))

    async def clear(self) -> None:
        s = self.s
        if self.added:
            since = s.mark()
            s.insim.send(IS_AXM(PMOAction=PMO.DEL_OBJECTS, Info=self.added[:1]))
            echo = await s.expect(IS_AXM, lambda p: p.PMOAction == PMO.DEL_OBJECTS, since=since)
            s.check("IS_AXM PMO_DEL_OBJECTS -> IS_AXM back", True if echo else None)
            layout = await self.layout(30)
            s.check(
                "TINY_AXM: the cone is gone, the checkpoint is left",
                not any(same_place(o, self.added[0]) for o in layout)
                and any(same_place(o, self.added[1]) for o in layout),
                f"{len(layout)} objects",
            )
        since = s.mark()
        s.insim.send(IS_AXM(PMOAction=PMO.CLEAR_ALL))
        await s.expect_check(
            "PMO_CLEAR_ALL -> TINY_AXC", IS_TINY, lambda p: p.SubT == TINY.AXC, since=since
        )
        layout = await self.layout(31)
        s.check("TINY_AXM: no objects left", not layout, f"{len(layout)} objects")
        for command, sub in (("/end", TINY.REN), ("/clear", TINY.CLR)):
            since = s.mark()
            s.insim.command(command)
            await s.expect_check(
                f"{command} -> TINY_{sub.name}", IS_TINY, subtype(sub), since=since
            )


async def main_async(port: int, sections: list[str], laps: int) -> int:
    s = Session("E", port=port, flags=FLAGS, interval_ms=500)
    async with s:
        if not s.check("connected (IS_VER)", await s.connected()):
            return s.finish()
        test = GroupE(s, laps)
        name = ""
        try:
            for name in sections:
                print(f"== {name}", flush=True)
                await getattr(test, name)()
            s.insim.send(IS_BFN(SubT=BFN.CLEAR))
            await asyncio.sleep(0.5)
        except ConnectionError as error:  # LFS closed mid-run: keep what was seen
            s.check(f"connection kept until the end (in {name})", False, str(error))
    return s.finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=29999)
    parser.add_argument("--only", nargs="+", choices=SECTIONS, default=SECTIONS)
    parser.add_argument("--laps", type=int, default=3)
    args = parser.parse_args()
    sections = [name for name in SECTIONS if name in args.only]
    return asyncio.run(main_async(args.port, sections, args.laps))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
