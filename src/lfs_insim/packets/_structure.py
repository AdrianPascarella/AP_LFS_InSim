"""The base classes of the generated packets, and reading any InSim packet (internal).

`Structure` packs and unpacks its `_LAYOUT` with the codecs of lfs_insim.packets._codec;
`InSimPacket` adds the 4-byte header, and `unpack_insim()` picks the class by the Type byte.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, Self

from lfs_insim.packets._codec import _OPTIONS, Codec, PacketError


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
    def _unpack_from(
        cls, data: bytes, offset: int, values: dict[str, Any] | None = None
    ) -> tuple[Self, int]:
        values = {} if values is None else values
        for name, codec in cls._LAYOUT:
            values[name], offset = codec.unpack(data, offset, values)
        fields = {name: values[name] for name, codec in cls._LAYOUT if codec.is_field}
        return cls(**fields), offset


class OptionalParts(Structure):
    """A structure whose parts depend on options that are not in its bytes (OutSimPack2).

    LFS sends only the parts selected in cfg.txt, so reading needs those options:
    `OutSimPack2.unpack(data, OSO.TIME | OSO.MAIN)`.
    """

    @classmethod
    def unpack(cls, data: bytes, options: int | None = None) -> Self:
        if options is None:
            raise PacketError(f"{cls.__name__} needs the options it was sent with")
        data = bytes(data)
        instance, end = cls._unpack_from(data, 0, {_OPTIONS: options})
        if end != len(data):
            raise PacketError(f"options {options:#x} give {end} bytes, but {len(data)} were given")
        return instance


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
