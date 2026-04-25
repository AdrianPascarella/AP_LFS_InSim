"""Tests for TestInsim lifecycle: __init__, set_isi_packet, on_connect, on_disconnect."""
from lfs_insim.packets import ISP_TINY, ISP_MSL
from lfs_insim.insim_enums import ISF
from lfs_insim.utils import CMDManager
from lfs_insim.packets import TINY


class TestInit:
    def test_users_starts_empty(self, insim):
        assert insim.users == {}

    def test_players_starts_empty(self, insim):
        assert insim.players == {}

    def test_cmd_base_value(self, insim):
        assert insim.cmd_base == "test"

    def test_cmd_prefix_default(self, insim):
        assert insim.cmd_prefix == "!"

    def test_name_matches_class(self, insim):
        assert insim.name == "TestInsim"


class TestSetIsiPacket:
    def test_local_flag_enabled(self, insim):
        insim.set_isi_packet()
        assert insim.isi.Flags & ISF.LOCAL

    def test_mci_flag_enabled(self, insim):
        insim.set_isi_packet()
        assert insim.isi.Flags & ISF.MCI

    def test_both_flags_enabled(self, insim):
        insim.set_isi_packet()
        assert insim.isi.Flags & (ISF.LOCAL | ISF.MCI)


class TestOnConnect:
    def test_sends_tiny_ncn(self, insim):
        insim.on_connect()
        tinies = [p for p in insim._sent if isinstance(p, ISP_TINY)]
        assert any(t.SubT == TINY.NCN for t in tinies)

    def test_sends_tiny_npl(self, insim):
        insim.on_connect()
        tinies = [p for p in insim._sent if isinstance(p, ISP_TINY)]
        assert any(t.SubT == TINY.NPL for t in tinies)

    def test_sends_connected_msl(self, insim):
        insim.on_connect()
        msls = [p for p in insim._sent if isinstance(p, ISP_MSL)]
        assert any("conectado" in m.Msg for m in msls)

    def test_cmds_is_cmd_manager(self, insim):
        insim.on_connect()
        assert isinstance(insim.cmds, CMDManager)

    def test_cmds_has_users_command(self, insim):
        insim.on_connect()
        assert "users" in insim.cmds._cmds

    def test_cmds_has_players_command(self, insim):
        insim.on_connect()
        assert "players" in insim.cmds._cmds


class TestOnDisconnect:
    def test_does_not_raise(self, insim):
        insim.on_disconnect()

    def test_sends_nothing(self, insim):
        insim.on_disconnect()
        assert insim._sent == []
