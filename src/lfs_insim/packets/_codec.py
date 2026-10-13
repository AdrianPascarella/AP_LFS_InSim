"""Packing and unpacking of the packet classes (internal).

Every packet or structure class declares its binary layout as a tuple of (name, codec) pairs in
`_LAYOUT`, in wire order. The generated code (W2.4) writes those layouts from the specification;
this module has the codecs, and lfs_insim.packets._structure the classes that run them.

Codecs that are not dataclass fields (padding, Size, Type, counters) are filled in here, so a
user never sets them: `IS_MST(Msg="hello").pack()` is a complete packet.
"""

from __future__ import annotations

import struct
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Any

from lfs_insim.packets import _text
from lfs_insim.packets._enums import LID

if TYPE_CHECKING:  # _structure imports this module
    from lfs_insim.packets._structure import Structure


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


def _start(code_page: str | None, values: Any) -> LID:
    """The code page a text starts in: Latin-1, or the one in the field named `code_page`.

    `values` is the packet when packing and the dict of the fields read so far when unpacking.
    """
    if code_page is None:
        return LID.LATIN
    value = values[code_page] if isinstance(values, dict) else getattr(values, code_page)
    return _text.code_page(value)


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


_CAR_CHARS = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def _skin_id_number(value: Any) -> int:
    """'5A1FB3' -> 0x5A1FB3. A SkinID is written as at least 6 hex digits."""
    if not isinstance(value, str) or len(value) < 6 or len(value) > 8:
        raise PacketError(f"{value!r} is not a SkinID (6 hex digits, like '5A1FB3')")
    try:
        return int(value, 16)
    except ValueError:
        raise PacketError(f"{value!r} is not a SkinID (6 hex digits, like '5A1FB3')") from None


class SkinID(Codec):
    """unsigned SkinID of a mod, as the hex digits LFS shows: '5A1FB3'."""

    def pack(self, value: Any, packet: Any) -> bytes:
        return struct.pack("<I", _skin_id_number(value))

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        if offset + 4 > len(data):
            raise PacketError("packet too short")
        return f"{int.from_bytes(data[offset : offset + 4], 'little'):06X}", offset + 4


class CarName(Codec):
    """char CName[4]: an official car ('XFG'), a mod's SkinID ('5A1FB3'), or '' for no car.

    LFS tells them apart by the first three bytes: all ASCII letters or digits means an official
    car; anything else is the SkinID as a 32-bit unsigned (LFS never issues a SkinID whose bytes
    would all be letters or digits).
    """

    def pack(self, value: Any, packet: Any) -> bytes:
        if value == "":
            return bytes(4)
        if isinstance(value, str) and len(value) == 3:
            raw = value.encode("ascii", errors="replace")
            if set(raw) <= _CAR_CHARS:
                return raw + b"\0"
        raw = struct.pack("<I", _skin_id_number(value))
        if set(raw[:3]) <= _CAR_CHARS:
            raise PacketError(f"{value!r} would be read as the official car {raw[:3]!r}")
        return raw

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        end = offset + 4
        if end > len(data):
            raise PacketError("packet too short")
        raw = data[offset:end]
        if raw == bytes(4):
            return "", end
        if set(raw[:3]) <= _CAR_CHARS:
            return raw[:3].decode("ascii"), end
        return f"{int.from_bytes(raw, 'little'):06X}", end


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
    """Variable-size text at the end of a packet: zero-terminated, padded to a multiple of 4.

    `code_page` names the field that holds the code page the text starts in (IS_MSO.MSOData).
    `caption` names the field for the text entry caption of IS_BTN: LFS reads it between a zero
    at the start and a second zero, and the button text follows. `text_start` names a field read
    as a byte offset into the text (IS_MSO.TextStart), turned here into an index into the str.
    """

    def __init__(
        self,
        max_size: int,
        code_page: str | None = None,
        caption: str | None = None,
        text_start: str | None = None,
    ) -> None:
        self.max_size = max_size
        self.code_page = code_page
        self.caption = caption
        self.text_start = text_start

    def pack(self, value: Any, packet: Any) -> bytes:
        raw = _text.encode(value, _start(self.code_page, packet))
        if self.caption is not None and getattr(packet, self.caption):
            raw = b"\0" + _text.encode(getattr(packet, self.caption)) + b"\0" + raw
        if len(raw) > self.max_size - 1:
            raise PacketError(f"text is {len(raw)} bytes long; the limit is {self.max_size - 1}")
        size = len(raw) + 1
        return raw.ljust(size + (-size % 4), b"\0")

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        tail = data[offset:]
        if self.caption is not None:
            caption = b""
            if tail[:1] == b"\0":
                caption, _, tail = tail[1:].partition(b"\0")
            values[self.caption] = _text.decode(caption)
        text = tail.split(b"\0", 1)[0]
        start = _start(self.code_page, values)
        if self.text_start is not None:
            values[self.text_start] = len(_text.decode(text[: values[self.text_start]], start))
        return _text.decode(text, start), len(data)


class TextOffset(Codec):
    """A byte giving where something starts in a text (IS_MSO.TextStart).

    The field is an index into the str named by `of`; LFS counts bytes, so it is converted here
    when packing and by that text's TailText when unpacking.
    """

    def __init__(self, of: str, code_page: str | None = None) -> None:
        self.scalar = Scalar("B")
        self.of = of
        self.code_page = code_page

    def pack(self, value: Any, packet: Any) -> bytes:
        text = getattr(packet, self.of)
        if not 0 <= value <= len(text):
            raise PacketError(f"{value!r} is not a position in {self.of} ({len(text)} characters)")
        start = _start(self.code_page, packet)
        offset = len(_text.encode(text[:value], start))
        if (
            text[value : value + 1] != "^"
            and _text.encode(text, start)[offset : offset + 1] == b"^"
        ):
            offset += 2  # a code page switch added before the character: LFS points after it
        return self.scalar.pack(offset, packet)

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return self.scalar.unpack(data, offset, values)


class FilledIn(Codec):
    """A field with no bytes of its own: another codec reads it (IS_BTN.Caption)."""

    def __init__(self, name: str) -> None:
        self.name = name

    def pack(self, value: Any, packet: Any) -> bytes:
        return b""

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return values[self.name], offset


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


_OPTIONS = "\0options"  # key of the unpack options in `values`; never a field name


class Options(Codec):
    """The options a packet was sent with (OutSim Opts): a field, but not part of the bytes."""

    def pack(self, value: Any, packet: Any) -> bytes:
        return b""

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return values[_OPTIONS], offset


class When(Codec):
    """A part that is only in the bytes if an option is set (OSO_MAIN...): None if it is not.

    `of` names the Options field. Packing checks that the value is given exactly when the option
    is set, so a packet never disagrees with its own options.
    """

    def __init__(self, option: int, item: Codec, of: str) -> None:
        self.option = option
        self.item = item
        self.of = of
        self.is_field = item.is_field

    def pack(self, value: Any, packet: Any) -> bytes:
        present = bool(getattr(packet, self.of) & self.option)
        if self.is_field and present != (value is not None):
            state = "set" if present else "not set"
            raise PacketError(f"option {self.option:#x} is {state}, but the value is {value!r}")
        return self.item.pack(value, packet) if present else b""

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        if not values[self.of] & self.option:
            return None, offset
        return self.item.unpack(data, offset, values)


class Magic(Codec):
    """Fixed bytes that mark a packet (the "LFST" of OutSimPack2): written and checked."""

    is_field = False

    def __init__(self, magic: bytes) -> None:
        self.magic = magic

    def pack(self, value: Any, packet: Any) -> bytes:
        return self.magic

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        end = offset + len(self.magic)
        if data[offset:end] != self.magic:
            raise PacketError(f"expected {self.magic!r}, got {data[offset:end]!r}")
        return None, end


class _Header(Codec):
    """Size or Type of an InSim packet: filled in by InSimPacket.pack()."""

    is_field = False

    def pack(self, value: Any, packet: Any) -> bytes:
        return b"\0"

    def unpack(self, data: bytes, offset: int, values: dict[str, Any]) -> tuple[Any, int]:
        return None, offset + 1


SIZE = _Header()
TYPE = _Header()
