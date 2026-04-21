"""Tests for PacketFunctions: serialization, string padding, size calculation."""
import struct
import pytest
from lfs_insim.insim_packet_class import ISP_TINY, ISP_SMALL, ISP_ISI, ISP_MSO
from lfs_insim.insim_packet_sender import _extract_values


class TestGetStructString:
    def test_tiny_format(self):
        pkt = ISP_TINY()
        assert pkt.get_struct_string() == "<BBBB"

    def test_small_format(self):
        pkt = ISP_SMALL()
        assert pkt.get_struct_string() == "<BBBBI"

    def test_isi_format(self):
        pkt = ISP_ISI()
        # B B B B H H B B H 16s 16s
        assert pkt.get_struct_string() == "<BBBBHHBBh16s16s".replace("h", "H")

    def test_starts_with_little_endian_marker(self):
        for cls in [ISP_TINY, ISP_SMALL, ISP_ISI]:
            assert cls().get_struct_string().startswith("<")


class TestGetSize:
    def test_tiny_is_4_bytes(self):
        assert ISP_TINY().get_size() == 4

    def test_small_is_8_bytes(self):
        assert ISP_SMALL().get_size() == 8

    def test_isi_size(self):
        # 4xB + H + H + B + B + H + 16s + 16s = 4 + 2 + 2 + 1 + 1 + 2 + 16 + 16 = 44
        assert ISP_ISI().get_size() == 44

    def test_size_matches_struct_calcsize(self):
        for cls in [ISP_TINY, ISP_SMALL, ISP_ISI]:
            pkt = cls()
            assert pkt.get_size() == struct.calcsize(pkt.get_struct_string())


class TestSetInsimSize:
    def test_tiny_size_field(self):
        pkt = ISP_TINY()
        pkt.set_insim_size()
        assert pkt.Size == 1  # 4 bytes / 4

    def test_small_size_field(self):
        pkt = ISP_SMALL()
        pkt.set_insim_size()
        assert pkt.Size == 2  # 8 bytes / 4

    def test_isi_size_field(self):
        pkt = ISP_ISI()
        pkt.set_insim_size()
        assert pkt.Size == 11  # 44 bytes / 4


class TestValidateStringLengths:
    """Tests for variable-length string padding (fmt=('s', limit))."""

    def _pad(self, text, limit):
        """Helper: apply validate_string_lengths and return the result."""
        pkt = ISP_MSO(Msg=text)
        pkt.validate_string_lengths()
        return pkt.Msg

    def test_short_string_padded_to_4_byte_boundary(self):
        # "hello" (5 chars): (5+1)%4 = 2, padding = 2 → 7 chars total
        result = self._pad("hello", 128)
        assert result == "hello\x00\x00"

    def test_two_char_padded(self):
        # "hi" (2 chars): (2+1)%4 = 3, padding = 1 → 3 chars
        result = self._pad("hi", 128)
        assert result == "hi\x00"

    def test_three_char_no_padding_needed(self):
        # "abc" (3 chars): (3+1)%4 = 0, no padding needed
        result = self._pad("abc", 128)
        assert result == "abc"

    def test_four_char_padded(self):
        # "abcd" (4 chars): (4+1)%4 = 1, padding = 3 → 7 chars
        result = self._pad("abcd", 128)
        assert result == "abcd\x00\x00\x00"

    def test_empty_string_padded(self):
        # "" (0 chars): (0+1)%4 = 1, padding = 3 → "\x00\x00\x00"
        result = self._pad("", 128)
        assert result == "\x00\x00\x00"

    def test_string_at_limit_truncated(self):
        # 128 chars >= limit 128 → truncated to 127 chars
        result = self._pad("a" * 128, 128)
        assert len(result) <= 128
        assert not result.startswith("a" * 128)

    def test_string_just_under_limit_not_truncated(self):
        # 127 chars < limit 128 → not truncated
        result = self._pad("a" * 127, 128)
        assert result.startswith("a" * 127)

    def test_result_null_padded(self):
        # Any padding must use null bytes, not spaces
        result = self._pad("hello", 128)
        for ch in result[5:]:
            assert ch == "\x00", f"Expected null byte, got {repr(ch)}"


class TestPrepare:
    def test_prepare_sets_size_and_pads_strings(self):
        pkt = ISP_MSO(Msg="hello")
        pkt.prepare()
        assert pkt.Size > 0
        assert "\x00" in pkt.Msg or len(pkt.Msg) == 3  # padded or naturally aligned

    def test_prepare_tiny_no_strings(self):
        pkt = ISP_TINY(ReqI=7)
        pkt.prepare()
        assert pkt.Size == 1
        assert pkt.ReqI == 7  # unchanged


class TestPackRoundtrip:
    """Verify that packets can be packed to bytes without errors."""

    def _pack(self, pkt):
        pkt.prepare()
        values = _extract_values(pkt)
        fmt = pkt.get_struct_string()
        return struct.pack(fmt, *values)

    def test_tiny_packs_to_4_bytes(self):
        data = self._pack(ISP_TINY(ReqI=42))
        assert len(data) == 4

    def test_tiny_reqi_in_correct_position(self):
        data = self._pack(ISP_TINY(ReqI=42))
        assert data[2] == 42  # Size=0, Type=1, ReqI=2, SubT=3

    def test_tiny_size_byte_after_prepare(self):
        data = self._pack(ISP_TINY())
        assert data[0] == 1  # Size = 4 bytes / 4 = 1

    def test_small_packs_to_8_bytes(self):
        data = self._pack(ISP_SMALL(UVal=999))
        assert len(data) == 8

    def test_isi_packs_to_44_bytes(self):
        data = self._pack(ISP_ISI())
        assert len(data) == 44

    def test_mso_variable_string_packs_without_error(self):
        pkt = ISP_MSO(Msg="hello")
        pkt.prepare()
        data = self._pack(pkt)
        # Fixed header is 8 bytes; packed data must be larger
        assert len(data) > 8
        # First byte is the Size field set by prepare()
        assert data[0] == pkt.Size
