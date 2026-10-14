"""Live test, group D (W11.10): a person drives their own car. Not collected by pytest.

    .venv/Scripts/python tests/live/group_d.py [--port 29999] [--only STEP ...]

Start a single player race and drive your own car (InSim at 29999). The test shows each step at
the top of LFS's screen (a button) and in the chat, and waits for what LFS sends; a step not done
in time is a SKIP. Steps, in order:

    lights    SMALL_LCL (lights, signals, fog) read back with TINY_LCL; SMALL_LCS (flash, horn)
    oco       IS_OCO on the start lights while driving (screenshot)
    reset     the driver's own reset-car key -> IS_CRS (Shift+R restarts the race: S25)
    penalty   /p_dt for the driver -> IS_PEN (DT, or DT_VALID if already in the pit lane);
              serving it -> IS_PEN cleared (S25: leaving the pit lane served a DT_VALID)
    pits      enter the pit lane, stop at the garage, leave -> IS_PLA, IS_PIT, IS_PSF
    buttons   Shift+B with buttons -> IS_BFN USER_CLEAR; again, with none -> IS_BFN REQUEST
              (Shift+I is the same for a host's buttons: this InSim is local)
    garage    Shift+P -> IS_PLP; then /spec -> IS_PLL
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from collections.abc import Callable

from harness import P, Session

from lfs_insim.packets import (
    BFN,
    IS_BFN,
    IS_BTN,
    IS_CRS,
    IS_MSL,
    IS_NPL,
    IS_OCO,
    IS_PEN,
    IS_PIT,
    IS_PLA,
    IS_PLL,
    IS_PLP,
    IS_PSF,
    IS_SMALL,
    IS_TINY,
    ISB,
    ISF,
    LCL,
    LCS,
    OCO,
    PENALTY,
    PENR,
    PITLANE,
    PTYPE,
    SMALL,
    TINY,
)
from lfs_insim.text import plain

STEPS = ["lights", "oco", "reset", "penalty", "pits", "buttons", "garage"]
FLAGS = ISF.LOCAL | ISF.HLV
WAIT = 120.0  # seconds a person has for each step
OCO_INDEX_MAIN = 240
HINT = 60  # ClickID of the instruction button


class GroupD:
    def __init__(self, s: Session) -> None:
        self.s = s
        self.plid = 0
        self.name = ""

    def tell(self, text: str) -> None:
        """Show what to do: a button at the top of the screen and a line in the chat."""
        self.s.insim.send(
            IS_BTN(
                ReqI=1, ClickID=HINT, BStyle=ISB.DARK | ISB.C1, L=40, T=20, W=120, H=10, Text=text
            ),
            IS_MSL(Msg=f"lfs_insim test: {text}", Sound=1),
        )
        print(f"  >>> {text}", flush=True)

    def of_driver(self, cls: type) -> Callable[[object], bool]:
        return lambda packet: getattr(packet, "PLID", None) == self.plid

    async def driver(self) -> bool:
        """The person's own car (not AI) on track: wait for one if there is none yet."""
        s = self.s
        players = await s.insim.request_all.IS_NPL()
        own = [p for p in players if not p.PType & PTYPE.AI]
        if not own:
            self.tell("Join the race and drive your own car")
            since = s.mark()
            npl = await s.expect(
                IS_NPL, lambda p: not p.PType & PTYPE.AI, since=since, timeout=WAIT
            )
            if npl is None:
                return s.check("a driver on track", None, "no player car joined")
            own = [npl]
        self.plid, self.name = own[0].PLID, plain(own[0].PName)
        s.note(f"driver: PLID {self.plid}, {self.name!r}")
        return True

    async def read_lcl(self, reqi: int) -> int | None:
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=reqi, SubT=TINY.LCL))
        reply = await self.s.expect(IS_SMALL, lambda p: p.ReqI == reqi, since=since, timeout=3)
        return None if reply is None else reply.UVal

    async def lights(self) -> None:
        s = self.s
        tests = [
            ("low beam", LCL.SET_LIGHTS, 2 << 18, 0x000C0000),
            ("hazard signals", LCL.SET_SIGNALS, 3 << 16, 0x00030000),
            ("rear fog", LCL.SET_FOG_REAR, 1 << 20, 0x00100000),
        ]
        for name, flag, value, mask in tests:
            s.insim.send(IS_SMALL(SubT=SMALL.LCL, UVal=flag | value))
            await asyncio.sleep(1)
            uval = await self.read_lcl(30)
            s.check(
                f"SMALL_LCL {name} -> TINY_LCL reads it",
                uval is not None and uval & mask == value,
                "no reply" if uval is None else f"UVal {uval:#010x}",
            )
            s.insim.send(IS_SMALL(SubT=SMALL.LCL, UVal=flag))  # value 0: off
            await asyncio.sleep(0.5)
        s.insim.send(IS_SMALL(SubT=SMALL.LCS, UVal=LCS.SET_FLASH | 0x0400))
        s.insim.send(IS_SMALL(SubT=SMALL.LCS, UVal=LCS.SET_HORN | 1 << 16))
        await asyncio.sleep(1.5)
        await s.screen()
        s.insim.send(IS_SMALL(SubT=SMALL.LCS, UVal=LCS.SET_FLASH | LCS.SET_HORN))  # both off
        s.note("SMALL_LCS flash and horn 1.5 s: heard / see screen.png (no packet to check)")

    async def oco(self) -> None:
        s = self.s
        s.insim.send(IS_OCO(OCOAction=OCO.LIGHTS_SET, Index=OCO_INDEX_MAIN, Data=1 | 2 | 4))
        await asyncio.sleep(1)
        await s.screen()
        s.insim.send(IS_OCO(OCOAction=OCO.LIGHTS_RESET, Index=OCO_INDEX_MAIN))
        s.note("IS_OCO three red start lights while driving: see screen.png")

    async def step(
        self, text: str, cls: type[P], where: Callable[[P], bool], name: str
    ) -> P | None:
        s = self.s
        self.tell(text)
        since = s.mark()
        packet = await s.expect(cls, where, since=since, timeout=WAIT)
        s.check(name, True if packet else None, str(packet) if packet else "not done in time")
        return packet

    async def reset(self) -> None:
        await self.step(
            "Reset your car with your reset-car key (not Shift+R)",
            IS_CRS,
            self.of_driver(IS_CRS),
            "reset-car key -> IS_CRS",
        )

    async def penalty(self) -> None:
        s = self.s
        since = s.mark()
        s.insim.command(f"/p_dt {self.name}")
        pen = await s.expect(IS_PEN, self.of_driver(IS_PEN), since=since, timeout=5)
        s.check(
            "/p_dt -> IS_PEN (drive-through, by admin)",
            True
            if pen and pen.NewPen in (PENALTY.DT, PENALTY.DT_VALID) and pen.Reason == PENR.ADMIN
            else None,
            str(pen) if pen else "no IS_PEN (single player may not take /p_dt)",
        )
        if pen is None:
            return
        self.tell("Drive through the pit lane to serve the penalty")
        since = s.mark()
        cleared = await s.expect(
            IS_PEN,
            lambda p: self.plid == p.PLID and p.NewPen == PENALTY.NONE,
            since=since,
            timeout=WAIT,
        )
        s.check("penalty served -> IS_PEN cleared", True if cleared else None, str(cleared))

    async def pits(self) -> None:
        s = self.s
        since = s.mark()
        await self.step(
            "Enter the pit lane",
            IS_PLA,
            lambda p: self.plid == p.PLID and p.Fact in (PITLANE.ENTER, PITLANE.NO_PURPOSE),
            "IS_PLA enter",
        )
        await self.step(
            "Stop at your pit box (a pit stop)",
            IS_PIT,
            self.of_driver(IS_PIT),
            "pit stop -> IS_PIT",
        )
        await self.step(
            "Wait for the pit stop to finish",
            IS_PSF,
            self.of_driver(IS_PSF),
            "pit stop finished -> IS_PSF",
        )
        await self.step(
            "Drive out of the pit lane",
            IS_PLA,
            lambda p: self.plid == p.PLID and p.Fact == PITLANE.EXIT,
            "IS_PLA exit",
        )
        speeding = [p for p in s.seen(IS_PEN, since) if p.Reason == PENR.SPEEDING]
        if speeding:
            s.note(f"pit lane speeding penalty seen: {speeding[0]}")

    async def buttons(self) -> None:
        # S25: Shift+B is for local buttons (Shift+I for a host's); with buttons it clears them,
        # with none it asks for them.
        await self.step(
            "Press Shift+B (hide these buttons)",
            IS_BFN,
            lambda p: p.SubT == BFN.USER_CLEAR,
            "Shift+B -> IS_BFN USER_CLEAR",
        )
        print("  >>> Press Shift+B again (ask for buttons)", flush=True)
        self.s.insim.send(
            IS_MSL(Msg="lfs_insim test: press Shift+B again (ask for buttons)", Sound=1)
        )
        since = self.s.mark()
        req = await self.s.expect(
            IS_BFN, lambda p: p.SubT == BFN.REQUEST, since=since, timeout=WAIT
        )
        self.s.check("Shift+B with no buttons -> IS_BFN REQUEST", True if req else None, str(req))

    async def garage(self) -> None:
        await self.step(
            "Press Shift+P (go to the pits / garage)",
            IS_PLP,
            self.of_driver(IS_PLP),
            "Shift+P -> IS_PLP",
        )
        s = self.s
        since = s.mark()
        s.insim.command("/spec")
        pll = await s.expect(IS_PLL, since=since, timeout=10)
        s.check("/spec -> IS_PLL (if still in the race)", True if pll else None, str(pll))


async def main_async(port: int, admin: str, steps: list[str]) -> int:
    s = Session("D", port=port, admin_password=admin, flags=FLAGS)
    async with s:
        if not s.check("connected (IS_VER)", await s.connected()):
            return s.finish()
        test = GroupD(s)
        name = ""
        try:
            if await test.driver():
                for name in steps:
                    print(f"== {name}", flush=True)
                    await getattr(test, name)()
            test.tell("lfs_insim test finished, thank you")
            await asyncio.sleep(3)
            s.insim.send(IS_BFN(SubT=BFN.CLEAR))
            await asyncio.sleep(0.5)
        except ConnectionError as error:
            s.check(f"connection kept until the end (in {name})", False, str(error))
    return s.finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=29999)
    parser.add_argument("--admin", default="", help="LFS's multiplayer admin password, if set")
    parser.add_argument("--only", nargs="+", choices=STEPS, default=STEPS)
    args = parser.parse_args()
    return asyncio.run(
        main_async(args.port, args.admin, [name for name in STEPS if name in args.only])
    )


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
