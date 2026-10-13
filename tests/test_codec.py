"""The packing core, tested with hand-written classes that copy the shapes in the specification.

The generated classes (W2.4) are tested separately; these pin down each codec on its own.
"""

from dataclasses import dataclass, field
from ipaddress import IPv4Address

import pytest

from lfs_insim.packets import PacketError, Vec
from lfs_insim.packets._codec import (
    SIZE,
    TYPE,
    Array,
    Count,
    IPv4,
    Nested,
    Optional,
    Pad,
    Scalar,
    TailArray,
    TailText,
    Text,
)
from lfs_insim.packets._structure import (
    InSimPacket,
    Structure,
    factory,
    register,
    unpack_insim,
)

B, H = Scalar("B"), Scalar("H")


@dataclass(kw_only=True)
class TINY(InSimPacket):  # struct IS_TINY: Size, Type, ReqI, SubT
    ReqI: int = 0
    SubT: int = 0

    _TYPE = 201
    _LAYOUT = (("Size", SIZE), ("Type", TYPE), ("ReqI", B), ("SubT", B))


@dataclass(kw_only=True)
class MST(InSimPacket):  # struct IS_MST: fixed char Msg[64], last byte must be zero
    ReqI: int = 0
    Msg: str = ""

    _TYPE = 202
    _LAYOUT = (("Size", SIZE), ("Type", TYPE), ("ReqI", B), ("Zero", Pad(1)), ("Msg", Text(64)))


@dataclass(kw_only=True)
class MSO(InSimPacket):  # struct IS_MSO: variable size text at the end
    UCID: int = 0
    Msg: str = ""

    _TYPE = 203
    _LAYOUT = (
        ("Size", SIZE),
        ("Type", TYPE),
        ("ReqI", Pad(1)),
        ("Zero", Pad(1)),
        ("UCID", B),
        ("Sp", Pad(3)),
        ("Msg", TailText(128)),
    )


@dataclass(kw_only=True)
class Car(Structure):  # like NodeLap: 6 bytes
    Node: int = 0
    Lap: int = 0
    PLID: int = 0
    Position: int = 0

    _LAYOUT = (("Node", H), ("Lap", H), ("PLID", B), ("Position", B))


@dataclass(kw_only=True)
class NLP(InSimPacket):  # struct IS_NLP: NumP counts Info; padded to a multiple of 4
    ReqI: int = 0
    Info: list[Car] = field(default_factory=list)

    _TYPE = 204
    _LAYOUT = (
        ("Size", SIZE),
        ("Type", TYPE),
        ("ReqI", B),
        ("NumP", Count("B", of="Info")),
        ("Info", TailArray(Nested(Car), 48, count="NumP")),
    )


@dataclass(kw_only=True)
class AIC(InSimPacket):  # struct IS_AIC: no counter, the items fill the packet
    PLID: int = 0
    Inputs: list[int] = field(default_factory=list)

    _TYPE = 205
    _LAYOUT = (
        ("Size", SIZE),
        ("Type", TYPE),
        ("ReqI", Pad(1)),
        ("PLID", B),
        ("Inputs", TailArray(Scalar("I"), 20)),
    )


@dataclass(kw_only=True)
class Mixed(Structure):  # fixed arrays, nested structure, unterminated text, IP, optional tail
    Tyres: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    Pos: Vec = field(default_factory=factory(Vec))
    Plate: str = ""
    IP: IPv4Address = field(default_factory=lambda: IPv4Address(0))
    ID: int | None = None

    _LAYOUT = (
        ("Tyres", Array(B, 4)),
        ("Pos", Nested(Vec)),
        ("Plate", Text(8, terminated=False)),
        ("IP", IPv4()),
        ("ID", Optional(Scalar("i"))),
    )


# Types 201+ are unused by LFS, so these never replace the real packets in unpack_insim().
register(TINY, MST, MSO, NLP, AIC)


def test_a_type_belongs_to_one_class() -> None:
    register(TINY)  # registering the same class again is harmless

    @dataclass(kw_only=True)
    class Other(InSimPacket):
        _TYPE = 201

    with pytest.raises(ValueError, match="type 201 already belongs to TINY"):
        register(Other)


def test_header_is_filled_in() -> None:
    assert TINY(ReqI=1, SubT=0).pack() == bytes([1, 201, 1, 0])  # Size is in units of 4 bytes
    assert TINY.unpack(bytes([1, 201, 1, 4])) == TINY(ReqI=1, SubT=4)


def test_fixed_text_and_padding() -> None:
    data = MST(Msg="/msg hi").pack()
    assert len(data) == 68
    assert data[:4] == bytes([17, 202, 0, 0])
    assert data[4:12] == b"/msg hi\0"
    assert MST.unpack(data) == MST(Msg="/msg hi")


def test_fixed_text_too_long() -> None:
    with pytest.raises(PacketError, match="limit is 63"):
        MST(Msg="x" * 64).pack()
    assert Mixed(Plate="ABCDEFGH").pack()  # NO ZERO AT END: all 8 bytes may be used


def test_variable_text_is_zero_terminated_and_padded_to_4() -> None:
    data = MSO(UCID=2, Msg="abc").pack()
    assert data == bytes([3, 203, 0, 0, 2, 0, 0, 0]) + b"abc\0"
    data = MSO(Msg="abcd").pack()
    assert len(data) == 16 and data[8:] == b"abcd\0\0\0\0"
    assert MSO.unpack(data) == MSO(Msg="abcd")


def test_counted_array_sets_the_counter() -> None:
    packet = NLP(Info=[Car(Node=1, Lap=2, PLID=3, Position=1)])
    data = packet.pack()
    assert data == bytes([3, 204, 0, 1, 1, 0, 2, 0, 3, 1, 0, 0])  # 4 + 6, padded to 12
    assert NLP.unpack(data) == packet
    assert NLP.unpack(NLP().pack()) == NLP()


def test_uncounted_array_fills_the_packet() -> None:
    packet = AIC(PLID=5, Inputs=[1, 2])
    assert packet.pack() == bytes([3, 205, 0, 5, 1, 0, 0, 0, 2, 0, 0, 0])
    assert AIC.unpack(packet.pack()) == packet
    with pytest.raises(PacketError, match="at most 20"):
        AIC(Inputs=[0] * 21).pack()


def test_mixed_round_trip_and_optional_tail() -> None:
    packet = Mixed(
        Tyres=[1, 2, 3, 4], Pos=Vec(X=-1, Y=2, Z=3), Plate="AB", IP=IPv4Address("10.0.0.1")
    )
    data = packet.pack()
    assert len(data) == 4 + 12 + 8 + 4
    assert Mixed.unpack(data) == packet
    assert Mixed.unpack(data + bytes([7, 0, 0, 0])).ID == 7
    with pytest.raises(PacketError, match="expected 4 items"):
        Mixed(Tyres=[1]).pack()


def test_values_out_of_range_are_rejected() -> None:
    with pytest.raises(PacketError, match="does not fit"):
        TINY(SubT=256).pack()


def test_unpack_any_chooses_the_class_by_type() -> None:
    assert unpack_insim(bytes([1, 201, 0, 0])) == TINY()
    assert unpack_insim(MSO(Msg="hi").pack()) == MSO(Msg="hi")
    with pytest.raises(PacketError, match="unknown packet type 250"):
        unpack_insim(bytes([1, 250, 0, 0]))


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"\x01\x03", "at least 4 bytes"),
        (bytes([2, 201, 0, 0]), "Size says 8 bytes"),
        (bytes([0, 201, 0, 0]), "Size says 0 bytes"),
        (bytes([1, 203, 0, 0]), "type 203 is not TINY"),
    ],
)
def test_malformed_bytes_raise_packet_error(data: bytes, message: str) -> None:
    with pytest.raises(PacketError, match=message):
        TINY.unpack(data)


def test_truncated_body_raises_packet_error() -> None:
    with pytest.raises(PacketError, match="too short"):
        MST.unpack(bytes([2, 202, 0, 0, 0, 0, 0, 0]))
