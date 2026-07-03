"""Tests del registro de cliente por defecto (insim_state.py).

Desde P13 este módulo es solo azúcar opcional: guarda el primer cliente
creado como "cliente por defecto" para las clases auxiliares que usan
PacketSenderMixin sin estar registradas en un cliente. Los sockets ya no
viven aquí (cada cliente tiene su InSimTransport).
"""

import pytest

import lfs_insim.insim_state as state


@pytest.fixture(autouse=True)
def clean_state():
    """Reset del cliente por defecto antes y después de cada test."""
    state.reset_insim_client()
    yield
    state.reset_insim_client()


class FakeClient:
    def __init__(self, name="test"):
        self.name = name


class TestDefaultClientRegistry:
    def test_initial_client_is_none(self):
        assert state.get_insim_client() is None

    def test_first_client_registered(self):
        client = FakeClient()
        state.set_insim_client(client)
        assert state.get_insim_client() is client

    def test_second_client_ignored(self):
        first = FakeClient("first")
        second = FakeClient("second")
        state.set_insim_client(first)
        state.set_insim_client(second)
        assert state.get_insim_client() is first

    def test_reset_allows_re_registration(self):
        first = FakeClient("first")
        state.set_insim_client(first)
        state.reset_insim_client()
        assert state.get_insim_client() is None

        second = FakeClient("second")
        state.set_insim_client(second)
        assert state.get_insim_client() is second
