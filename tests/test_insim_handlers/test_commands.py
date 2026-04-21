"""Tests for on_ISP_MSO dispatch and _cmd_users / _cmd_players commands."""
from lfs_insim.packets import ISP_MSO, ISP_NCN, ISP_NPL, ISP_MSL
from lfs_insim.insim_enums import PTYPE


def _ncn(ucid=1, uname="User") -> ISP_NCN:
    p = ISP_NCN()
    p.UCID = ucid
    p.UName = uname
    p.PName = uname
    return p


def _npl_human(plid=10, ucid=1, car="XFG", plate="TST") -> ISP_NPL:
    p = ISP_NPL()
    p.PLID = plid
    p.UCID = ucid
    p.PType = 0
    p.CName = car
    p.Plate = plate
    p.PName = ""
    return p


def _npl_ai(plid=20, ucid=1, ai_name="AI1") -> ISP_NPL:
    p = ISP_NPL()
    p.PLID = plid
    p.UCID = ucid
    p.PType = PTYPE.AI
    p.CName = "XFG"
    p.Plate = ""
    p.PName = ai_name
    return p


def _mso(msg: str, ucid=1) -> ISP_MSO:
    p = ISP_MSO()
    p.Msg = msg
    p.UCID = ucid
    return p


def _sent_msgs(insim) -> list[str]:
    return [p.Msg for p in insim._sent if isinstance(p, ISP_MSL)]


class TestOnISP_MSO:
    def test_unknown_prefix_ignored(self, connected):
        connected.on_ISP_MSO(_mso(".other cmd"))
        assert connected._sent == []

    def test_wrong_base_cmd_ignored(self, connected):
        connected.on_ISP_MSO(_mso("!other users"))
        assert connected._sent == []

    def test_known_cmd_dispatched(self, connected):
        connected.on_ISP_MSO(_mso("!test_insim users"))
        assert connected._sent != []

    def test_unknown_sub_cmd_sends_error(self, connected):
        connected.on_ISP_MSO(_mso("!test_insim nonexistent"))
        msgs = _sent_msgs(connected)
        assert any("no reconocido" in m for m in msgs)


class TestCmdUsers:
    def test_empty_server_sends_no_users_msg(self, connected):
        connected._cmd_users()
        msgs = _sent_msgs(connected)
        assert any("No hay" in m for m in msgs)

    def test_shows_connected_user(self, connected):
        connected.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        connected._cmd_users()
        msgs = _sent_msgs(connected)
        assert any("Alice" in m for m in msgs)

    def test_shows_ucid(self, connected):
        connected.on_ISP_NCN(_ncn(ucid=3, uname="Bob"))
        connected._cmd_users()
        msgs = _sent_msgs(connected)
        assert any("3" in m for m in msgs)

    def test_shows_spectator_status(self, connected):
        connected.on_ISP_NCN(_ncn(ucid=1))
        connected._cmd_users()
        msgs = _sent_msgs(connected)
        assert any("Espectador" in m for m in msgs)

    def test_shows_on_track_status(self, connected):
        connected.on_ISP_NCN(_ncn(ucid=1))
        connected.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        connected._cmd_users()
        msgs = _sent_msgs(connected)
        assert any("pista" in m for m in msgs)

    def test_shows_plid_when_on_track(self, connected):
        connected.on_ISP_NCN(_ncn(ucid=1))
        connected.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        connected._cmd_users()
        msgs = _sent_msgs(connected)
        assert any("10" in m for m in msgs)

    def test_multiple_users_each_mentioned(self, connected):
        connected.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        connected.on_ISP_NCN(_ncn(ucid=2, uname="Bob"))
        connected._cmd_users()
        msgs = " ".join(_sent_msgs(connected))
        assert "Alice" in msgs and "Bob" in msgs


class TestCmdPlayers:
    def test_empty_track_sends_no_cars_msg(self, connected):
        connected._cmd_players()
        msgs = _sent_msgs(connected)
        assert any("No hay" in m for m in msgs)

    def test_shows_human_player(self, connected):
        connected.on_ISP_NPL(_npl_human(plid=10, car="XFG", plate="ADRN"))
        connected._cmd_players()
        msgs = " ".join(_sent_msgs(connected))
        assert "XFG" in msgs

    def test_shows_plate(self, connected):
        connected.on_ISP_NPL(_npl_human(plid=10, plate="ADRN"))
        connected._cmd_players()
        msgs = " ".join(_sent_msgs(connected))
        assert "ADRN" in msgs

    def test_shows_plid(self, connected):
        connected.on_ISP_NPL(_npl_human(plid=42))
        connected._cmd_players()
        msgs = " ".join(_sent_msgs(connected))
        assert "42" in msgs

    def test_shows_ai_name(self, connected):
        connected.on_ISP_NPL(_npl_ai(plid=20, ai_name="Ghost"))
        connected._cmd_players()
        msgs = " ".join(_sent_msgs(connected))
        assert "Ghost" in msgs

    def test_shows_ai_label_prefix(self, connected):
        connected.on_ISP_NPL(_npl_ai(plid=20, ai_name="Ghost"))
        connected._cmd_players()
        msgs = " ".join(_sent_msgs(connected))
        assert "AI:" in msgs

    def test_human_and_ai_both_listed(self, connected):
        connected.on_ISP_NPL(_npl_human(plid=10, plate="TST"))
        connected.on_ISP_NPL(_npl_ai(plid=20, ai_name="Ghost"))
        connected._cmd_players()
        msgs = " ".join(_sent_msgs(connected))
        assert "TST" in msgs and "Ghost" in msgs
