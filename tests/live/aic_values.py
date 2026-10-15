"""Live test of the IS_AIC value names (W12.2). Not collected by pytest: it needs the game.

    .venv/Scripts/python tests/live/aic_values.py [--port 29999] [--admin PASSWORD]

Start as for group_a.py: LFS in the single player race setup screen, InSim on the port. The race
is set up as group_a.py does (two AI drivers, GO), then an IS_AIC takes the first AI car on the
grid (S24: any IS_AIC takes the car from the AI) and each value is checked with SMALL_AII:

    gear     CS.GEAR with no auto gears: REVERSE, NEUTRAL, FIRST, SECOND read back in IS_AII.Gear;
             SEQUENTIAL, then CS.CHUP, goes up one gear
    lights   HEADLIGHTS (SIDE, LOW, HIGH, OFF), INDICATORS (LEFT, RIGHT, HAZARD, CANCEL) and
             TOGGLE (CS.PITSPEED: ON, OFF, TOGGLE) in IS_AII.ShowLights
    ignition TOGGLE (OFF, ON, TOGGLE, TOGGLE) on CS.IGNITION, read in AIFLAGS.IGNITION

A car without some dash light shows nothing for it: those checks say so, they are not failures of
the names. The report goes to tests/live_reports/group_AIC_*.json (see harness.py).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib

from group_a import GroupA
from harness import Session

from lfs_insim.packets import (
    AIFLAGS,
    CS,
    DL,
    GEAR,
    HEADLIGHTS,
    INDICATORS,
    IS_AIC,
    IS_AII,
    IS_SMALL,
    ISF,
    PIF,
    SMALL,
    TOGGLE,
    AIInputVal,
)


class AicValues:
    def __init__(self, s: Session, plid: int) -> None:
        self.s = s
        self.plid = plid
        self.reqi = 100

    def set(self, input: CS, value: int, time: int = 0) -> None:
        packet = IS_AIC(PLID=self.plid, Inputs=[AIInputVal(Input=input, Time=time, Value=value)])
        self.s.insim.send(packet)

    async def aii(self) -> IS_AII | None:
        self.reqi = self.reqi % 250 + 1
        reqi = self.reqi
        since = self.s.mark()
        self.s.insim.send(IS_SMALL(ReqI=reqi, SubT=SMALL.AII, UVal=self.plid))
        return await self.s.expect(IS_AII, lambda p: p.ReqI == reqi, since=since, timeout=3)

    async def lights(self, samples: int = 8) -> int:
        """The dash lights seen on in any of a few IS_AII (indicators blink)."""
        seen = 0
        for _ in range(samples):
            aii = await self.aii()
            if aii is not None:
                seen |= aii.ShowLights
            await asyncio.sleep(0.15)
        return seen

    async def gear(self) -> None:
        s = self.s
        self.set(CS.SET_HELP_FLAGS, PIF.AUTOCLUTCH)  # no AUTOGEARS: the shifter is ours
        await asyncio.sleep(0.5)
        for gear in (GEAR.NEUTRAL, GEAR.FIRST, GEAR.SECOND, GEAR.REVERSE, GEAR.NEUTRAL):
            self.set(CS.GEAR, gear)
            await asyncio.sleep(0.8)
            aii = await self.aii()
            read = None if aii is None else aii.Gear
            s.check(
                f"CS.GEAR = GEAR.{gear.name} -> IS_AII.Gear {int(gear)}", read == gear, str(read)
            )
        self.set(CS.GEAR, GEAR.SEQUENTIAL)
        await asyncio.sleep(0.5)
        self.set(CS.CHUP, 1, time=20)  # hold the shift up lever 0.2 s
        await asyncio.sleep(1)
        aii = await self.aii()
        read = None if aii is None else aii.Gear
        s.check(
            "GEAR.SEQUENTIAL, then CS.CHUP: neutral -> first",
            read == GEAR.FIRST,
            f"IS_AII.Gear {read}",
        )

    async def light(self, name: str, input: CS, value: int, on: list[DL], off: list[DL]) -> None:
        """SKIP, not FAIL, when none of the lights to see came on: S27, the AI's car showed no
        SIDELIGHTS, DIPPED or PITSPEED at all (a car without that dash light)."""
        self.set(input, value)
        await asyncio.sleep(0.5)
        seen = await self.lights()
        lit = [d.name for d in DL if seen & 1 << d]
        ok: bool | None = all(seen & 1 << d for d in on) and not any(seen & 1 << d for d in off)
        if not ok and not any(seen & 1 << d for d in on + off):
            ok = None  # nothing of it lit: maybe the car has no such light
        self.s.check(f"{name} -> ShowLights", ok, f"lit: {', '.join(lit) or 'none'}")

    async def dash(self) -> None:
        hl = CS.HEADLIGHTS
        beams = [DL.SIDELIGHTS, DL.DIPPED, DL.FULLBEAM]
        await self.light("HEADLIGHTS.SIDE", hl, HEADLIGHTS.SIDE, [DL.SIDELIGHTS], beams[1:])
        await self.light("HEADLIGHTS.LOW", hl, HEADLIGHTS.LOW, [DL.DIPPED], [DL.FULLBEAM])
        await self.light("HEADLIGHTS.HIGH", hl, HEADLIGHTS.HIGH, [DL.FULLBEAM], [])
        await self.light("HEADLIGHTS.OFF", hl, HEADLIGHTS.OFF, [], beams)
        ind = CS.INDICATORS
        left, right = DL.SIGNAL_L, DL.SIGNAL_R
        await self.light("INDICATORS.LEFT", ind, INDICATORS.LEFT, [left], [right])
        await self.light("INDICATORS.RIGHT", ind, INDICATORS.RIGHT, [right], [left])
        await self.light("INDICATORS.HAZARD", ind, INDICATORS.HAZARD, [left, right], [])
        await self.light("INDICATORS.CANCEL", ind, INDICATORS.CANCEL, [], [left, right])
        pit = CS.PITSPEED
        await self.light("TOGGLE.ON on CS.PITSPEED", pit, TOGGLE.ON, [DL.PITSPEED], [])
        await self.light("TOGGLE.OFF on CS.PITSPEED", pit, TOGGLE.OFF, [], [DL.PITSPEED])
        await self.light("TOGGLE.TOGGLE on CS.PITSPEED", pit, TOGGLE.TOGGLE, [DL.PITSPEED], [])
        self.set(pit, TOGGLE.OFF)

    async def ignition(self) -> None:
        """TOGGLE on the one toggle input IS_AII reads back: AIFLAGS.IGNITION."""
        s = self.s
        before = await self.aii()
        s.note(f"AIFLAGS before: {None if before is None else AIFLAGS(before.Flags)!r}")
        steps = [
            (TOGGLE.OFF, False),
            (TOGGLE.ON, True),
            (TOGGLE.TOGGLE, False),
            (TOGGLE.TOGGLE, True),
        ]
        for value, running in steps:
            self.set(CS.IGNITION, value)
            await asyncio.sleep(3)
            aii = await self.aii()
            flags = None if aii is None else AIFLAGS(aii.Flags)
            s.check(
                f"TOGGLE.{value.name} on CS.IGNITION -> AIFLAGS.IGNITION {running}",
                flags is not None and bool(flags & AIFLAGS.IGNITION) == running,
                repr(flags),
            )


async def main_async(port: int, admin: str) -> int:
    s = Session("AIC", port=port, admin_password=admin, flags=ISF.LOCAL)
    async with s:
        if not s.check("connected (IS_VER)", await s.connected()):
            return s.finish()
        race = GroupA(s, laps=1)
        await race.setup()
        if not race.racing or not race.ai:
            s.check("an AI car on the grid", None, "the race did not start")
            return s.finish()
        test = AicValues(s, race.ai[0])
        try:
            for name in ("gear", "dash", "ignition"):
                print(f"== {name}", flush=True)
                await getattr(test, name)()
        finally:
            test.set(CS.STOP_CONTROL, 0)
            await asyncio.sleep(1)
            s.insim.command("/end")
            await asyncio.sleep(2)
    return s.finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=29999)
    parser.add_argument("--admin", default="", help="Game Admin of cfg.txt, if LFS has one")
    args = parser.parse_args()
    return asyncio.run(main_async(args.port, args.admin))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
