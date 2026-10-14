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
UDP_PORT = 30011  # free on this computer: 30000 is the user's OutGauge (PROTOCOL §13)
OCO_INDEX_MAIN = 240  # main start lights (InSim.txt has it as a #define, not an enum)


class GroupA:
    def __init__(self, s: Session, laps: int) -> None:
        self.s = s
        self.laps = laps
        self.ai: list[int] = []  # PLIDs of the AI drivers this test added
        self.race_start = 0  # mark of the race start

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
        since = s.mark()
        for _ in range(2):
            s.insim.command("/ai")
            await asyncio.sleep(1)
        await asyncio.sleep(2)
        ai = [p for p in s.seen(IS_NPL, since) if p.PType & PTYPE.AI]
        self.ai = [p.PLID for p in ai]
        s.check("/ai x2 -> IS_NPL with PTYPE.AI", len(ai) == 2, f"PLIDs {self.ai}")
        for npl in ai:
            s.check(f"NPL {npl.PLID}: name and car", bool(npl.PName and npl.CName), npl.PName)
        if len(self.ai) == 2:  # the start order: the second AI first
            order = [self.ai[1], self.ai[0]]
            s.insim.send(IS_REO(NumP=2, PLID=order + [0] * 46))
            await self.ask(TINY.REO, IS_REO, 50)
            reo = s.seen(IS_REO)[-1]
            s.check(
                "IS_REO sent -> TINY_REO reads it back", reo.PLID[:2] == order, str(reo.PLID[:4])
            )
        since = s.mark()
        s.insim.command("/restart")
        rst = await s.expect_check("/restart -> IS_RST", IS_RST, since=since, timeout=60)
        self.race_start = since
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
            await self.ai_control(self.ai[0])
        await s.expect_check("IS_LAP", IS_LAP, since=start, timeout=240)
        await self.ask(TINY.NLP, IS_NLP, 60)
        await self.ask(TINY.MCI, IS_MCI, 61)
        await self.ask(TINY.RST, IS_RST, 62)
        await self.ask(TINY.NPL, IS_NPL, 63)

    async def ai_control(self, plid: int) -> None:
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
        since = s.mark()
        info = AIInputVal(Input=CS.SEND_AI_INFO)
        s.insim.send(IS_AIC(ReqI=71, PLID=plid, Inputs=[info]))
        await s.expect_check(
            "IS_AIC CS_SEND_AI_INFO -> IS_AII", IS_AII, lambda p: p.ReqI == 71, since=since
        )
        horn = AIInputVal(Input=CS.HORN, Time=100, Value=3)  # hold the horn 1 s
        s.insim.send(IS_AIC(PLID=plid, Inputs=[horn]))
        s.note("IS_AIC horn sent to an AI car: only heard, not checked")
        # Steer hard left for 2 s: the car's heading must turn left (anticlockwise: it grows).
        before = await self.aii(plid, 73)
        steer = AIInputVal(Input=CS.MSX, Time=200, Value=1)
        s.insim.send(IS_AIC(PLID=plid, Inputs=[steer]))
        await asyncio.sleep(1)
        after = await self.aii(plid, 74)
        if before is None or after is None:
            s.check("IS_AIC steer left turns the car", None, "no IS_AII to compare")
        else:
            turn = math.degrees(after.OSData.Heading - before.OSData.Heading)
            turn = (turn + 180) % 360 - 180
            s.check(
                "IS_AIC steer left turns the car left", turn > 5, f"heading {turn:+.0f} degrees"
            )
        s.insim.send(IS_AIC(PLID=plid, Inputs=[AIInputVal(Input=CS.RESET_INPUTS)]))

    async def aii(self, plid: int, reqi: int) -> IS_AII | None:
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
        since = s.mark()
        s.insim.send(IS_SCH(CharB=ord("V")))  # V: next view
        await s.expect_check("IS_SCH 'V' -> IS_CCH (camera change)", IS_CCH, since=since)
        ssh = await s.insim.instruct.IS_SSH(Name="lfs_insim_live")
        s.check(
            "instruct.IS_SSH -> SSH.OK", ssh.Error == 0, f"Error {ssh.Error}, Name {ssh.Name!r}"
        )
        s.insim.send(IS_SMALL(SubT=SMALL.NLI, UVal=1000))
        since = s.mark()
        await asyncio.sleep(3.5)
        count = len(s.seen(IS_NLP, since))
        s.check("SMALL_NLI 1000 ms -> ~3 IS_NLP in 3.5 s", 2 <= count <= 4, f"{count} IS_NLP")
        s.insim.send(IS_SMALL(SubT=SMALL.NLI, UVal=500))

    async def state_flag(self, name: str, flag: ISS, *, off: bool) -> None:
        s = self.s
        s.insim.send(IS_SFP(Flag=flag, OffOn=0 if off else 1))
        await asyncio.sleep(0.5)
        state = await s.insim.request.IS_STA()
        s.check(name, bool(state.Flags & flag) != off, repr(ISS(state.Flags)))

    async def udp(self) -> None:
        """SMALL_SSP / SSG send to IS_ISI.UDPPort, which InSim() cannot set yet (W11 finding)."""
        for sub, source in ((SMALL.SSP, LiveOutSim(UDP_PORT)), (SMALL.SSG, LiveOutGauge(UDP_PORT))):
            source.recorder = self.s.recorder
            other = Session(  # one report: its packets go to the same recorder
                f"A-{sub.name}", port=self.s.port, udp_port=UDP_PORT, recorder=self.s.recorder
            )
            async with source, other:
                if not await other.connected(10):
                    self.s.check(f"SMALL_{sub.name}: second connection", False, "no IS_VER")
                    continue
                since = self.s.mark()
                other.insim.send(IS_SMALL(SubT=sub, UVal=100))
                await asyncio.sleep(3)
                other.insim.send(IS_SMALL(SubT=sub, UVal=0))
                got = [i for i in self.s.recorder.received[since:] if i.source != "InSim"]
                self.s.check(
                    f"SMALL_{sub.name} 100 ms -> UDP to UDPPort",
                    len(got) >= 10,
                    f"{len(got)} packets",
                )
            self.s.insim.sent_log += other.insim.sent_log

    async def finish(self) -> None:
        s = self.s
        start = self.race_start
        for plid in self.ai:
            fin = next((p for p in s.seen(IS_FIN, start) if plid == p.PLID), None)
            deadline = asyncio.get_running_loop().time() + 300
            while fin is None and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.5)
                fin = next((p for p in s.seen(IS_FIN, start) if plid == p.PLID), None)
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
        for name in sections:
            print(f"== {name}")
            await getattr(test, name)()
        s.insim.send(IS_BFN(SubT=BFN.CLEAR))
        await asyncio.sleep(0.5)
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
