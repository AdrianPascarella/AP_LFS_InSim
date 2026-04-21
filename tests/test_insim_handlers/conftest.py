"""Shared fixtures for test_insim handler tests."""
import pytest
from unittest.mock import patch
import lfs_insim.insim_state as state
from insims.test_insim.main import TestInsim


PATCH_TARGETS = (
    'lfs_insim.insim_packet_sender.send_packet',  # PacketSenderMixin / CMDManager
    'lfs_insim.insim_client.send_packet',          # InSimClient.send
)


@pytest.fixture(autouse=True)
def clean_state():
    state.reset_insim_client()
    state.reset_sockets()
    yield
    state.reset_insim_client()
    state.reset_sockets()


@pytest.fixture
def insim():
    """TestInsim instance with send_packet mocked; captured packets in app._sent."""
    sent = []
    capturer = lambda p: sent.append(p)
    with patch(PATCH_TARGETS[0], side_effect=capturer), \
         patch(PATCH_TARGETS[1], side_effect=capturer):
        app = TestInsim(config={})
        app._sent = sent
        yield app


@pytest.fixture
def connected(insim):
    """TestInsim after on_connect(); _sent cleared so tests see only new packets."""
    insim.on_connect()
    insim._sent.clear()
    return insim
