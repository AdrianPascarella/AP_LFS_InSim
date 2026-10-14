"""Live protocol probe against a real LFS (W3.1). Not collected by pytest: it needs the game.

    .venv/Scripts/python tests/live/probe.py [--port 29999] [--seconds 10] [--wait 180] [--exit]
        [--outgauge PORT] [--outsim PORT [--outsim-opts HEX]]

With LFS open and InSim listening (`/insim=29999` in LFS), it connects, asks LFS for everything
it can report (version, state, connections, players, results...), sends messages and a button,
and listens for a while, wherever LFS is (menu, race, replay). Every packet received is packed
again and compared with the bytes LFS sent (see harness.py). The report goes to
tests/live_reports/ and a summary to the console. The group scripts (group_a.py...) go further:
they set up a situation and check what LFS sends.

--exit sends /exit at the end, which closes LFS: only for an LFS that the tester opened.
--outgauge and --outsim also listen to those UDP ports (the OutGauge and OutSim lines of LFS's
cfg.txt; --outsim-opts is its "OutSim Opts", in hexadecimal as there) and check their packets the
same way. LFS sends them only while a car is on track.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import time
from typing import Any

from harness import (
    REPORTS,
    LiveOutGauge,
    LiveOutSim,
    Recorder,
    _Recorded,
    received_report,
    summary,
)

import lfs_insim
from lfs_insim import InSim
from lfs_insim.packets import (
    BFN,
    IS_BFN,
    IS_BTN,
    IS_MSL,
    IS_MST,
    IS_MSX,
    IS_TINY,
    IS_VER,
    ISB,
    ISF,
    TINY,
)
from lfs_insim.packets._directions import InstructionPacket

REQUESTS = [  # TINY info requests: in single player some get no answer, which the report shows
    TINY.VER,
    TINY.PING,
    TINY.SST,
    TINY.GTM,
    TINY.SCP,
    TINY.ISM,
    TINY.NCN,
    TINY.NPL,
    TINY.RES,
    TINY.NLP,
    TINY.MCI,
    TINY.REO,
    TINY.RST,
    TINY.AXI,
    TINY.RIP,
    TINY.NCI,
    TINY.ALC,
    TINY.AXM,
    TINY.SLC,
    TINY.MAL,
    TINY.PLH,
    TINY.IPB,
    TINY.LCL,
]
FIRST_REQI = 10  # ReqI of REQUESTS[0]; the next ones count up, so each answer names its request


def sent_packets() -> list[InstructionPacket]:
    requests: list[InstructionPacket] = [
        IS_TINY(ReqI=FIRST_REQI + i, SubT=sub) for i, sub in enumerate(REQUESTS)
    ]
    messages: list[InstructionPacket] = [
        IS_MSL(Msg="lfs_insim live test: IS_MSL (local message)"),
        IS_MSX(Msg="lfs_insim live test: IS_MSX ^1red ^2green ^7white"),
        IS_MST(Msg="lfs_insim live test: IS_MST áéí ñ ü € Ωλ"),
    ]
    button = IS_BTN(
        ReqI=1,
        UCID=0,
        ClickID=1,
        BStyle=ISB.DARK | ISB.CLICK,
        TypeIn=20,
        L=70,
        T=40,
        W=60,
        H=8,
        Text="lfs_insim live test: button",
        Caption="Type something",
    )  # clicked, it opens a text box and LFS answers with IS_BTT
    plain_button = IS_BTN(
        ReqI=2,
        UCID=0,
        ClickID=2,
        BStyle=ISB.LIGHT | ISB.CLICK,
        L=70,
        T=50,
        W=60,
        H=8,
        Text="lfs_insim live test: click me",
    )  # clicked, LFS answers with IS_BTC
    return [*requests, *messages, button, plain_button]


def report(recorder: Recorder, sent: list[InstructionPacket], ver_seen: bool) -> dict[str, Any]:
    insim = [item for item in recorder.received if item.source == "InSim"]
    by_reqi = {item.raw[2] for item in insim}  # ReqI is the third byte
    return {
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lfs_insim": lfs_insim.__version__,
        "connected": ver_seen,
        "requests_answered": {
            sub.name: (FIRST_REQI + i) in by_reqi for i, sub in enumerate(REQUESTS)
        },
        "sent": [type(packet).__name__ for packet in sent],
        **received_report(recorder),
    }


def probe_summary(data: dict[str, Any]) -> str:
    unanswered = [name for name, ok in data["requests_answered"].items() if not ok]
    return "\n".join(
        [
            f"connected: {data['connected']}",
            "requests without answer: " + (", ".join(unanswered) or "none"),
            summary(data),
        ]
    )


async def live(
    port: int,
    seconds: float,
    wait: float,
    exit_lfs: bool,
    outgauge: int | None = None,
    outsim: int | None = None,
    outsim_opts: int = 0,
) -> dict[str, Any]:
    recorder = Recorder()
    recorder.install()

    flags = ISF.LOCAL | ISF.CON | ISF.MCI | ISF.HLV | ISF.OBH  # in a race: positions, contacts
    insim = InSim(name="lfs_insim live", port=port, flags=flags, interval_ms=500)
    accepted = asyncio.Event()
    sent = sent_packets()

    @insim.on(IS_VER)
    def version(packet: IS_VER) -> None:
        accepted.set()

    udp: list[_Recorded] = []
    if outgauge is not None:
        udp.append(LiveOutGauge(outgauge))
    if outsim is not None:
        udp.append(LiveOutSim(outsim, options=outsim_opts))
    for source in udp:
        source.recorder = recorder

    async with contextlib.AsyncExitStack() as stack:
        for source in udp:
            await stack.enter_async_context(source)
        await stack.enter_async_context(insim)
        try:
            await asyncio.wait_for(accepted.wait(), wait)
        except TimeoutError:
            return report(recorder, sent, ver_seen=False)
        insim.send(*sent)
        await asyncio.sleep(seconds)
        insim.send(IS_BFN(SubT=BFN.CLEAR))
        if exit_lfs:
            insim.send(IS_MST(Msg="/exit"))
        await asyncio.sleep(0.5)
    return report(recorder, sent, ver_seen=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=29999)
    parser.add_argument("--seconds", type=float, default=10, help="time to listen after sending")
    parser.add_argument("--wait", type=float, default=180, help="time to wait for LFS to answer")
    parser.add_argument("--exit", action="store_true", help="close LFS with /exit at the end")
    parser.add_argument("--outgauge", type=int, help="also listen to OutGauge on this UDP port")
    parser.add_argument("--outsim", type=int, help="also listen to OutSim on this UDP port")
    parser.add_argument(
        "--outsim-opts", type=lambda text: int(text, 16), default=0, help="OutSim Opts (hex)"
    )
    args = parser.parse_args()
    data = asyncio.run(
        live(
            args.port,
            args.seconds,
            args.wait,
            args.exit,
            args.outgauge,
            args.outsim,
            args.outsim_opts,
        )
    )
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / time.strftime("live_%Y%m%d_%H%M%S.json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(probe_summary(data))
    print(f"report: {path}")
    ok = data["connected"] and not data["unreadable"] and not data["content_changes"]
    return 0 if ok else 1


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
