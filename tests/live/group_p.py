"""Live test, group P (W11.6): another person connected to the server. Not collected by pytest.

    .venv/Scripts/python tests/live/group_p.py --host IP --port N --admin PASS --person USERNAME
                                              [--only STEP ...]

Connect to the InSim of the hosted server (as group_h.py: lfs.net -> Hosting -> Your hosts; this
computer's IP in its InSim access list; its admin password). `--person` is the LFS username of the
other person, who gets each step by private message (IS_MTC) and has two minutes for it; a step
not done in time is a SKIP. Steps, in order:

    message  IS_MTC to the person -> they type /i ok -> IS_III from their connection
    rename   they change their nickname -> IS_CPR
    setup    they send their setup from the garage -> IS_SET (ISF.SET)
    join     ISF.REQ_JOIN: they spectate and join -> join request (IS_NPL, NumP 0), refused with
             IS_JRR JRR.REJECT (no IS_NPL follows); they join again -> JRR.SPAWN -> IS_NPL
    vote     they vote to restart -> IS_VTN; TINY_VTC sent -> TINY_VTC back (cancelled); a second
             vote let through -> SMALL_VTA
    leave    they leave the server and come back -> IS_CNL, then IS_NCN (remote) and IS_NCI

While it runs, any other join request (the user's own, an AI added with /uai) is let through at
once (JRR.SPAWN): with ISF.REQ_JOIN, LFS waits for an answer. IS_TOC (taking over another's car)
needs a driver swap in a team race: not here. Never stop a free hosted server: it is deleted.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib

from harness import Session

from lfs_insim.packets import (
    IS_CNL,
    IS_CPR,
    IS_III,
    IS_JRR,
    IS_MTC,
    IS_NCI,
    IS_NCN,
    IS_NPL,
    IS_SET,
    IS_SMALL,
    IS_TINY,
    IS_VTN,
    ISF,
    JRR,
    LEAVR,
    NCNF,
    SMALL,
    TINY,
    VOTE,
)
from lfs_insim.text import plain

STEPS = ["message", "rename", "setup", "join", "vote", "leave"]
FLAGS = ISF.MSO_COLS | ISF.SET | ISF.REQ_JOIN
WAIT = 120.0  # seconds the person has for each step
NO_JOIN_S = 5.0  # after a refused join request, no IS_NPL may follow within this long


class GroupP:
    def __init__(self, s: Session, person: str) -> None:
        self.s = s
        self.person = person  # their LFS username
        self.ucid = 0
        self.judging = False  # the join step answers the person's requests itself

        @s.insim.on(IS_NPL)
        def let_in(packet: IS_NPL) -> None:
            if packet.NumP != 0 or (self.judging and self.ucid == packet.UCID):
                return
            s.insim.send(IS_JRR(UCID=packet.UCID, JRRAction=JRR.SPAWN))
            s.note(f"join request from UCID {packet.UCID} ({plain(packet.PName)}): let in")

    def tell(self, text: str) -> None:
        self.s.insim.send(IS_MTC(UCID=self.ucid, Text=f"lfs_insim test: {text}", Sound=1))
        print(f"  told {self.person}: {text}", flush=True)

    async def find(self) -> bool:
        """The person's connection, from the connections LFS lists (TINY_NCN)."""
        since = self.s.mark()
        self.s.insim.send(IS_TINY(ReqI=1, SubT=TINY.NCN))
        await asyncio.sleep(2.0)
        for ncn in self.s.seen(IS_NCN, since):
            if ncn.UName.lower() == self.person.lower():
                self.ucid = ncn.UCID
        return self.s.check(f"{self.person} connected", self.ucid != 0, f"UCID {self.ucid}")

    async def message(self) -> None:
        since = self.s.mark()
        self.tell("type   /i ok   (a message only this program sees)")
        await self.s.expect_check(
            "IS_MTC to a person -> IS_III from them",
            IS_III,
            lambda p: self.ucid == p.UCID,
            since=since,
            timeout=WAIT,
            show=lambda p: f"UCID {p.UCID}: {p.Msg!r}",
        )

    async def rename(self) -> None:
        since = self.s.mark()
        self.tell("change your nickname (Options > Player), then come back")
        await self.s.expect_check(
            "rename -> IS_CPR",
            IS_CPR,
            lambda p: self.ucid == p.UCID,
            since=since,
            timeout=WAIT,
            show=lambda p: f"UCID {p.UCID}: {plain(p.PName)!r}, plate {p.Plate!r}",
        )

    async def setup(self) -> None:
        since = self.s.mark()
        self.tell("in the garage, send your setup to the others (Setup screen)")
        await self.s.expect_check(
            "setup sent -> IS_SET",
            IS_SET,
            since=since,
            timeout=WAIT,
            show=lambda p: f"PLID {p.PLID}, {p.CName!r}, fuel {p.FuelLoad}",
        )

    async def join(self) -> None:
        s = self.s
        self.judging = True
        try:
            since = s.mark()
            self.tell("go to spectate (/spec), then join the race again")
            asked = await s.expect_check(
                "join request -> IS_NPL with NumP 0",
                IS_NPL,
                lambda p: self.ucid == p.UCID and p.NumP == 0,
                since=since,
                timeout=WAIT,
                show=lambda p: f"UCID {p.UCID}, {p.CName}",
            )
            if asked is None:
                return
            refused = s.mark()
            s.insim.send(IS_JRR(UCID=self.ucid, JRRAction=JRR.REJECT))
            late = await s.expect(
                IS_NPL,
                lambda p: self.ucid == p.UCID and p.NumP > 0,
                since=refused,
                timeout=NO_JOIN_S,
            )
            s.check("IS_JRR REJECT -> no IS_NPL follows", late is None)
            since = s.mark()
            self.tell("you were refused on purpose: join again, now you will get in")
            again = await s.expect(
                IS_NPL, lambda p: self.ucid == p.UCID and p.NumP == 0, since=since, timeout=WAIT
            )
            if not s.check("second join request", again is not None):
                return
            since = s.mark()
            s.insim.send(IS_JRR(UCID=self.ucid, JRRAction=JRR.SPAWN))
            await s.expect_check(
                "IS_JRR SPAWN -> IS_NPL",
                IS_NPL,
                lambda p: self.ucid == p.UCID and p.NumP > 0,
                since=since,
                timeout=10,
                show=lambda p: f"PLID {p.PLID}, {p.CName}",
            )
        finally:
            self.judging = False

    async def vote(self) -> None:
        s = self.s
        since = s.mark()
        self.tell("vote to restart: type /restart")
        # S29: an admin's /restart comes as IS_VTN from the host (UCID 0), then SMALL_VTA at once;
        # a guest's, from their connection, and with nobody else to vote it also passes at once.
        voted = await s.expect_check(
            "vote -> IS_VTN",
            IS_VTN,
            lambda p: p.UCID in (self.ucid, 0),
            since=since,
            timeout=WAIT,
            show=lambda p: f"UCID {p.UCID}, {VOTE(p.Action).name}",
        )
        if voted is None:
            return
        if voted.UCID == 0:
            s.note("the /restart of an admin: IS_VTN from the host (UCID 0), carried out at once")
        done = await s.expect(IS_SMALL, lambda p: p.SubT == SMALL.VTA, since=since, timeout=3)
        if done is not None:
            s.check("vote carried out -> SMALL_VTA", True, VOTE(done.UVal).name)
            s.note("the vote passed at once (no one else to vote): nothing left to cancel")
            return
        since = s.mark()
        s.insim.send(IS_TINY(SubT=TINY.VTC))
        await s.expect_check(
            "TINY_VTC sent -> TINY_VTC (cancelled)",
            IS_TINY,
            lambda p: p.SubT == TINY.VTC,
            since=since,
            timeout=10,
        )
        since = s.mark()
        self.tell("vote to restart again (/restart): this time it goes through")
        await s.expect_check(
            "second vote -> SMALL_VTA",
            IS_SMALL,
            lambda p: p.SubT == SMALL.VTA,
            since=since,
            timeout=WAIT,
            show=lambda p: f"{VOTE(p.UVal).name}",
        )

    async def leave(self) -> None:
        s = self.s
        since = s.mark()
        self.tell("leave the server, then join it again")
        cnl = await s.expect_check(
            "leaving -> IS_CNL",
            IS_CNL,
            lambda p: self.ucid == p.UCID,
            since=since,
            timeout=WAIT,
            show=lambda p: f"UCID {p.UCID}, {LEAVR(p.Reason).name}, {p.Total} left",
        )
        if cnl is None:
            return
        since = s.mark()
        ncn = await s.expect_check(
            "coming back -> IS_NCN (remote)",
            IS_NCN,
            lambda p: p.UName.lower() == self.person.lower() and bool(p.Flags & NCNF.REMOTE),
            since=since,
            timeout=WAIT,
            show=lambda p: f"UCID {p.UCID}, {p.UName}, admin {p.Admin}",
        )
        if ncn is None:
            return
        self.ucid = ncn.UCID
        await s.expect_check(
            "coming back -> IS_NCI",
            IS_NCI,
            lambda p: p.UCID == ncn.UCID,
            since=since,
            timeout=10,
            show=lambda p: f"UCID {p.UCID}, language {p.Language}, licence {p.License}",
        )


async def main_async(host: str, admin: str, port: int, person: str, steps: list[str]) -> int:
    s = Session("P", host=host, admin_password=admin, port=port, flags=FLAGS)
    async with s:
        if not s.check("connected (IS_VER)", await s.connected()):
            return s.finish()
        test = GroupP(s, person)
        if not await test.find():
            return s.finish()
        name = ""
        try:
            for name in steps:
                print(f"== {name}", flush=True)
                await getattr(test, name)()
            test.tell("done, thank you")
            await asyncio.sleep(0.5)
        except ConnectionError as error:
            s.check(f"connection kept until the end (in {name})", False, str(error))
    return s.finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", required=True, help="the server's InSim address")
    parser.add_argument("--admin", default="", help="the server's admin password")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--person", required=True, help="the other person's LFS username")
    parser.add_argument("--only", nargs="+", choices=STEPS, default=STEPS)
    args = parser.parse_args()
    steps = [name for name in STEPS if name in args.only]
    return asyncio.run(main_async(args.host, args.admin, args.port, args.person, steps))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
