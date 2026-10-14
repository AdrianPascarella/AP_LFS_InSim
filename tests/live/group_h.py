"""Live test, group H (W11.5): this LFS as a multiplayer host. Not collected by pytest.

    .venv/Scripts/python tests/live/group_h.py [--port 29999] [--only SECTION ...]

Start with LFS hosting (Multiplayer -> Create new host; hidden, no one else needs to join), in
the race setup screen, with InSim listening (`/insim=29999`). Every host list the test changes
(allowed mods, IP bans, allowed cars, handicaps) is read first and put back at the end.
Sections, in order:

    requests  ISM (Host), NCN, NCI (only with an admin password), SLC, MAL, PLH, IPB, ALC
    lists     IS_MAL, IS_IPB, SMALL_ALC, IS_PLC: set, read back, restore
    messages  IS_MTC to the host (UCID 0), to everyone (255), to a player; /i -> IS_III; IS_ACR
    race      an AI driver, /restart; IS_PLH (sent -> echoed), IS_HCP, TINY_PLH
    leave     /end, /clear and /leave -> TINY_MPE (LFS stops hosting)
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from collections.abc import Callable
from ipaddress import IPv4Address

from harness import Session

from lfs_insim.packets import (
    BFN,
    IS_ACR,
    IS_BFN,
    IS_HCP,
    IS_III,
    IS_IPB,
    IS_MAL,
    IS_MTC,
    IS_NCN,
    IS_NPL,
    IS_PLC,
    IS_PLH,
    IS_RST,
    IS_SMALL,
    IS_TINY,
    ISF,
    PLHF,
    PTYPE,
    SMALL,
    TINY,
    CarHCP,
    PlayerHCap,
)

SECTIONS = ["requests", "lists", "messages", "race", "leave"]
FLAGS = ISF.MSO_COLS | ISF.SET
TEST_IP = IPv4Address("192.0.2.1")  # TEST-NET-1 (RFC 5737): no real computer has it
TEST_MOD = "35D799"  # the mod in this computer's single player tests (SLX180 TYPEX)
XF_GTI = 1  # CARS bit of the XF GTI


def subtype(sub: TINY) -> Callable[[IS_TINY], bool]:
    return lambda packet: packet.SubT == sub


class GroupH:
    def __init__(self, s: Session) -> None:
        self.s = s
        self.mods: list[str] = []
        self.bans: list[IPv4Address] = []
        self.cars = 0
        self.host = False
        self.has_ipb = False

    async def requests(self) -> None:
        s = self.s
        ism = await s.insim.request.IS_ISM()
        self.host = ism.Host == 1
        # S24: with LFS 0.8C32's "Create new host", this game is an admin guest (UCID 1) of a
        # host it runs inside (UCID 0, remote): Host 0. Only a dedicated host's InSim is the host.
        s.check("TINY_ISM -> IS_ISM", True, f"Host {ism.Host}, {ism.HName!r}")
        s.note("this InSim is the host's" if self.host else "this InSim is a guest's (admin)")
        ncn = await s.insim.request_all.IS_NCN()
        s.check("TINY_NCN -> IS_NCN of every connection", bool(ncn), f"{len(ncn)} connections")
        nci = await s.insim.request_all.IS_NCI(quiet=2)
        s.check(
            "TINY_NCI -> IS_NCI (only with an admin password)",
            True if nci else None,
            f"{len(nci)} IS_NCI" + (f"; {nci[0]}" if nci else "; no admin password on this host"),
        )
        slc = await s.insim.request_all.IS_SLC(quiet=2)
        s.check("TINY_SLC -> IS_SLC", True if slc else None, "; ".join(map(str, slc)))
        mal = await s.insim.request.IS_MAL()
        self.mods = list(mal.SkinID)
        s.check("TINY_MAL -> IS_MAL", True, f"{len(self.mods)} mods allowed (0 = all)")
        plh = await s.insim.request.IS_PLH()
        s.check("TINY_PLH -> IS_PLH", True, f"{len(plh.HCaps)} players")
        try:
            ipb = await s.insim.request.IS_IPB(timeout=3)
            self.bans = list(ipb.BanIPs)
            self.has_ipb = True
            s.check("TINY_IPB -> IS_IPB", True, f"{len(self.bans)} bans")
        except TimeoutError:
            s.check("TINY_IPB -> IS_IPB", None if not self.host else False, "no answer")
        since = s.mark()
        s.insim.send(IS_TINY(ReqI=40, SubT=TINY.ALC))
        alc = await s.expect(IS_SMALL, lambda p: p.ReqI == 40, since=since)
        self.cars = alc.UVal if alc else 0
        s.check("TINY_ALC -> SMALL_ALC", alc is not None, f"cars {self.cars:#x}")

    async def read_mal(self, reqi: int) -> list[str]:
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=reqi, SubT=TINY.MAL))
        await asyncio.sleep(1)
        return [m for p in self.s.seen(IS_MAL, since) if p.ReqI == reqi for m in p.SkinID]

    async def read_ipb(self, reqi: int) -> list[IPv4Address]:
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=reqi, SubT=TINY.IPB))
        await asyncio.sleep(1)
        return [ip for p in self.s.seen(IS_IPB, since) if p.ReqI == reqi for ip in p.BanIPs]

    async def read_alc(self, reqi: int) -> int | None:
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=reqi, SubT=TINY.ALC))
        alc = await self.s.expect(IS_SMALL, lambda p: p.ReqI == reqi, since=since)
        return None if alc is None else alc.UVal

    async def lists(self) -> None:
        s = self.s
        try:
            s.insim.send(IS_MAL(SkinID=[*self.mods, TEST_MOD] if self.mods else [TEST_MOD]))
            await asyncio.sleep(0.5)
            mods = await self.read_mal(50)
            s.check("IS_MAL sent -> TINY_MAL reads it", TEST_MOD in mods, f"{mods}")
            if self.has_ipb:
                s.insim.send(IS_IPB(BanIPs=[*self.bans, TEST_IP]))
                await asyncio.sleep(0.5)
                bans = await self.read_ipb(51)
                s.check("IS_IPB sent -> TINY_IPB reads it", TEST_IP in bans, f"{bans}")
            if self.cars:
                fewer = self.cars & ~XF_GTI or XF_GTI
                s.insim.send(IS_SMALL(SubT=SMALL.ALC, UVal=fewer))
                await asyncio.sleep(0.5)
                cars = await self.read_alc(52)
                s.check("SMALL_ALC sent -> TINY_ALC reads it", cars == fewer, f"{cars} / {fewer}")
            s.insim.send(IS_PLC(UCID=0, Cars=XF_GTI))  # no reply: LFS only accepts it or not
            s.note("IS_PLC sent to the host's connection (XF GTI only): no reply to check")
            await s.screen()
            s.note("after the lists: see tests/live_reports/screen.png (red = refused)")
        finally:
            s.insim.send(IS_MAL(SkinID=self.mods))  # an empty list allows all mods
            if self.has_ipb:
                s.insim.send(IS_IPB(BanIPs=self.bans))
            if self.cars:
                s.insim.send(IS_SMALL(SubT=SMALL.ALC, UVal=self.cars))
            s.insim.send(IS_PLC(UCID=0, Cars=0xFFFFFFFF))  # all the host's cars
            await asyncio.sleep(0.5)
        s.check("IS_MAL restored", await self.read_mal(53) == self.mods)
        if self.has_ipb:
            s.check("IS_IPB restored", await self.read_ipb(54) == self.bans)
        if self.cars:
            s.check("SMALL_ALC restored", await self.read_alc(55) == self.cars)

    async def messages(self) -> None:
        s = self.s
        since = s.mark()
        s.insim.send(IS_MTC(UCID=0, Text="lfs_insim live H: IS_MTC to UCID 0 (the host)"))
        s.insim.send(IS_MTC(UCID=255, Text="lfs_insim live H: IS_MTC to everyone"))
        await asyncio.sleep(1)
        await s.screen()
        s.note("IS_MTC to UCID 0 and 255: see tests/live_reports/screen.png (red = refused)")
        s.insim.command("/i hello from the host")
        iii = await s.expect(IS_III, since=since, timeout=5)
        s.check("/i text -> IS_III", True if iii else None, str(iii))
        s.insim.command("/rstmin 0")
        acr = await s.expect(IS_ACR, lambda p: "rstmin" in p.Text, since=since, timeout=5)
        s.check("an admin command -> IS_ACR", acr is not None, str(acr))
        await s.expect_check(
            "IS_NCN when it starts (if any joined)", IS_NCN, since=since, timeout=0.1
        )

    async def race(self) -> None:
        s = self.s
        since = s.mark()
        s.insim.command("/ai")
        npl = await s.expect(IS_NPL, lambda p: bool(p.PType & PTYPE.AI), since=since, timeout=10)
        if not s.check("/ai on the host -> IS_NPL", npl is not None):
            return
        assert npl is not None
        since = s.mark()
        s.insim.command("/restart")
        if not await s.expect_check(
            "/restart on the host -> IS_RST", IS_RST, since=since, timeout=30
        ):
            return
        await asyncio.sleep(3)
        hcap = PlayerHCap(PLID=npl.PLID, Flags=PLHF.SET_MASS | PLHF.SET_TRES, H_Mass=50, H_TRes=10)
        since = s.mark()
        s.insim.send(IS_PLH(HCaps=[hcap]))
        echo = await s.expect(IS_PLH, lambda p: p.ReqI == 0, since=since)
        s.check(
            "IS_PLH sent -> IS_PLH output",
            echo is not None and any(h.H_Mass == 50 and h.H_TRes == 10 for h in echo.HCaps),
            str(echo),
        )
        plh = await s.insim.request.IS_PLH()
        caps = [h for h in plh.HCaps if h.PLID == npl.PLID]
        s.check("TINY_PLH reads it", any(h.H_Mass == 50 for h in caps), str(caps))
        hcp = IS_HCP()
        hcp.Info[0] = CarHCP(H_Mass=20, H_TRes=5)  # XF GTI
        s.insim.send(hcp)
        await asyncio.sleep(0.5)
        s.insim.send(IS_HCP())  # back to no car handicaps
        s.note("IS_HCP sent (XF GTI 20 kg, 5 %) and cleared: no reply to check")
        quiet = PlayerHCap(PLID=npl.PLID, Flags=PLHF.SET_MASS | PLHF.SET_TRES | PLHF.SILENT)
        s.insim.send(IS_PLH(HCaps=[quiet]))

    async def leave(self) -> None:
        s = self.s
        for command, sub in (("/end", TINY.REN), ("/clear", TINY.CLR)):
            since = s.mark()
            s.insim.command(command)
            await s.expect_check(
                f"{command} -> TINY_{sub.name}", IS_TINY, subtype(sub), since=since
            )
        since = s.mark()
        s.insim.command("/leave")
        mpe = await s.expect(IS_TINY, subtype(TINY.MPE), since=since, timeout=10)
        s.check("/leave -> TINY_MPE (no longer hosting)", mpe is not None)


async def main_async(port: int, sections: list[str]) -> int:
    s = Session("H", port=port, flags=FLAGS)
    async with s:
        if not s.check("connected (IS_VER)", await s.connected()):
            return s.finish()
        test = GroupH(s)
        name = ""
        try:
            for name in sections:
                print(f"== {name}", flush=True)
                await getattr(test, name)()
            if "leave" not in sections:
                s.insim.send(IS_BFN(SubT=BFN.CLEAR))
            await asyncio.sleep(0.5)
        except ConnectionError as error:
            s.check(f"connection kept until the end (in {name})", name == "leave", str(error))
    return s.finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=29999)
    parser.add_argument("--only", nargs="+", choices=SECTIONS, default=SECTIONS)
    args = parser.parse_args()
    sections = [name for name in SECTIONS if name in args.only]
    return asyncio.run(main_async(args.port, sections))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
