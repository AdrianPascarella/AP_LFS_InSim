"""The generated packets: round trips, sizes against the specification, and hand-made bytes."""

import itertools
import re
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

import pytest

from lfs_insim import packets
from lfs_insim.packets import (
    CCI,
    IS_ISI,
    IS_MCI,
    IS_MSO,
    IS_MST,
    IS_TINY,
    ISF,
    ISP,
    TINY,
    CompCar,
    PacketError,
    Vec,
)
from lfs_insim.packets import _codec as c
from lfs_insim.packets._codec import InSimPacket, Structure, unpack_insim

CACHE = Path(__file__).resolve().parent.parent / "spec" / "cache"
CLASSES = [
    cls
    for cls in vars(packets).values()
    if isinstance(cls, type) and issubclass(cls, Structure) and cls not in (Structure,)
]
PACKETS = [cls for cls in CLASSES if issubclass(cls, InSimPacket)]
_counter = itertools.count(1)


def sample_value(codec: c.Codec) -> Any:
    """A value for a codec that differs from the default and from the other fields."""
    n = next(_counter)
    if isinstance(codec, c.Scalar):
        fmt = codec.struct.format[-1]
        if fmt == "f":
            return n + 0.5
        if fmt in "bh":
            return -(n % 100)
        return n % 200 + 1
    if isinstance(codec, c.Text):
        return (chr(ord("a") + n % 26) * codec.limit)[: max(1, codec.limit)]
    if isinstance(codec, c.TailText):
        return "hello" + str(n)
    if isinstance(codec, c.IPv4):
        return IPv4Address(f"10.0.0.{n % 250}")
    if isinstance(codec, c.Nested):
        return sample(codec.cls)
    if isinstance(codec, c.Array):
        return [sample_value(codec.item) for _ in range(codec.count)]
    if isinstance(codec, c.TailArray):
        return [sample_value(codec.item) for _ in range(2)]
    if isinstance(codec, c.Optional):
        return sample_value(codec.item)
    raise AssertionError(f"no sample for {codec!r}")


def sample(cls: type[Structure]) -> Any:
    return cls(**{name: sample_value(co) for name, co in cls._LAYOUT if co.is_field})


def test_every_packet_type_is_generated() -> None:
    generated = {cls._TYPE for cls in PACKETS}
    missing = {isp.name for isp in ISP if isp not in generated} - {"NONE"}
    assert missing == set()
    assert len(PACKETS) == len(generated)  # one class per type


@pytest.mark.parametrize("cls", CLASSES, ids=lambda cls: cls.__name__)
def test_round_trip(cls: type[Structure]) -> None:
    for instance in (cls(), sample(cls)):
        data = instance.pack()
        assert cls.unpack(data) == instance
        if isinstance(instance, InSimPacket):
            assert len(data) % 4 == 0 and data[0] * 4 == len(data)
            assert unpack_insim(data) == instance


def spec_sizes() -> dict[str, tuple[int, int | None]]:
    """struct name -> (size when empty, size of each extra item or None) from the comments."""
    import spec_parser

    spec = spec_parser.parse((CACHE / "InSim.txt").read_text(encoding="utf-8"), "InSim.txt")
    sizes: dict[str, tuple[int, int | None]] = {}
    for struct in spec.structs.values():
        size = struct.fields[0].comment if struct.fields[0].name == "Size" else ""
        if match := re.match(r"^(\d+) \+ (?:Num\w+ \* (\d+)|(\d+) \* \(number)", size):
            sizes[struct.name] = (int(match[1]), int(match[2] or match[3]))
        elif match := re.match(r"^(\d+) \+ TEXT_SIZE", size):
            sizes[struct.name] = (int(match[1]) + 4, None)  # empty text still takes 4 bytes
        elif match := re.match(r"^(\d+)\b", size) or re.search(r"(\d+) bytes", struct.comment):
            sizes[struct.name] = (int(match[1]), None)  # "44", or "Car info in 28 bytes"
    return sizes


@pytest.mark.skipif(not (CACHE / "InSim.txt").exists(), reason="run scripts/fetch_spec.py first")
def test_sizes_match_the_specification() -> None:
    sizes = spec_sizes()
    unchecked = {cls.__name__ for cls in CLASSES} - sizes.keys()
    # These declare no size anywhere in the specification.
    assert unchecked == {"ObjectInfo", "AIInputVal", "OSMain", "Vec", "Vector"}
    for name, (empty, per_item) in sizes.items():
        cls = getattr(packets, name)
        assert len(cls().pack()) == empty, name
        if per_item is not None:
            field = next(n for n, co in cls._LAYOUT if isinstance(co, c.TailArray))
            one = cls(**{field: [sample_value(dict(cls._LAYOUT)[field].item)]})
            assert len(one.pack()) == empty + per_item + (-(empty + per_item) % 4), name


def test_variable_text_limits_from_the_specification() -> None:
    assert len(IS_MSO(Msg="x" * 127).pack()) == 136  # "12, 16, 20... 136 depending on Msg"
    with pytest.raises(PacketError):
        IS_MSO(Msg="x" * 128).pack()


def test_keep_alive_bytes() -> None:
    # "the keep alive packet": Size 4 (1 in units of 4), Type ISP_TINY, ReqI 0, SubT TINY_NONE
    assert IS_TINY(SubT=TINY.NONE).pack() == bytes([1, 3, 0, 0])
    assert IS_TINY.unpack(bytes([1, 3, 7, TINY.NCN])) == IS_TINY(ReqI=7, SubT=TINY.NCN)


def test_isi_bytes() -> None:
    packet = IS_ISI(
        ReqI=1,
        Flags=ISF.LOCAL | ISF.MCI,
        InSimVer=10,
        Prefix=ord("!"),
        Interval=100,
        Admin="pw",
        IName="app",
    )
    expected = (
        bytes([11, 1, 1, 0])  # Size 44 / 4, ISP_ISI, ReqI, Zero
        + bytes([0, 0, 0x24, 0])  # UDPPort 0, Flags = 4 | 0x20
        + bytes([10, ord("!"), 100, 0])  # InSimVer, Prefix, Interval
        + b"pw".ljust(16, b"\0")
        + b"app".ljust(16, b"\0")
    )
    assert packet.pack() == expected


def test_mst_text_is_zero_terminated() -> None:
    data = IS_MST(Msg="/msg hi").pack()
    assert data[:4] == bytes([17, ISP.MST, 0, 0]) and data[4:12] == b"/msg hi\0"


def test_mci_from_hand_made_bytes() -> None:
    data = b"".join(
        bytes(part)
        for part in (
            [8, ISP.MCI, 0, 1],  # Size (4 + 28) / 4, Type, ReqI, NumC
            [2, 1, 3, 0, 5, 1, CCI.FIRST, 0],  # Node 0x0102, Lap 3, PLID 5, Position 1, Info, Sp3
            [0, 0, 1, 0, 0, 0, 0xFF, 0xFF, 0, 0, 0, 0],  # X 65536, Y -65536, Z 0
            [0, 0x80, 0, 0, 0, 0x40, 0xFF, 0xFF],  # Speed 32768, Direction 0, Heading, AngVel -1
        )
    )
    expected = CompCar(
        Node=0x0102,
        Lap=3,
        PLID=5,
        Position=1,
        Info=CCI.FIRST,
        X=65536,
        Y=-65536,
        Z=0,
        Speed=32768,
        Direction=0,
        Heading=16384,
        AngVel=-1,
    )
    assert IS_MCI.unpack(data) == IS_MCI(Info=[expected])
    assert IS_MCI(Info=[expected]).pack() == data


def test_vectors_inside_packets() -> None:
    assert isinstance(packets.IS_CPP().Pos, Vec)
