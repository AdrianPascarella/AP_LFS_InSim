"""Live test, group A (W11.3): single player with AI. Not collected by pytest: it needs the game.

    .venv/Scripts/python tests/live/group_a.py [--port 29999] [--only SECTION ...] [--laps 2]

Start with LFS in the single player race setup screen (the one with the GO button) and InSim
listening (`/insim=29999`). The script sets up the race with LFS commands (`/laps`, `/ai`,
`/restart`), so nothing is typed or clicked unless a section says so. Sections, in order:

    requests  TINY requests answered in any state (STA, RTP, NCN, NPL, ALC, LCL, REO, RES)
    setup     a race with AI drivers: REO sent, NPL of each AI, RST
    race      what a race sends (SPX, LAP, NLP, MCI, CSC...), AIC / AII on an AI car
    sends     instructions with a visible or answered effect: buttons, OCO, SFP, SCH, SSH, NLI
    udp       OutSim and OutGauge started with SMALL_SSP / SSG (no cfg.txt), on a free port
    finish    FIN and RES of each car, TINY_RES, then /end (TINY_REN) and /clear (TINY_CLR)

Things that may or may not happen in a race (contacts, flags, penalties) are recorded as SKIP
when they did not. The report goes to tests/live_reports/group_A_*.json (see harness.py).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import math
from collections.abc import Callable

from harness import LiveOutGauge, LiveOutSim, Session

from lfs_insim.packets import (
    BFN,
    CS,
    IS_AIC,
    IS_AII,
    IS_BFN,
    IS_BTN,
    IS_CCH,
    IS_CON,
    IS_CSC,
    IS_FIN,
    IS_FLG,
    IS_HLV,
    IS_LAP,
    IS_MCI,
    IS_NCN,
    IS_NLP,
    IS_NPL,
    IS_OCO,
    IS_PEN,
    IS_REO,
    IS_RES,
    IS_RST,
    IS_SCH,
    IS_SFP,
    IS_SMALL,
    IS_SPX,
    IS_STA,
    IS_TINY,
    ISB,
    ISF,
    ISS,
    OCO,
    PTYPE,
    SMALL,
    TINY,
    AIInputVal,
)
from lfs_insim.packets._structure import Structure

SECTIONS = ["requests", "setup", "race", "sends", "udp", "finish"]
FLAGS = ISF.LOCAL | ISF.CON | ISF.MCI | ISF.NLP | ISF.HLV | ISF.OBH
UDP_PORTS = {SMALL.SSP: 30011, SMALL.SSG: 30012}  # free here: 30000 is the user's OutGauge
GO_BUTTON = (0.935, 0.96)  # in the race setup screen, as fractions of LFS's window
OCO_INDEX_MAIN = 240  # main start lights (InSim.txt has it as a #define, not an enum)


def of_player(plid: int) -> Callable[[IS_FIN], bool]:
    return lambda packet: plid == packet.PLID


def speed(aii: IS_AII) -> float:
    return math.hypot(aii.OSData.Vel.X, aii.OSData.Vel.Y)


class GroupA:
    def __init__(self, s: Session, laps: int) -> None:
        self.s = s
        self.laps = laps
        self.ai: list[int] = []  # PLIDs of the AI drivers this test added
        self.race_start = 0  # mark of the race start
        self.racing = True  # False when setup could not start the race: race and finish skip

    async def ask(self, sub: TINY, cls: type[Structure], reqi: int, timeout: float = 3) -> None:
        """Send a TINY request and check that the answer carries its ReqI."""
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=reqi, SubT=sub))
        await self.s.expect_check(
            f"TINY_{sub.name} -> {cls.__name__}",
            cls,
            lambda p: p.ReqI == reqi,  # type: ignore[attr-defined]
            since=since,
            timeout=timeout,
            show=lambda p: str(p)[:200],
        )

    async def requests(self) -> None:
        await self.ask(TINY.SST, IS_STA, 40)
        await self.ask(TINY.GTM, IS_SMALL, 41)
        await self.ask(TINY.NCN, IS_NCN, 42)
        await self.ask(TINY.ALC, IS_SMALL, 43)
        await self.ask(TINY.LCL, IS_SMALL, 44)
        await self.ask(TINY.REO, IS_REO, 45)

    async def setup(self) -> None:
        s = self.s
        state = await s.insim.request.IS_STA()
        s.note(f"state before setup: {ISS(state.Flags)!r}, RaceInProg {state.RaceInProg}")
        s.insim.command(f"/laps {self.laps}")
        grid = await s.insim.request_all.IS_NPL()
        missing = 2 - sum(1 for p in grid if p.PType & PTYPE.AI)  # a run stopped early leaves some
        since = s.mark()
        for _ in range(missing):
            s.insim.command("/ai")
            await asyncio.sleep(1)
        await asyncio.sleep(2)
        added = [p for p in s.seen(IS_NPL, since) if p.PType & PTYPE.AI]
        s.check(f"/ai x{missing} -> IS_NPL with PTYPE.AI", len(added) == missing, str(len(added)))
        for npl in added:
            s.check(f"NPL {npl.PLID}: name and car", bool(npl.PName and npl.CName), npl.PName)
        grid = await s.insim.request_all.IS_NPL()
        self.ai = [p.PLID for p in grid if p.PType & PTYPE.AI]
        order = [p.PLID for p in reversed(grid)]  # the start order, reversed
        s.insim.send(IS_REO(NumP=len(order), PLID=order + [0] * (48 - len(order))))
        await asyncio.sleep(1)  # S24: a TINY_REO sent right after still gets the old order
        await self.ask(TINY.REO, IS_REO, 50)
        reo = s.seen(IS_REO)[-1]
        s.check(
            "IS_REO sent -> TINY_REO reads it back",
            reo.PLID[: len(order)] == order,
            f"sent {order}, read {reo.PLID[: len(order)]}",
        )
        since = s.mark()
        s.insim.command("/restart")
        rst = await s.expect(IS_RST, since=since, timeout=5)
        if rst is None:  # seen in S24: in single player /restart does not start the race
            s.note("/restart did not start the race (single player): clicking GO")
            await s.screen(at=GO_BUTTON, wait=500)
            rst = await s.expect(IS_RST, since=since, timeout=60)
        s.check("the race starts (IS_RST)", rst is not None)
        self.race_start = since
        self.racing = rst is not None
        if rst is not None:
            s.check("IS_RST laps", rst.RaceLaps == self.laps, f"RaceLaps {rst.RaceLaps}")
            s.check("IS_RST track", rst.Track != "", rst.Track)

    async def race(self) -> None:
        s = self.s
        start = self.race_start
        await s.expect_check("IS_MCI in the race", IS_MCI, since=start, timeout=30)
        await s.expect_check("IS_NLP in the race", IS_NLP, since=start, timeout=30)
        await s.expect_check("IS_CSC (car start)", IS_CSC, since=start, timeout=30)
        await s.expect_check("IS_SPX (split)", IS_SPX, since=start, timeout=120)
        if self.ai:
            await self.ai_info(self.ai[0])
        await s.expect_check("IS_LAP", IS_LAP, since=start, timeout=240)
        await self.ask(TINY.NLP, IS_NLP, 60)
        await self.ask(TINY.MCI, IS_MCI, 61)
        await self.ask(TINY.RST, IS_RST, 62)
        await self.ask(TINY.NPL, IS_NPL, 63)

    async def ai_info(self, plid: int) -> None:
        """SMALL_AII only: it does not take the car from the AI (any IS_AIC does, S24)."""
        s = self.s
        since = s.mark()
        s.insim.send(IS_SMALL(ReqI=70, SubT=SMALL.AII, UVal=plid))
        aii = await s.expect_check(
            "SMALL_AII -> IS_AII",
            IS_AII,
            lambda p: p.ReqI == 70,
            since=since,
            show=lambda p: f"PLID {p.PLID}, gear {p.Gear}, rpm {p.RPM:.0f}, pos {p.OSData.Pos}",
        )
        if aii is not None:
            s.check("IS_AII of the asked car", plid == aii.PLID, f"PLID {aii.PLID}")

    async def ai_control(self, plid: int) -> None:
        """IS_AIC, on a car past the finish line. S24: in the race, after an IS_AIC (even
        CS_SEND_AI_INFO and the horn) the AI stopped driving and crashed. Here: measure it,
        and whether CS_STOP_CONTROL gives the car back to the AI."""
        s = self.s
        first = await self.aii(plid, 75)
        since = s.mark()
        info = AIInputVal(Input=CS.SEND_AI_INFO)
        s.insim.send(IS_AIC(ReqI=71, PLID=plid, Inputs=[info]))
        await s.expect_check(
            "IS_AIC CS_SEND_AI_INFO -> IS_AII", IS_AII, lambda p: p.ReqI == 71, since=since
        )
        horn = AIInputVal(Input=CS.HORN, Time=100, Value=3)  # hold the horn 1 s
        s.insim.send(IS_AIC(PLID=plid, Inputs=[horn]))
        s.note("IS_AIC horn sent to an AI car: only heard, not checked")
        await self.steer(plid)
        await asyncio.sleep(3)
        held = await self.aii(plid, 76)
        s.insim.send(IS_AIC(PLID=plid, Inputs=[AIInputVal(Input=CS.STOP_CONTROL)]))
        await asyncio.sleep(6)
        released = await self.aii(plid, 77)
        s.note(
            "AI speed (m/s) before IS_AIC / 4 s after / 6 s after CS_STOP_CONTROL: "
            + " / ".join("-" if a is None else f"{speed(a):.1f}" for a in (first, held, released))
        )

    async def steer(self, plid: int) -> None:
        """IS_AIC steering, after the finish line: in the race it put the car off (S24)."""
        s = self.s
        # Steer a little left for 0.5 s: the heading must turn left (anticlockwise: it grows).
        before = await self.aii(plid, 73)
        steer = AIInputVal(Input=CS.MSX, Time=50, Value=26000)
        s.insim.send(IS_AIC(PLID=plid, Inputs=[steer]))
        await asyncio.sleep(1)
        after = await self.aii(plid, 74)
        if before is None or after is None:
            s.check("IS_AIC steer left turns the car", None, "no IS_AII to compare")
        else:
            turn = math.degrees(after.OSData.Heading - before.OSData.Heading)
            turn = (turn + 180) % 360 - 180
            s.check(
                "IS_AIC steer left turns the car left", turn > 1, f"heading {turn:+.0f} degrees"
            )
        s.insim.send(IS_AIC(PLID=plid, Inputs=[AIInputVal(Input=CS.RESET_INPUTS)]))

    async def aii(self, plid: int, reqi: int) -> IS_AII | None:
        """Ask for an IS_AII with SMALL_AII (which leaves the car to the AI)."""
        since = self.s.mark()
        self.s.insim.send(IS_SMALL(ReqI=reqi, SubT=SMALL.AII, UVal=plid))
        return await self.s.expect(IS_AII, lambda p: p.ReqI == reqi, since=since, timeout=3)

    async def sends(self) -> None:
        s = self.s
        styles = [ISB.LIGHT, ISB.DARK, ISB.LEFT | ISB.LIGHT, ISB.RIGHT | ISB.DARK, ISB.C1]
        for i, style in enumerate(styles):
            s.insim.send(
                IS_BTN(
                    ReqI=1,
                    ClickID=10 + i,
                    BStyle=style,
                    L=5,
                    T=60 + 7 * i,
                    W=40,
                    H=6,
                    Text=f"style {style!r}",
                )
            )
        await s.screen()  # a screenshot of the buttons
        s.note("buttons with 5 styles drawn: see tests/live_reports/screen.png")
        s.insim.send(IS_BFN(SubT=BFN.DEL_BTN, ClickID=10, ClickMax=12))
        await s.screen()
        s.note("BFN_DEL_BTN for ClickID 10-12: two buttons should be left")
        s.insim.send(IS_BFN(SubT=BFN.CLEAR))
        for data in (1, 2, 4, 8):  # red1, red2, red3, green
            s.insim.send(IS_OCO(OCOAction=OCO.LIGHTS_SET, Index=OCO_INDEX_MAIN, Data=data))
            await asyncio.sleep(0.5)
        s.insim.send(IS_OCO(OCOAction=OCO.LIGHTS_RESET, Index=OCO_INDEX_MAIN))
        s.note("IS_OCO start lights red1, red2, red3, green, reset: visible only")
        await self.state_flag("SFP hide 2D", ISS.SHOW_2D, off=True)
        await self.state_flag("SFP show 2D", ISS.SHOW_2D, off=False)
        ssh = await s.insim.instruct.IS_SSH(Name="lfs_insim_live")
        s.check(
            "instruct.IS_SSH -> SSH.OK", ssh.Error == 0, f"Error {ssh.Error}, Name {ssh.Name!r}"
        )
        if not self.racing:  # S24: no camera and no IS_NLP in the race setup screen
            s.check("IS_SCH and SMALL_NLI", None, "the race did not start")
            return
        since = s.mark()
        before = await s.insim.request.IS_STA()
        s.insim.send(IS_SCH(CharB=ord("V")))  # V: next view
        cch = await s.expect(IS_CCH, since=since, timeout=5)
        after = await s.insim.request.IS_STA()
        s.check(
            "IS_SCH 'V' changes the view",
            cch is not None or after.InGameCam != before.InGameCam,
            f"IS_CCH {cch}, InGameCam {before.InGameCam} -> {after.InGameCam}",
        )
        s.insim.send(IS_SMALL(SubT=SMALL.NLI, UVal=1000))
        await asyncio.sleep(1.5)  # S24: counted at once, the old 500 ms gave 5 in 3.5 s
        since = s.mark()
        await asyncio.sleep(5)
        count = len(s.seen(IS_NLP, since))
        s.check("SMALL_NLI 1000 ms -> ~5 IS_NLP in 5 s", 4 <= count <= 6, f"{count} IS_NLP")
        s.insim.send(IS_SMALL(SubT=SMALL.NLI, UVal=500))

    async def state_flag(self, name: str, flag: ISS, *, off: bool) -> None:
        s = self.s
        s.insim.send(IS_SFP(Flag=flag, OffOn=0 if off else 1))
        await asyncio.sleep(0.5)
        state = await s.insim.request.IS_STA()
        s.check(name, bool(state.Flags & flag) != off, repr(ISS(state.Flags)))

    async def udp(self) -> None:
        """SMALL_SSP / SSG send to the port of InSim(udp_port=...) (W11.8)."""
        # One port each: in S24, with one port, OutGauge datagrams reached the OutSim reader.
        ssp, ssg = UDP_PORTS[SMALL.SSP], UDP_PORTS[SMALL.SSG]
        for sub, source in ((SMALL.SSP, LiveOutSim(ssp)), (SMALL.SSG, LiveOutGauge(ssg))):
            source.recorder = self.s.recorder
            other = Session(  # one report: its packets go to the same recorder
                f"A-{sub.name}", port=self.s.port, udp_port=UDP_PORTS[sub], recorder=self.s.recorder
            )
            async with source, other:
                if not await other.connected(10):
                    self.s.check(f"SMALL_{sub.name}: second connection", False, "no IS_VER")
                    continue
                since = self.s.mark()
                other.insim.send(IS_SMALL(SubT=sub, UVal=10))  # S24: hundredths of a second
                await asyncio.sleep(3)
                other.insim.send(IS_SMALL(SubT=sub, UVal=0))
                got = [i for i in self.s.recorder.received[since:] if i.source != "InSim"]
                self.s.check(
                    f"SMALL_{sub.name} UVal 10 (0.1 s) -> UDP to UDPPort",
                    20 <= len(got) <= 40,
                    f"{len(got)} packets in 3 s",
                )
                await asyncio.sleep(0.5)
                since = self.s.mark()
                await asyncio.sleep(2)
                after = [i for i in self.s.recorder.received[since:] if i.source != "InSim"]
                self.s.check(f"SMALL_{sub.name} UVal 0 stops it", not after, f"{len(after)} after")
            self.s.insim.sent_log += other.insim.sent_log

    async def finish(self) -> None:
        s = self.s
        start = self.race_start
        # IS_AIC on the first car to finish, at once: after the line an AI drives one more lap
        # back to the pits and parks (the user, S24), so it is still moving for a while.
        winner = await s.expect(IS_FIN, since=start, timeout=300)
        if winner is not None:
            await self.ai_control(winner.PLID)
        for plid in self.ai:
            fin = await s.expect(IS_FIN, of_player(plid), since=start, timeout=120)
            s.check(
                f"IS_FIN of AI {plid}", fin is not None, "" if fin is None else f"{fin.TTime} ms"
            )
        await s.expect_check("IS_RES after the finish", IS_RES, since=start, timeout=30)
        await self.ask(TINY.RES, IS_RES, 80, timeout=5)  # S12: no answer even in a race
        for cls, name in (
            (IS_CON, "IS_CON"),
            (IS_FLG, "IS_FLG"),
            (IS_HLV, "IS_HLV"),
            (IS_PEN, "IS_PEN"),
        ):
            seen = s.seen(cls, start)
            s.check(
                f"{name} in the race (if it happened)", True if seen else None, f"{len(seen)} seen"
            )
        since = s.mark()
        s.insim.command("/end")
        await s.expect_check("/end -> TINY_REN", IS_TINY, lambda p: p.SubT == TINY.REN, since=since)
        since = s.mark()
        s.insim.command("/clear")
        await s.expect_check(
            "/clear -> TINY_CLR", IS_TINY, lambda p: p.SubT == TINY.CLR, since=since
        )


async def main_async(port: int, sections: list[str], laps: int) -> int:
    s = Session("A", port=port, flags=FLAGS, interval_ms=500)
    async with s:
        if not s.check("connected (IS_VER)", await s.connected()):
            return s.finish()
        test = GroupA(s, laps)
        try:
            for name in sections:
                print(f"== {name}", flush=True)
                if name in ("race", "udp", "finish") and not test.racing:
                    s.check(f"section {name}", None, "the race did not start")
                    continue
                await getattr(test, name)()
            s.insim.send(IS_BFN(SubT=BFN.CLEAR))
            await asyncio.sleep(0.5)
        except ConnectionError as error:  # S24: LFS closed mid-run; keep what was seen
            s.check(f"connection kept until the end (in {name})", False, str(error))
    return s.finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=29999)
    parser.add_argument("--only", nargs="+", choices=SECTIONS, default=SECTIONS)
    parser.add_argument("--laps", type=int, default=2)
    args = parser.parse_args()
    sections = [name for name in SECTIONS if name in args.only]
    return asyncio.run(main_async(args.port, sections, args.laps))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
