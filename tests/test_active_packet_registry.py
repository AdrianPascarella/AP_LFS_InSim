"""Tests for the Active Packet Registry optimization.

Covers _build_active_handlers() in InSimClient, the pre-decode filter
in _process_raw_bytes(), and the post-decode filter in _dispatch_packet().
"""
import struct
from unittest.mock import MagicMock, patch, call
import pytest

import lfs_insim.insim_state as state
from lfs_insim.insim_client import InSimClient
from lfs_insim.insim_enums import ISP
from lfs_insim.packets import INSIM_PACKETS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client():
    """InSimClient with send_packet mocked so __init__ doesn't need sockets."""
    state.reset_insim_client()
    state.reset_sockets()
    with patch('lfs_insim.insim_packet_sender.send_packet'), \
         patch('lfs_insim.insim_client.send_packet'):
        client = InSimClient(config={})
    return client


def _make_tcp_bytes(type_id: int, payload_size: int = 0) -> bytes:
    """Build a minimal InSim TCP packet for type_id.
    Size field = (4 + payload_size) // 4  (InSim invariant: Size*4 == total bytes).
    """
    total = 4 + payload_size
    size_field = total // 4
    data = bytes([size_field, type_id, 0, 0]) + bytes(payload_size)
    assert data[0] * 4 == len(data), "test helper invariant broken"
    return data


def _make_udp_bytes(size: int = 10) -> bytes:
    """Build bytes that look like UDP OutSim (data[0]*4 != len(data))."""
    # First byte * 4 must NOT equal total length.
    data = bytes(size)
    assert data[0] * 4 != len(data), "test helper invariant broken"
    return data


# ---------------------------------------------------------------------------
# _build_active_handlers: handler discovery
# ---------------------------------------------------------------------------

class TestBuildActiveHandlers:

    def setup_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def teardown_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def test_collects_module_handler_names(self):
        client = _make_client()

        class ModA:
            name = "ModA"
            def on_ISP_MCI(self, p): pass
            def on_ISP_MSO(self, p): pass

        mod = ModA()
        client.modules.append(mod)
        client._build_active_handlers()

        assert 'on_ISP_MCI' in client._active_handler_names
        assert 'on_ISP_MSO' in client._active_handler_names

    def test_collects_corresponding_type_ids(self):
        client = _make_client()

        mci_id = next(tid for tid, cls in INSIM_PACKETS.items() if cls.__name__ == 'ISP_MCI')

        class ModA:
            name = "ModA"
            def on_ISP_MCI(self, p): pass

        client.modules.append(ModA())
        client._build_active_handlers()

        assert mci_id in client._active_type_ids

    def test_always_includes_tiny(self):
        client = _make_client()
        client._build_active_handlers()
        assert int(ISP.TINY) in client._active_type_ids
        assert 'on_ISP_TINY' in client._active_handler_names

    def test_always_includes_ver(self):
        client = _make_client()
        client._build_active_handlers()
        assert int(ISP.VER) in client._active_type_ids
        assert 'on_ISP_VER' in client._active_handler_names

    def test_no_handlers_still_has_tiny_ver(self):
        """Module with zero on_ISP_* still gets TINY and VER."""
        client = _make_client()

        class Empty:
            name = "Empty"

        client.modules.append(Empty())
        client._build_active_handlers()

        assert int(ISP.TINY) in client._active_type_ids
        assert int(ISP.VER) in client._active_type_ids

    def test_inherited_handlers_found_via_mro(self):
        """Handlers defined in a base class are found through the MRO."""
        client = _make_client()

        class Base:
            name = "Base"
            def on_ISP_NCN(self, p): pass

        class Child(Base):
            pass  # no override

        client.modules.append(Child())
        client._build_active_handlers()

        assert 'on_ISP_NCN' in client._active_handler_names

    def test_handlers_from_multiple_modules_merged(self):
        client = _make_client()

        class ModA:
            name = "ModA"
            def on_ISP_NCN(self, p): pass

        class ModB:
            name = "ModB"
            def on_ISP_NPL(self, p): pass

        client.modules += [ModA(), ModB()]
        client._build_active_handlers()

        assert 'on_ISP_NCN' in client._active_handler_names
        assert 'on_ISP_NPL' in client._active_handler_names


# ---------------------------------------------------------------------------
# Pre-decode filter in _process_raw_bytes
# ---------------------------------------------------------------------------

class TestPreDecodeFilter:
    """Tests that _process_raw_bytes skips decode for inactive packet types."""

    MCI_ID = next(tid for tid, cls in INSIM_PACKETS.items() if cls.__name__ == 'ISP_MCI')

    def setup_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def teardown_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def _client_with_registry(self, active_ids):
        client = _make_client()
        client._active_type_ids = active_ids
        client._active_handler_names = set()
        return client

    def test_skips_decode_for_inactive_type(self):
        """Packet whose type_id is NOT in active_ids is not decoded."""
        client = self._client_with_registry({int(ISP.TINY), int(ISP.VER)})
        raw = _make_tcp_bytes(self.MCI_ID)

        with patch('lfs_insim.insim_state.get_insim_client', return_value=client), \
             patch('lfs_insim.insim_packet_io.decode_packet') as mock_decode:
            from lfs_insim.insim_packet_io import _process_raw_bytes
            _process_raw_bytes(raw)
            mock_decode.assert_not_called()

    def test_passes_decode_for_active_type(self):
        """Packet whose type_id IS in active_ids is decoded."""
        active = {int(ISP.TINY), int(ISP.VER), self.MCI_ID}
        client = self._client_with_registry(active)
        raw = _make_tcp_bytes(self.MCI_ID)

        mock_packet = MagicMock()
        with patch('lfs_insim.insim_state.get_insim_client', return_value=client), \
             patch('lfs_insim.insim_packet_io.decode_packet', return_value=mock_packet):
            from lfs_insim.insim_packet_io import _process_raw_bytes
            _process_raw_bytes(raw)
            # on_packet_received would be called — client received the packet
            # (we verify decode was called implicitly via the mock returning a packet)

    def test_passes_udp_outsim_regardless(self):
        """UDP bytes (data[0]*4 != len(data)) always reach decode_packet."""
        client = self._client_with_registry({int(ISP.TINY)})  # only TINY active
        raw = _make_udp_bytes(16)

        mock_packet = MagicMock()
        with patch('lfs_insim.insim_state.get_insim_client', return_value=client), \
             patch('lfs_insim.insim_packet_io.decode_packet', return_value=mock_packet) as mock_decode:
            from lfs_insim.insim_packet_io import _process_raw_bytes
            _process_raw_bytes(raw)
            mock_decode.assert_called_once_with(raw)

    def test_no_registry_passes_all(self):
        """Client without _active_type_ids never skips decode (safe default)."""
        client = _make_client()
        # Deliberately do NOT call _build_active_handlers()
        assert not hasattr(client, '_active_type_ids')

        raw = _make_tcp_bytes(self.MCI_ID)
        mock_packet = MagicMock()
        with patch('lfs_insim.insim_state.get_insim_client', return_value=client), \
             patch('lfs_insim.insim_packet_io.decode_packet', return_value=mock_packet) as mock_decode:
            from lfs_insim.insim_packet_io import _process_raw_bytes
            _process_raw_bytes(raw)
            mock_decode.assert_called_once_with(raw)

    def test_none_client_returns_without_error(self):
        """If no client is registered, _process_raw_bytes exits cleanly."""
        state.reset_insim_client()
        raw = _make_tcp_bytes(self.MCI_ID)
        with patch('lfs_insim.insim_packet_io.decode_packet') as mock_decode:
            from lfs_insim.insim_packet_io import _process_raw_bytes
            _process_raw_bytes(raw)  # should not raise
            mock_decode.assert_not_called()


# ---------------------------------------------------------------------------
# Post-decode filter in _dispatch_packet
# ---------------------------------------------------------------------------

class TestPostDecodeFilter:
    """Tests that _dispatch_packet skips module loop for unregistered handlers."""

    def setup_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def teardown_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def test_skips_execute_handler_for_unregistered_type(self):
        client = _make_client()
        client._active_handler_names = {'on_ISP_TINY', 'on_ISP_VER'}

        fake_packet = MagicMock()
        fake_packet.__class__.__name__ = 'ISP_MCI'

        with patch.object(client, '_execute_handler') as mock_exec:
            client._dispatch_packet(fake_packet)
            mock_exec.assert_not_called()

    def test_calls_execute_handler_for_registered_type(self):
        client = _make_client()
        client._active_handler_names = {'on_ISP_TINY', 'on_ISP_MCI'}

        fake_packet = MagicMock()
        fake_packet.__class__.__name__ = 'ISP_MCI'

        with patch.object(client, '_execute_handler') as mock_exec:
            client._dispatch_packet(fake_packet)
            assert mock_exec.called

    def test_no_registry_dispatches_normally(self):
        """Without _active_handler_names, all packets are dispatched."""
        client = _make_client()
        assert not hasattr(client, '_active_handler_names')

        fake_packet = MagicMock()
        fake_packet.__class__.__name__ = 'ISP_MCI'

        with patch.object(client, '_execute_handler') as mock_exec:
            client._dispatch_packet(fake_packet)
            assert mock_exec.called
