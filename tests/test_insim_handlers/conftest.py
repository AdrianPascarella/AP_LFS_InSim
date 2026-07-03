"""Shared fixtures for test_insim handler tests.

Desde P13 el envío viaja por el cliente (mixin → self.client o cliente por
defecto), así que se captura parcheando `client.send` de un cliente real en
el que se registra la app. Los helpers sin `client` propio (CMDManager...)
caen en el cliente por defecto, que es este mismo (el primero creado).
"""

from unittest.mock import patch

import pytest

import lfs_insim.insim_state as state
from insims.test_insim.main import TestInsim
from lfs_insim.insim_client import InSimClient


@pytest.fixture(autouse=True)
def clean_state():
    state.reset_insim_client()
    yield
    state.reset_insim_client()


@pytest.fixture
def insim():
    """TestInsim registrada en un cliente con el envío capturado en app._sent."""
    sent = []
    client = InSimClient(config={})
    with patch.object(client, "send", side_effect=sent.append):
        app = TestInsim(config={})
        client.register(app)
        app._sent = sent
        yield app


@pytest.fixture
def connected(insim):
    """TestInsim after on_connect(); _sent cleared so tests see only new packets."""
    insim.on_connect()
    insim._sent.clear()
    return insim
