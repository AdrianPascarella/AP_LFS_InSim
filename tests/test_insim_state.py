"""Tests for global state management in insim_state.py."""
import socket
import pytest
import lfs_insim.insim_state as state


@pytest.fixture(autouse=True)
def clean_state():
    """Reset all global state before and after each test."""
    state.reset_insim_client()
    state.reset_sockets()
    yield
    state.reset_insim_client()
    state.reset_sockets()


class FakeClient:
    def __init__(self, name="test"):
        self.name = name


class TestClientRegistration:
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

    def test_force_set_overrides_existing(self):
        first = FakeClient("first")
        second = FakeClient("second")
        state.set_insim_client(first)
        state.force_set_insim_client(second)
        assert state.get_insim_client() is second


class TestSocketState:
    def test_initial_tcp_socket_is_none(self):
        assert state.get_socket_tcp() is None

    def test_initial_udp_socket_is_none(self):
        assert state.get_socket_udp() is None

    def test_set_and_get_tcp_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            state.set_socket_tcp(sock)
            assert state.get_socket_tcp() is sock
        finally:
            sock.close()

    def test_set_and_get_udp_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            state.set_socket_udp(sock)
            assert state.get_socket_udp() is sock
        finally:
            sock.close()

    def test_reset_sockets_clears_both(self):
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            state.set_socket_tcp(tcp)
            state.set_socket_udp(udp)
            state.reset_sockets()
            assert state.get_socket_tcp() is None
            assert state.get_socket_udp() is None
        finally:
            tcp.close()
            udp.close()
