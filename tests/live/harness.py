"""What the live tests against a real LFS share (W11.2). Not collected by pytest: it needs the game.

Every packet LFS sends goes through a Recorder, which keeps its bytes, reads it with the library,
packs it again and reads that: a packet written back with other content means the library reads or
writes it wrongly. Every packet the test sends is packed and read back the same way.

A group script (group_a.py...) opens a `Session`, sets up a situation (LFS commands by InSim, keys
and clicks with tests/lfs_screen.ps1), waits for what LFS must send (`expect`) and records checks.
`finish()` writes a JSON report to tests/live_reports/ (ignored by git: it holds player names) and
prints a summary: the checks, what was seen in each direction (for docs/dev/COVERAGE.md) and any
packet read or written wrongly.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
from collections import Counter
from collections.abc import Callable
from enum import IntEnum
from pathlib import Path
from typing import Any, TypeVar

import lfs_insim
import lfs_insim._stream
from lfs_insim import InSim, OutGauge, OutSim
from lfs_insim._udp import _UDPSource
from lfs_insim.packets import IS_SMALL, IS_TINY, IS_TTC, IS_VER, SMALL, TINY, TTC
from lfs_insim.packets._directions import InstructionPacket
from lfs_insim.packets._structure import InSimPacket, Structure, unpack_insim

TESTS = Path(__file__).resolve().parent.parent
REPORTS = TESTS / "live_reports"
SCREEN = TESTS / "lfs_screen.ps1"
KEPT_PER_TYPE = 20  # packets of each type written whole to the report (MCI and UDP ones abound)

P = TypeVar("P", bound=Structure)
_SUBTYPES: dict[type[Any], type[IntEnum]] = {IS_TINY: TINY, IS_SMALL: SMALL, IS_TTC: TTC}


def name_of(packet: Structure) -> str:
    """'IS_NPL', or the subtype for IS_TINY / IS_SMALL / IS_TTC: 'TINY_REPLY'."""
    subtypes = _SUBTYPES.get(type(packet))
    if subtypes is None:
        return type(packet).__name__
    sub = packet.SubT  # type: ignore[attr-defined]
    try:
        return f"{subtypes.__name__}_{subtypes(sub).name}"
    except ValueError:
        return f"{subtypes.__name__}_{sub}"


@dataclasses.dataclass
class Received:
    """One packet as LFS sent it, and what the library made of it."""

    raw: bytes
    source: str = "InSim"
    packet: Structure | None = None
    error: str = ""
    repacked: bytes = b""
    same_content: bool = False
    """Packing it again and reading that gives an equal packet (bytes may differ: see report)."""

    @property
    def name(self) -> str:
        if self.packet is not None:
            return name_of(self.packet)
        return f"type {self.raw[1]}" if self.source == "InSim" else f"{self.source} datagram"

    @property
    def same_bytes(self) -> bool:
        return self.packet is not None and self.repacked == self.raw

    def first_difference(self) -> int:
        return next(
            (i for i, (a, b) in enumerate(zip(self.raw, self.repacked, strict=False)) if a != b),
            min(len(self.raw), len(self.repacked)),
        )


class Recorder:
    """Wraps the library's packet readers to keep the bytes of every packet LFS sends."""

    def __init__(self) -> None:
        self.received: list[Received] = []
        self.log: list[str] = []

    def unpack(self, data: bytes) -> InSimPacket:
        packet = self.read(data, unpack_insim, "InSim")
        assert isinstance(packet, InSimPacket)
        return packet

    def read(self, data: bytes, reader: Callable[[bytes], Structure], source: str) -> Structure:
        """Read with the library's own reader, then pack the result and read it again."""
        item = Received(raw=bytes(data), source=source)
        self.received.append(item)
        try:
            item.packet = reader(data)
        except Exception as error:
            item.error = f"{type(error).__name__}: {error}"
            raise
        try:
            item.repacked = item.packet.pack()
        except Exception as error:
            item.error = f"pack() failed: {type(error).__name__}: {error}"
            return item.packet
        try:
            item.same_content = reader(item.repacked) == item.packet
        except Exception as error:
            item.error = f"reading the repacked bytes failed: {type(error).__name__}: {error}"
        return item.packet

    def install(self) -> None:
        """Read every InSim packet through this recorder, and keep the library's log."""
        self._handler = _LogHandler(self)
        lfs_insim._stream.unpack_insim = self.unpack  # type: ignore[attr-defined]
        logger = logging.getLogger("lfs_insim")
        logger.addHandler(self._handler)
        logger.setLevel(logging.INFO)

    def uninstall(self) -> None:
        """Undo install() (for the pytest test of this module)."""
        lfs_insim._stream.unpack_insim = unpack_insim  # type: ignore[attr-defined]
        logging.getLogger("lfs_insim").removeHandler(self._handler)


class _LogHandler(logging.Handler):
    def __init__(self, recorder: Recorder) -> None:
        super().__init__(logging.INFO)
        self.recorder = recorder

    def emit(self, record: logging.LogRecord) -> None:
        self.recorder.log.append(f"{record.levelname} {record.getMessage()}")


class _Recorded(_UDPSource):
    """An OutSim or OutGauge whose packets also go through the Recorder."""

    recorder: Recorder

    def _read(self, data: bytes) -> Structure:
        return self.recorder.read(data, super()._read, type(self).__name__.removeprefix("Live"))


class LiveOutGauge(_Recorded, OutGauge):
    pass


class LiveOutSim(_Recorded, OutSim):
    pass


@dataclasses.dataclass
class Sent:
    """One packet the test sent, and whether reading its bytes gives it back."""

    packet: InSimPacket
    error: str = ""

    @property
    def name(self) -> str:
        return name_of(self.packet)


class LiveInSim(InSim):
    """An InSim that keeps every packet it sends (all sending goes through _write)."""

    sent_log: list[Sent]

    def _write(self, packets: tuple[InstructionPacket, ...]) -> None:
        for packet in packets:
            item = Sent(packet)
            try:
                if unpack_insim(packet.pack()) != packet:
                    item.error = "reading its bytes gives another packet"
            except Exception as error:
                item.error = f"{type(error).__name__}: {error}"
            self.sent_log.append(item)
        super()._write(packets)


@dataclasses.dataclass
class Check:
    name: str
    ok: bool | None  # None: skipped (the situation could not be set up)
    detail: str = ""

    @property
    def status(self) -> str:
        return {True: "PASS", False: "FAIL", None: "SKIP"}[self.ok]


class ScreenRefused(RuntimeError):
    """LFS was not the window in front: lfs_screen.ps1 sent nothing. The test stops."""


class Session:
    """One connection to the real LFS for a group script: wait, check, drive the screen, report."""

    def __init__(
        self,
        group: str,
        *,
        host: str = "127.0.0.1",
        port: int = 29999,
        flags: int = 0,
        interval_ms: int = 0,
        udp_port: int = 0,
        recorder: Recorder | None = None,
    ):
        """udp_port: where SMALL_SSP / SSG make LFS send OutSim / OutGauge (InSim's udp_port).
        recorder: another session's, to put both connections in one report."""
        self.group = group
        self.port = port
        if recorder is None:
            recorder = Recorder()
            recorder.install()
        self.recorder = recorder
        self.insim = LiveInSim(
            name=f"live {group}",
            host=host,
            port=port,
            flags=flags,
            interval_ms=interval_ms,
            udp_port=udp_port,
        )
        self.insim.sent_log = []
        self.checks: list[Check] = []
        self.notes: list[str] = []
        self.version: IS_VER | None = None
        self._accepted = asyncio.Event()

        @self.insim.on(IS_VER)
        def version(packet: IS_VER) -> None:
            if self.version is None:
                self.version = packet
            self._accepted.set()

    async def __aenter__(self) -> Session:
        await self.insim.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.insim.__aexit__(None, None, None)

    async def connected(self, wait: float = 30) -> bool:
        """Wait for LFS to accept the connection (IS_VER)."""
        try:
            await asyncio.wait_for(self._accepted.wait(), wait)
        except TimeoutError:
            return False
        return True

    def mark(self) -> int:
        """A point in time: `expect(..., since=mark)` looks only at what came after it."""
        return len(self.recorder.received)

    def seen(self, cls: type[P], since: int = 0) -> list[P]:
        """The packets of a type received since a mark, in order."""
        return [
            item.packet for item in self.recorder.received[since:] if isinstance(item.packet, cls)
        ]

    async def expect(
        self,
        cls: type[P],
        where: Callable[[P], bool] | None = None,
        *,
        since: int | None = None,
        timeout: float = 10.0,
    ) -> P | None:
        """The first packet of a type (that `where` accepts) since a mark (default: now)."""
        start = self.mark() if since is None else since
        deadline = time.monotonic() + timeout
        while True:
            for packet in self.seen(cls, start):
                if where is None or where(packet):
                    return packet
            if time.monotonic() >= deadline:
                return None
            await asyncio.sleep(0.05)

    def check(self, name: str, ok: bool | None, detail: str = "") -> bool:
        self.checks.append(Check(name, ok, detail))
        print(f"  {Check(name, ok).status} {name}" + (f": {detail}" if detail else ""))
        return bool(ok)

    async def expect_check(
        self,
        name: str,
        cls: type[P],
        where: Callable[[P], bool] | None = None,
        *,
        since: int | None = None,
        timeout: float = 10.0,
        show: Callable[[P], str] = repr,
    ) -> P | None:
        """`expect` and record the result as a check."""
        packet = await self.expect(cls, where, since=since, timeout=timeout)
        detail = show(packet) if packet is not None else f"no {cls.__name__} in {timeout:g} s"
        self.check(name, packet is not None, detail)
        return packet

    def note(self, text: str) -> None:
        self.notes.append(text)
        print(f"  note: {text}")

    async def screen(
        self,
        *,
        keys: str = "",
        then: str = "",
        at: tuple[float, float] | None = None,
        wait: int = 1500,
    ) -> None:
        """Type or click into LFS with lfs_screen.ps1 (which also leaves a screenshot).

        at: where to click, as fractions (0 to 1) of LFS's window, full screen or windowed.

        Raises ScreenRefused if LFS was not in front: then nothing was sent, and the test stops
        rather than type into someone else's window.
        """
        args = ["-Wait", str(wait)]
        if keys:
            args += ["-Keys", keys]
        if then:
            args += ["-Then", then]
        if at is not None:
            args += ["-FX", str(at[0]), "-FY", str(at[1])]
        process = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCREEN), *args
        )
        code = await process.wait()
        if code == 2:
            raise ScreenRefused("LFS was not the window in front: nothing was sent")
        if code != 0:
            raise RuntimeError(f"lfs_screen.ps1 ended with {code}")

    def report(self) -> dict[str, Any]:
        return {
            "group": self.group,
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lfs_insim": lfs_insim.__version__,
            "lfs": None
            if self.version is None
            else f"{self.version.Product} {self.version.Version}",
            "checks": [dataclasses.asdict(c) | {"status": c.status} for c in self.checks],
            "notes": self.notes,
            "sent_count": dict(sorted(Counter(item.name for item in self.insim.sent_log).items())),
            "sent_errors": [
                {"packet": item.name, "error": item.error, "fields": _plain(item.packet)}
                for item in self.insim.sent_log
                if item.error
            ],
            **received_report(self.recorder),
        }

    def finish(self) -> int:
        """Write the report, print the summary; the exit code: 0 if nothing failed."""
        data = self.report()
        REPORTS.mkdir(exist_ok=True)
        path = REPORTS / time.strftime(f"{self.group}_%Y%m%d_%H%M%S.json")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(summary(data))
        print(f"report: {path}")
        return 0 if passed(data) else 1


def passed(data: dict[str, Any]) -> bool:
    return (
        all(check["ok"] is not False for check in data.get("checks", []))
        and not data["unreadable"]
        and not data["content_changes"]
        and not data.get("sent_errors")
    )


def _plain(value: Any) -> Any:
    """A JSON-friendly copy of a field: nested structures become dicts."""
    if isinstance(value, bool | int | float | str) or value is None:
        return value
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    return repr(value)


def kept(received: list[Received]) -> list[Received]:
    seen: Counter[str] = Counter()
    result = []
    for item in received:
        seen[item.name] += 1
        if seen[item.name] <= KEPT_PER_TYPE:
            result.append(item)
    return result


def received_report(recorder: Recorder) -> dict[str, Any]:
    """What LFS sent: counts, packets read or written wrongly, and the first ones of each type."""
    counts = Counter(item.name for item in recorder.received)
    return {
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
        "log": recorder.log,
        "packets": [
            {"packet": item.name, **(_plain(item.packet) or {})} for item in kept(recorder.received)
        ],
    }


def summary(data: dict[str, Any]) -> str:
    lines = []
    if "group" in data:
        lines.append(f"group {data['group']}, LFS {data['lfs']}, lfs_insim {data['lfs_insim']}")
        statuses = Counter(check["status"] for check in data["checks"])
        lines.append("checks: " + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items())))
        lines.extend(
            f"  {check['status']} {check['name']}: {check['detail']}"
            for check in data["checks"]
            if check["status"] != "PASS"
        )
        lines.append("sent: " + ", ".join(f"{k} x{v}" for k, v in data["sent_count"].items()))
        lines.append(f"sent packets that read back wrong: {len(data['sent_errors'])}")
        lines.extend(f"  {item['packet']}: {item['error']}" for item in data["sent_errors"])
    lines.append("received: " + ", ".join(f"{k} x{v}" for k, v in data["received_count"].items()))
    lines.append(f"unreadable packets: {len(data['unreadable'])}")
    lines.extend(f"  {item['error']}  [{item['raw']}]" for item in data["unreadable"])
    lines.append(f"packets written back with other content: {len(data['content_changes'])}")
    lines.extend(
        f"  {item['packet']} {item['error']}  [{item['raw']}]" for item in data["content_changes"]
    )
    other = Counter(item["packet"] for item in data["other_bytes"])
    lines.append(
        "same content, other bytes (see the report): "
        + (", ".join(f"{k} x{v}" for k, v in sorted(other.items())) or "none")
    )
    warnings = [line for line in data["log"] if not line.startswith("INFO")]
    lines.append(f"library warnings and errors: {len(warnings)}")
    lines.extend(f"  {line}" for line in warnings)
    return "\n".join(lines)
