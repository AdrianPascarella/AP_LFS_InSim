"""Packing and unpacking of the packet classes (internal).

Every packet or structure class declares its binary layout as a tuple of (name, codec) pairs in
`_LAYOUT`, in wire order. The generated code (W2.4) writes those layouts from the specification;
this module is the only hand-written logic that turns them into bytes and back.

Codecs that are not dataclass fields (padding, Size, Type, counters) are filled in here, so a
user never sets them: `IS_MST(Msg="hello").pack()` is a complete packet.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from ipaddress import IPv4Address
from typing import Any, ClassVar, Self

from lfs_insim.packets import _text


class PacketError(ValueError):
    """Bytes that do not form a valid packet, or a packet that cannot be packed."""


class Codec:
    """One field of a layout. Subclasses define how a value becomes bytes and back."""

    is_field = True  # False = filled in by the library, not a dataclass field

    def pack(self, value: Any, packet: Any) -> bytes:
        raise NotImplementedError

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        raise NotImplementedError


class Scalar(Codec):
    """A number: struct format letter (B, H, h, I, i, f, b)."""

    def __init__(self, fmt: str) -> None:
        self.struct = struct.Struct("<" + fmt)

    def pack(self, value: Any, packet: Any) -> bytes:
        try:
            return self.struct.pack(value)
        except struct.error as error:
            raise PacketError(f"{value!r} does not fit in format {self.struct.format}") from error

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        end = offset + self.struct.size
        if end > len(data):
            raise PacketError("packet too short")
        return self.struct.unpack_from(data, offset)[0], end


class Pad(Codec):
    """Spare or Zero bytes: always written as zero, ignored when read."""

    is_field = False

    def __init__(self, size: int) -> None:
        self.size = size

    def pack(self, value: Any, packet: Any) -> bytes:
        return bytes(self.size)

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        if offset + self.size > len(data):
            raise PacketError("packet too short")
        return None, offset + self.size


class Text(Codec):
    """char[size]: text up to the first zero byte. `terminated` reserves the last byte for it."""

    def __init__(self, size: int, terminated: bool = True) -> None:
        self.size = size
        self.limit = size - 1 if terminated else size

    def pack(self, value: Any, packet: Any) -> bytes:
        raw = _text.encode(value)
        if len(raw) > self.limit:
            raise PacketError(f"text is {len(raw)} bytes long; the limit is {self.limit}")
        return raw.ljust(self.size, b"\0")

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        end = offset + self.size
        if end > len(data):
            raise PacketError("packet too short")
        return _text.decode(data[offset:end].split(b"\0", 1)[0]), end


class IPv4(Codec):
    """in_addr: 4 bytes, network order."""

    def pack(self, value: Any, packet: Any) -> bytes:
        return IPv4Address(value).packed

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        if offset + 4 > len(data):
            raise PacketError("packet too short")
        return IPv4Address(data[offset : offset + 4]), offset + 4


class Nested(Codec):
    """A structure inside another one (CompCar, Vec, ...)."""

    def __init__(self, cls: type[Structure]) -> None:
        self.cls = cls

    def pack(self, value: Any, packet: Any) -> bytes:
        if not isinstance(value, self.cls):
            raise PacketError(f"expected {self.cls.__name__}, got {type(value).__name__}")
        return value.pack()

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return self.cls._unpack_from(data, offset)


class Array(Codec):
    """A fixed number of items (Tyres[4], OSWheels[4]): the list must have exactly that many."""

    def __init__(self, item: Codec, count: int) -> None:
        self.item = item
        self.count = count

    def pack(self, value: Any, packet: Any) -> bytes:
        if len(value) != self.count:
            raise PacketError(f"expected {self.count} items, got {len(value)}")
        return b"".join(self.item.pack(item, packet) for item in value)

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        items = []
        for _ in range(self.count):
            item, offset = self.item.unpack(data, offset, values)
            items.append(item)
        return items, offset


class Count(Codec):
    """A counter (NumC, NumP, ...) that the library fills in from the length of a list field."""

    is_field = False

    def __init__(self, fmt: str, of: str) -> None:
        self.scalar = Scalar(fmt)
        self.of = of

    def pack(self, value: Any, packet: Any) -> bytes:
        return self.scalar.pack(len(getattr(packet, self.of)), packet)

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return self.scalar.unpack(data, offset, values)


class TailText(Codec):
    """Variable-size text at the end of a packet: zero-terminated, padded to a multiple of 4."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size

    def pack(self, value: Any, packet: Any) -> bytes:
        raw = _text.encode(value)
        if len(raw) > self.max_size - 1:
            raise PacketError(f"text is {len(raw)} bytes long; the limit is {self.max_size - 1}")
        size = len(raw) + 1
        return raw.ljust(size + (-size % 4), b"\0")

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return _text.decode(data[offset:].split(b"\0", 1)[0]), len(data)


class TailArray(Codec):
    """Variable number of items at the end of a packet.

    `count` names the Count field that holds how many there are; None means "as many as fit".
    """

    def __init__(self, item: Codec, max_count: int, count: str | None = None) -> None:
        self.item = item
        self.max_count = max_count
        self.count = count

    def pack(self, value: Any, packet: Any) -> bytes:
        if len(value) > self.max_count:
            raise PacketError(f"at most {self.max_count} items, got {len(value)}")
        return b"".join(self.item.pack(item, packet) for item in value)

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        items = []
        count = values[self.count] if self.count is not None else self.max_count
        for _ in range(min(count, self.max_count)):
            if self.count is None and offset >= len(data):
                break
            item, offset = self.item.unpack(data, offset, values)
            items.append(item)
        return items, offset


class Optional(Codec):
    """A trailing value that LFS only sends in some configurations (OutGauge ID): None if absent."""

    def __init__(self, item: Codec) -> None:
        self.item = item

    def pack(self, value: Any, packet: Any) -> bytes:
        return b"" if value is None else self.item.pack(value, packet)

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        if offset >= len(data):
            return None, offset
        return self.item.unpack(data, offset, values)


class _Header(Codec):
    """Size or Type of an InSim packet: filled in by InSimPacket.pack()."""

    is_field = False

    def pack(self, value: Any, packet: Any) -> bytes:
        return b"\0"

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return None, offset + 1


SIZE = _Header()
TYPE = _Header()


class Structure:
    """Base of every generated class: a dataclass with a binary layout."""

    _LAYOUT: ClassVar[tuple[tuple[str, Codec], ...]] = ()

    def pack(self) -> bytes:
        """The bytes of this structure, as LFS expects them."""
        return b"".join(codec.pack(getattr(self, name, None), self) for name, codec in self._LAYOUT)

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        """Read an instance from bytes, as LFS sends them."""
        instance, _ = cls._unpack_from(bytes(data), 0)
        return instance

    @classmethod
    def _unpack_from(cls, data: bytes, offset: int) -> tuple[Self, int]:
        values: dict[str, Any] = {}
        for name, codec in cls._LAYOUT:
            values[name], offset = codec.unpack(data, offset, values)
        fields = {name: values[name] for name, codec in cls._LAYOUT if codec.is_field}
        return cls(**fields), offset


_PACKET_TYPES: dict[int, type[InSimPacket]] = {}


class InSimPacket(Structure):
    """Base of every InSim packet: a 4-byte header (Size / 4, Type, ReqI, ...) and a body."""

    _TYPE: ClassVar[int]

    def pack(self) -> bytes:
        body = bytearray(super().pack())
        body.extend(bytes(-len(body) % 4))
        if len(body) > 255 * 4:
            raise PacketError(f"{type(self).__name__} is {len(body)} bytes; the limit is 1020")
        body[0] = len(body) // 4
        body[1] = self._TYPE
        return bytes(body)

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        data = _checked(data)
        if data[1] != cls._TYPE:
            raise PacketError(f"type {data[1]} is not {cls.__name__} ({cls._TYPE})")
        return super().unpack(data)


def _checked(data: bytes) -> bytes:
    if len(data) < 4:
        raise PacketError("an InSim packet has at least 4 bytes")
    size = data[0] * 4
    if size < 4 or size > len(data):
        raise PacketError(f"Size says {size} bytes, but {len(data)} were given")
    return bytes(data[:size])


def register(*classes: type[InSimPacket]) -> None:
    """Make unpack_insim() read these classes. A Type can only belong to one class."""
    for cls in classes:
        known = _PACKET_TYPES.setdefault(cls._TYPE, cls)
        if known is not cls:
            raise ValueError(f"type {cls._TYPE} already belongs to {known.__name__}")


def unpack_insim(data: bytes) -> InSimPacket:
    """Read any InSim packet: the class is chosen by its Type byte."""
    data = _checked(data)
    cls = _PACKET_TYPES.get(data[1])
    if cls is None:
        raise PacketError(f"unknown packet type {data[1]}")
    return cls.unpack(data)


def factory(cls: type[Structure], count: int | None = None) -> Callable[[], Any]:
    """default_factory for generated fields: a new instance, or a list of `count` of them."""
    if count is None:
        return cls
    return lambda: [cls() for _ in range(count)]
