"""Tests for the custom exception hierarchy."""
import pytest
from lfs_insim.exceptions import (
    InSimError,
    InSimConnectionError,
    InSimConfigurationError,
    InSimPacketError,
    InSimModuleError,
    InSimProtocolError,
    InSimCommandError,
)


class TestInheritance:
    def test_connection_error_is_insim_error(self):
        assert issubclass(InSimConnectionError, InSimError)

    def test_configuration_error_is_insim_error(self):
        assert issubclass(InSimConfigurationError, InSimError)

    def test_packet_error_is_insim_error(self):
        assert issubclass(InSimPacketError, InSimError)

    def test_module_error_is_insim_error(self):
        assert issubclass(InSimModuleError, InSimError)

    def test_protocol_error_is_insim_error(self):
        assert issubclass(InSimProtocolError, InSimError)

    def test_command_error_is_insim_error(self):
        assert issubclass(InSimCommandError, InSimError)

    def test_insim_error_is_exception(self):
        assert issubclass(InSimError, Exception)


class TestConnectionError:
    def test_message(self):
        e = InSimConnectionError("no connection")
        assert str(e) == "no connection"

    def test_host_port_stored(self):
        e = InSimConnectionError("fail", host="127.0.0.1", port=29999)
        assert e.host == "127.0.0.1"
        assert e.port == 29999

    def test_host_port_default_none(self):
        e = InSimConnectionError("fail")
        assert e.host is None
        assert e.port is None

    def test_can_be_caught_as_insim_error(self):
        with pytest.raises(InSimError):
            raise InSimConnectionError("test")


class TestPacketError:
    def test_metadata_stored(self):
        e = InSimPacketError("bad packet", packet_type="ISP_ISI", packet_size=44, data=b"\x00")
        assert e.packet_type == "ISP_ISI"
        assert e.packet_size == 44
        assert e.data == b"\x00"

    def test_metadata_defaults_none(self):
        e = InSimPacketError("bad")
        assert e.packet_type is None
        assert e.packet_size is None
        assert e.data is None


class TestModuleError:
    def test_module_name_stored(self):
        e = InSimModuleError("load failed", module_name="ai_control")
        assert e.module_name == "ai_control"

    def test_module_name_default_none(self):
        e = InSimModuleError("load failed")
        assert e.module_name is None


class TestCommandError:
    def test_command_name_stored(self):
        e = InSimCommandError("bad command", command_name="!speed")
        assert e.command_name == "!speed"

    def test_command_name_default_none(self):
        e = InSimCommandError("bad command")
        assert e.command_name is None
