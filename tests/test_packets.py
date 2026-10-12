"""The generated packets: round trips, sizes against the specification, and hand-made bytes."""

import itertools
import re
import struct
from dataclasses import replace
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

import pytest

from lfs_insim import packets
from lfs_insim.packets import (
    CCI,
    IS_ISI,
    IS_MAL,
    IS_MCI,
    IS_MSO,
    IS_MST,
    IS_SLC,
    IS_TINY,
    ISF,
    ISP,
    OG,
    OSO,
    TINY,
    CompCar,
    OutGaugePack,
    OutSimPack,
    OutSimPack2,
    OutSimWheel,
    PacketError,
    Vec,
    Vector,
)
from lfs_insim.packets import _codec as c
from lfs_insim.packets._codec import InSimPacket, OptionalParts, Structure, unpack_insim

CACHE = Path(__file__).resolve().parent.parent / "spec" / "cache"
# OutSim and OutGauge: no Size field, so their sizes are checked one by one below.
OUTSIDE_INSIM = {
    "OutSimPack",
    "OutSimMain",
    "OutSimInputs",
    "OutSimWheel",
    "OutSimPack2",
    "OutGaugePack",
}
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
    if isinstance(codec, c.CarName):
        return "XRT" if n % 2 else f"{n:06X}"
    if isinstance(codec, c.SkinID):
        return f"{n:06X}"
    if isinstance(codec, c.IPv4):
        return IPv4Address(f"10.0.0.{n % 250}")
    if isinstance(codec, c.Nested):
        return sample(codec.cls)
    if isinstance(codec, c.Array):
        return [sample_value(codec.item) for _ in range(codec.count)]
    if isinstance(codec, c.TailArray):
        return [sample_value(codec.item) for _ in range(2)]
    if isinstance(codec, (c.Optional, c.When)):
        return sample_value(codec.item)
    if isinstance(codec, c.Options):
        return sum(OSO)  # every part: what OutSim Opts 1ff sends
    raise AssertionError(f"no sample for {codec!r}")


def sample(cls: type[Structure]) -> Any:
    return cls(**{name: sample_value(co) for name, co in cls._LAYOUT if co.is_field})


def unpack(cls: type[Structure], data: bytes, instance: Any) -> Any:
    """cls.unpack(data), passing the options when the layout depends on them."""
    if issubclass(cls, OptionalParts):
        return cls.unpack(data, instance.OSOpts)
    return cls.unpack(data)


def test_every_packet_type_is_generated() -> None:
    generated = {cls._TYPE for cls in PACKETS}
    missing = {isp.name for isp in ISP if isp not in generated} - {"NONE"}
    assert missing == set()
    assert len(PACKETS) == len(generated)  # one class per type


@pytest.mark.parametrize("cls", CLASSES, ids=lambda cls: cls.__name__)
def test_round_trip(cls: type[Structure]) -> None:
    for instance in (cls(), sample(cls)):
        data = instance.pack()
        assert unpack(cls, data, instance) == instance
        if isinstance(instance, InSimPacket):
            assert len(data) % 4 == 0 and data[0] * 4 == len(data)
            assert unpack_insim(data) == instance


def spec_sizes() -> dict[str, tuple[int, int | None]]:
    """struct name -> (size when empty, size of each extra item or None) from the comments."""
    import spec_parser

    spec = spec_parser.parse((CACHE / "InSim.txt").read_text(encoding="utf-8"), "InSim.txt")
    sizes: dict[str, tuple[int, int | None]] = {}
    for item in spec.structs.values():
        size = item.fields[0].comment if item.fields[0].name == "Size" else ""
        if match := re.match(r"^(\d+) \+ (?:Num\w+ \* (\d+)|(\d+) \* \(number)", size):
            sizes[item.name] = (int(match[1]), int(match[2] or match[3]))
        elif match := re.match(r"^(\d+) \+ TEXT_SIZE", size):
            sizes[item.name] = (int(match[1]) + 4, None)  # empty text still takes 4 bytes
        elif match := re.match(r"^(\d+)\b", size) or re.search(r"(\d+) bytes", item.comment):
            sizes[item.name] = (int(match[1]), None)  # "44", or "Car info in 28 bytes"
    return sizes


@pytest.mark.skipif(not (CACHE / "InSim.txt").exists(), reason="run scripts/fetch_spec.py first")
def test_sizes_match_the_specification() -> None:
    sizes = spec_sizes()
    unchecked = {cls.__name__ for cls in CLASSES} - sizes.keys() - OUTSIDE_INSIM
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


# CName is an official car ("XFG") or, for a mod, its SkinID: a 32-bit unsigned whose hex digits
# are the skin ID shown by LFS (LFS forum). The mods below have bytes that are not valid cp1252
# (0x81, 0x8D, 0x90) or a zero in the middle, which plain text would lose.
@pytest.mark.parametrize(
    ("raw", "name"),
    [
        (b"XFG\0", "XFG"),
        (b"FZ5\0", "FZ5"),
        (bytes(4), ""),  # IS_SLC with no car selected
        ((0x5A1FB3).to_bytes(4, "little"), "5A1FB3"),
        ((0x8D0A90).to_bytes(4, "little"), "8D0A90"),
        ((0x100081).to_bytes(4, "little"), "100081"),
        ((0x5A0012).to_bytes(4, "little"), "5A0012"),
    ],
)
def test_car_name_is_an_official_car_or_a_mod_skin_id(raw: bytes, name: str) -> None:
    data = bytes([2, ISP.SLC, 0, 1]) + raw
    packet = IS_SLC.unpack(data)
    assert packet.CName == name
    assert packet.pack() == data


def test_car_name_accepts_lowercase_skin_ids() -> None:
    assert IS_SLC(CName="5a1fb3").pack() == IS_SLC(CName="5A1FB3").pack()


@pytest.mark.parametrize("name", ["XFGT", "XF", "5A1FB", "5A1FBZ", "X G", "5A5A5A"])
def test_car_name_rejects_what_is_neither(name: str) -> None:
    # 5A5A5A would be read back as the official car "ZZZ": LFS never issues such a SkinID.
    with pytest.raises(PacketError):
        IS_SLC(CName=name).pack()


def test_mal_skin_ids_look_like_car_names() -> None:
    packet = IS_MAL(SkinID=["5A1FB3", "000001"])
    data = packet.pack()
    assert data[3] == 2  # NumM
    assert data[8:] == struct.pack("<II", 0x5A1FB3, 1)
    assert IS_MAL.unpack(data) == packet
    with pytest.raises(PacketError):
        IS_MAL(SkinID=["XFG"]).pack()


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


def test_outsim_and_outgauge_sizes() -> None:
    assert len(OutSimPack().pack()) == 64
    assert len(OutSimPack(ID=1).pack()) == 68  # "optional - only if OutSim ID is specified"
    assert len(OutGaugePack().pack()) == 92
    assert len(OutGaugePack(ID=1).pack()) == 96
    assert len(OutSimWheel().pack()) == 40  # "struct OutSimWheel // 10 ints"
    assert len(sample(OutSimPack2).pack()) == 280  # "for all fields set OutSim Opts to 1ff"


def test_outsim2_size_of_each_part() -> None:
    parts = {
        OSO.HEADER: 4,
        OSO.ID: 4,
        OSO.TIME: 4,
        OSO.MAIN: 60,
        OSO.INPUTS: 20,
        OSO.DRIVE: 12,
        OSO.DISTANCE: 8,
        OSO.WHEELS: 160,
        OSO.EXTRA_1: 8,
    }
    assert set(parts) == set(OSO)
    full = sample(OutSimPack2)
    for option, size in parts.items():
        values = {
            name: getattr(full, name) if co.option == option else None
            for name, co in OutSimPack2._LAYOUT
            if isinstance(co, c.When) and co.is_field
        }
        packet = OutSimPack2(OSOpts=option, **values)
        assert len(packet.pack()) == size, option.name
        assert OutSimPack2.unpack(packet.pack(), option) == packet


def test_outsim2_from_hand_made_bytes() -> None:
    options = OSO.HEADER | OSO.TIME | OSO.DISTANCE
    data = b"LFST" + struct.pack("<Iff", 1234, 1.5, 2.5)
    expected = OutSimPack2(OSOpts=options, Time=1234, CurrentLapDist=1.5, IndexedDistance=2.5)
    assert OutSimPack2.unpack(data, options) == expected
    assert expected.pack() == data


def test_outsim2_needs_the_right_options() -> None:
    data = b"LFST" + struct.pack("<I", 1234)
    with pytest.raises(PacketError, match="options"):
        OutSimPack2.unpack(data)
    with pytest.raises(PacketError, match="too short"):  # one part more than was sent
        OutSimPack2.unpack(data, OSO.HEADER | OSO.TIME | OSO.ID)
    with pytest.raises(PacketError, match="give 4 bytes, but 8"):  # one part less
        OutSimPack2.unpack(data, OSO.HEADER)
    with pytest.raises(PacketError, match="LFST"):
        OutSimPack2.unpack(b"XXXX" + data[4:], OSO.HEADER | OSO.TIME)


def test_outsim2_values_must_match_the_options() -> None:
    with pytest.raises(PacketError, match="is set"):
        OutSimPack2(OSOpts=OSO.TIME).pack()  # Time missing
    with pytest.raises(PacketError, match="not set"):
        OutSimPack2(OSOpts=OSO.TIME, Time=1, ID=7).pack()  # ID given, OSO_ID not set


def test_outsim_from_hand_made_bytes() -> None:
    body = struct.pack("<I12f3i", 99, 0.0, 0.0, 1.0, 0.5, 0.25, 0.125, *[0.0] * 6, 65536, 0, -1)
    expected = OutSimPack(
        Time=99,
        AngVel=Vector(Z=1.0),
        Heading=0.5,
        Pitch=0.25,
        Roll=0.125,
        Pos=Vec(X=65536, Z=-1),
    )
    assert OutSimPack.unpack(body) == expected
    assert OutSimPack.unpack(body + struct.pack("<i", 5)) == replace(expected, ID=5)
    assert expected.pack() == body


def test_outgauge_from_hand_made_bytes() -> None:
    data = (
        struct.pack("<I4sHBB", 500, b"XRT\0", OG.KM | OG.BAR, 3, 7)
        + struct.pack("<7f", 30.0, 6000.0, 1.0, 90.0, 0.5, 4.0, 100.0)
        + struct.pack("<II3f", 0x3FF, 0x5, 1.0, 0.0, 0.0)
        + b"Fuel 50%".ljust(16, b"\0")
        + b"Brake 60:40".ljust(16, b"\0")
    )
    packet = OutGaugePack.unpack(data)
    assert (packet.Time, packet.Car, packet.Flags, packet.Gear, packet.PLID) == (
        500,
        "XRT",
        OG.KM | OG.BAR,
        3,
        7,
    )
    assert (packet.RPM, packet.ShowLights, packet.Display2, packet.ID) == (
        6000.0,
        5,
        "Brake 60:40",
        None,
    )
    assert packet.pack() == data
    assert OutGaugePack.unpack(data + struct.pack("<i", 2)).ID == 2
