"""Splitting the InSim TCP stream into packets (W3.2): what arrives in each read is arbitrary."""

import logging

import pytest

from lfs_insim._stream import PacketStream
from lfs_insim.packets import IS_TINY, IS_VER, ISP, TINY, PacketError

TINY_PING = IS_TINY(ReqI=7, SubT=TINY.PING)
VER = IS_VER(ReqI=1, Version="0.8C31", Product="S3", InSimVer=10)
UNKNOWN = bytes([1, 250, 0, 0])  # Size 1 (4 bytes), Type 250: not an InSim packet


def test_one_packet_in_one_read() -> None:
    assert PacketStream().feed(TINY_PING.pack()) == [TINY_PING]


def test_nothing_read_gives_nothing() -> None:
    assert PacketStream().feed(b"") == []


def test_size_is_counted_in_units_of_four_bytes() -> None:
    data = VER.pack()
    assert data[0] * 4 == len(data) == 20
    assert PacketStream().feed(data) == [VER]


def test_several_packets_in_one_read() -> None:
    data = TINY_PING.pack() + VER.pack() + TINY_PING.pack()
    assert PacketStream().feed(data) == [TINY_PING, VER, TINY_PING]


def test_a_packet_split_between_reads() -> None:
    data = VER.pack()
    stream = PacketStream()
    assert stream.feed(data[:7]) == []
    assert stream.feed(data[7:]) == [VER]


def test_byte_by_byte() -> None:
    data = TINY_PING.pack() + VER.pack()
    stream = PacketStream()
    received = [packet for byte in data for packet in stream.feed(bytes([byte]))]
    assert received == [TINY_PING, VER]


def test_a_read_that_ends_inside_the_next_packet() -> None:
    data = TINY_PING.pack() + VER.pack()
    stream = PacketStream()
    assert stream.feed(data[:10]) == [TINY_PING]
    assert stream.feed(data[10:]) == [VER]


def test_an_unknown_type_is_skipped_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="lfs_insim"):
        received = PacketStream().feed(TINY_PING.pack() + UNKNOWN + VER.pack())
    assert received == [TINY_PING, VER]
    assert "250" in caplog.text


def test_a_malformed_packet_is_skipped_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    short_ver = bytes([1, ISP.VER, 0, 0])  # IS_VER needs 20 bytes; Size says 4
    with caplog.at_level(logging.WARNING, logger="lfs_insim"):
        received = PacketStream().feed(short_ver + TINY_PING.pack())
    assert received == [TINY_PING]
    assert "IS_VER" in caplog.text


def test_size_zero_breaks_the_stream() -> None:
    # With Size 0 there is no way to know where the next packet starts: the connection is lost.
    with pytest.raises(PacketError, match="Size 0"):
        PacketStream().feed(TINY_PING.pack() + bytes([0, ISP.TINY, 0, 0]))
