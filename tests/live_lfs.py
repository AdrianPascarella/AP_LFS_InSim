"""Live protocol test against a real LFS (W3.1). Not collected by pytest: it needs the game.

    .venv/Scripts/python tests/live_lfs.py [--port 29999] [--seconds 10] [--wait 180] [--exit]

With LFS open and InSim listening (`/insim=29999` in LFS), it connects, asks LFS for everything
it can report (version, state, connections, players, results...), sends messages and a button,
and listens for a while. Every packet received is packed again and compared with the bytes LFS
sent: a difference means the library reads or writes that packet wrongly (or LFS leaves bytes
the library does not keep, which the report shows so it can be told apart). The report goes to
tests/live_reports/ (ignored by git: it holds player names) and a summary to the console.

--exit sends /exit at the end, which closes LFS: only for an LFS that the tester opened.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Any

import lfs_insim
import lfs_insim._stream
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
from lfs_insim.packets._codec import InSimPacket, unpack_insim

REPORTS = Path(__file__).resolve().parent / "live_reports"

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


@dataclasses.dataclass
class Received:
    """One packet as LFS sent it, and what the library made of it."""

    raw: bytes
    packet: InSimPacket | None = None
    error: str = ""
    repacked: bytes = b""
    same_content: bool = False
    """Packing it again and reading that gives an equal packet (bytes may differ: see below)."""

    @property
    def name(self) -> str:
        return type(self.packet).__name__ if self.packet else f"type {self.raw[1]}"

    @property
    def same_bytes(self) -> bool:
        return self.packet is not None and self.repacked == self.raw

    def first_difference(self) -> int:
        return next(
            (i for i, (a, b) in enumerate(zip(self.raw, self.repacked, strict=False)) if a != b),
            min(len(self.raw), len(self.repacked)),
        )


class Recorder:
    """Wraps the library's packet reader to keep the bytes of every packet LFS sends."""

    def __init__(self) -> None:
        self.received: list[Received] = []
        self.log: list[str] = []

    def unpack(self, data: bytes) -> InSimPacket:
        item = Received(raw=bytes(data))
        self.received.append(item)
        try:
            item.packet = unpack_insim(data)
        except Exception as error:
            item.error = f"{type(error).__name__}: {error}"
            raise
        try:
            item.repacked = item.packet.pack()
        except Exception as error:
            item.error = f"pack() failed: {type(error).__name__}: {error}"
            return item.packet
        try:
            item.same_content = unpack_insim(item.repacked) == item.packet
        except Exception as error:
            item.error = f"reading the repacked bytes failed: {type(error).__name__}: {error}"
        return item.packet

    def emit(self, record: logging.LogRecord) -> None:
        self.log.append(f"{record.levelname} {record.getMessage()}")


class _LogHandler(logging.Handler):
    def __init__(self, recorder: Recorder) -> None:
        super().__init__(logging.INFO)
        self.recorder = recorder

    def emit(self, record: logging.LogRecord) -> None:
        self.recorder.emit(record)


def sent_packets() -> list[InSimPacket]:
    requests: list[InSimPacket] = [
        IS_TINY(ReqI=FIRST_REQI + i, SubT=sub) for i, sub in enumerate(REQUESTS)
    ]
    messages: list[InSimPacket] = [
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


def _plain(value: Any) -> Any:
    """A JSON-friendly copy of a field: nested structures become dicts."""
    if isinstance(value, bool | int | float | str) or value is None:
        return value
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    return repr(value)


def describe(packet: InSimPacket | None) -> dict[str, Any]:
    if packet is None:
        return {}
    plain: dict[str, Any] = _plain(packet)
    return plain


def report(recorder: Recorder, sent: list[InSimPacket], ver_seen: bool) -> dict[str, Any]:
    by_reqi = {item.raw[2] for item in recorder.received}  # ReqI is the third byte
    answered = {sub.name: (FIRST_REQI + i) in by_reqi for i, sub in enumerate(REQUESTS)}
    counts = Counter(item.name for item in recorder.received)
    return {
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lfs_insim": lfs_insim.__version__,
        "connected": ver_seen,
        "received_count": dict(sorted(counts.items())),
        "unreadable": [
            {"raw": item.raw.hex(" "), "error": item.error}
            for item in recorder.received
            if item.packet is None
        ],
        # A failure: the library writes the packet back with other content than it read.
        "content_changes": [
            {"packet": item.name, "raw": item.raw.hex(" "), "error": item.error}
            for item in recorder.received
            if item.packet is not None and not item.same_content
        ],
        # Not a failure, but worth a look: same content, other bytes. Expected for text (LFS
        # sends ^L page changes that the str does not keep, and zeros after the text).
        "other_bytes": [
            {
                "packet": item.name,
                "first_difference": item.first_difference(),
                "raw": item.raw.hex(" "),
                "repacked": item.repacked.hex(" "),
                "error": item.error,
            }
            for item in recorder.received
            if item.same_content and not item.same_bytes
        ],
        "requests_answered": answered,
        "sent": [type(packet).__name__ for packet in sent],
        "log": recorder.log,
        "packets": [{"packet": item.name, **describe(item.packet)} for item in recorder.received],
    }


def summary(data: dict[str, Any]) -> str:
    lines = [f"connected: {data['connected']}"]
    lines.append("received: " + ", ".join(f"{k} x{v}" for k, v in data["received_count"].items()))
    unanswered = [name for name, ok in data["requests_answered"].items() if not ok]
    lines.append("requests without answer: " + (", ".join(unanswered) or "none"))
    lines.append(f"unreadable packets: {len(data['unreadable'])}")
    for item in data["unreadable"]:
        lines.append(f"  {item['error']}  [{item['raw']}]")
    lines.append(f"packets written back with other content: {len(data['content_changes'])}")
    for item in data["content_changes"]:
        lines.append(f"  {item['packet']} {item['error']}  [{item['raw']}]")
    other = Counter(item["packet"] for item in data["other_bytes"])
    lines.append(
        "same content, other bytes (see the report): "
        + (", ".join(f"{k} x{v}" for k, v in sorted(other.items())) or "none")
    )
    warnings = [line for line in data["log"] if not line.startswith("INFO")]
    lines.append(f"library warnings and errors: {len(warnings)}")
    lines.extend(f"  {line}" for line in warnings)
    return "\n".join(lines)


async def live(port: int, seconds: float, wait: float, exit_lfs: bool) -> dict[str, Any]:
    recorder = Recorder()
    logging.getLogger("lfs_insim").addHandler(_LogHandler(recorder))
    logging.getLogger("lfs_insim").setLevel(logging.INFO)
    lfs_insim._stream.unpack_insim = recorder.unpack  # type: ignore[attr-defined]

    flags = ISF.LOCAL | ISF.CON | ISF.MCI | ISF.HLV | ISF.OBH  # in a race: positions, contacts
    insim = InSim(name="lfs_insim live", port=port, flags=flags, interval_ms=500)
    accepted = asyncio.Event()
    sent = sent_packets()

    @insim.on(IS_VER)
    def version(packet: IS_VER) -> None:
        accepted.set()

    async with insim:
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
    args = parser.parse_args()
    data = asyncio.run(live(args.port, args.seconds, args.wait, args.exit))
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / time.strftime("live_%Y%m%d_%H%M%S.json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(summary(data))
    print(f"report: {path}")
    ok = data["connected"] and not data["unreadable"] and not data["content_changes"]
    return 0 if ok else 1


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(main())
