"""Splitting the InSim TCP stream into packets (internal).

TCP delivers bytes, not packets: one read may hold half a packet or several of them. The first
byte of every packet is its Size / 4, so the stream can always be cut at the right place, except
when Size is 0: then nothing says where the next packet starts and the connection is lost.
"""

from __future__ import annotations

import logging

from lfs_insim.packets import ISP, PacketError
from lfs_insim.packets._structure import InSimPacket, unpack_insim

log = logging.getLogger("lfs_insim")


class PacketStream:
    """Collects what arrives on the connection and returns the packets it completes."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[InSimPacket]:
        """Add the bytes of one read; return every packet now complete, in order.

        A packet that cannot be read (an unknown Type, or bytes that do not fit its layout) is
        logged and skipped: its Size still says where the next one starts. Size 0 raises
        PacketError, because the stream cannot be followed any more.
        """
        self._buffer += data
        packets = []
        while self._buffer:
            size = self._buffer[0] * 4
            if size == 0:
                raise PacketError("Size 0: the InSim stream is broken and cannot be followed")
            if len(self._buffer) < size:
                break
            raw = bytes(self._buffer[:size])
            del self._buffer[:size]
            try:
                packets.append(unpack_insim(raw))
            except PacketError as error:
                log.warning("skipped %s: %s", _describe(raw), error)
            except Exception:
                log.exception("skipped %s, which could not be read", _describe(raw))
        return packets


def _describe(raw: bytes) -> str:
    """'IS_VER (type 2, 4 bytes)': names the packet in log messages."""
    try:
        name = f"IS_{ISP(raw[1]).name}"
    except ValueError:
        name = "an unknown packet"
    return f"{name} (type {raw[1]}, {len(raw)} bytes)"
