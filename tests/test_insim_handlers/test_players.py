"""Tests for ISP_NPL and ISP_PLL handlers (human players and AIs)."""
from lfs_insim.packets import ISP_NCN, ISP_NPL, ISP_PLL
from lfs_insim.insim_enums import PTYPE


def _ncn(ucid=1, uname="User") -> ISP_NCN:
    p = ISP_NCN()
    p.UCID = ucid
    p.UName = uname
    p.PName = uname
    return p


def _npl_human(plid=10, ucid=1, car="XFG", plate="TEST") -> ISP_NPL:
    p = ISP_NPL()
    p.PLID = plid
    p.UCID = ucid
    p.PType = 0  # human
    p.CName = car
    p.Plate = plate
    p.PName = ""
    return p


def _npl_ai(plid=20, ucid=1, ai_name="AI1", car="XFG") -> ISP_NPL:
    p = ISP_NPL()
    p.PLID = plid
    p.UCID = ucid
    p.PType = PTYPE.AI
    p.CName = car
    p.Plate = ""
    p.PName = ai_name
    return p


def _pll(plid=10) -> ISP_PLL:
    p = ISP_PLL()
    p.PLID = plid
    return p


class TestOnISP_NPL_Human:
    def test_player_added(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        assert 10 in insim.players

    def test_car_name_stored(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, car="XFG"))
        assert insim.players[10]["car"] == "XFG"

    def test_plate_stored(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, plate="ADRN"))
        assert insim.players[10]["plate"] == "ADRN"

    def test_ucid_stored(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=5))
        assert insim.players[10]["ucid"] == 5

    def test_is_ai_false(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10))
        assert insim.players[10]["is_ai"] is False

    def test_user_plid_updated(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        assert insim.users[1]["plid"] == 10

    def test_user_plid_not_updated_if_unknown_ucid(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=99))  # no NCN for ucid 99
        assert 10 in insim.players  # player still added


class TestOnISP_NPL_AI:
    def test_ai_added_to_players(self, insim):
        insim.on_ISP_NPL(_npl_ai(plid=20, ucid=1))
        assert 20 in insim.players

    def test_is_ai_true(self, insim):
        insim.on_ISP_NPL(_npl_ai(plid=20))
        assert insim.players[20]["is_ai"] is True

    def test_ai_name_stored(self, insim):
        insim.on_ISP_NPL(_npl_ai(plid=20, ai_name="Ghost"))
        assert insim.players[20]["ai_name"] == "Ghost"

    def test_user_plid_not_set_for_ai(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        insim.on_ISP_NPL(_npl_ai(plid=20, ucid=1))
        assert insim.users[1]["plid"] is None  # AI doesn't set plid on user

    def test_human_and_ai_coexist(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        insim.on_ISP_NPL(_npl_ai(plid=20, ucid=1))
        assert not insim.players[10]["is_ai"]
        assert insim.players[20]["is_ai"]


class TestOnISP_PLL:
    def test_player_removed(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        insim.on_ISP_PLL(_pll(plid=10))
        assert 10 not in insim.players

    def test_user_plid_cleared_on_human_leave(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=1))
        insim.on_ISP_PLL(_pll(plid=10))
        assert insim.users[1]["plid"] is None

    def test_ai_removed_without_touching_user_plid(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        insim.on_ISP_NPL(_npl_human(plid=10, ucid=1))  # human
        insim.on_ISP_NPL(_npl_ai(plid=20, ucid=1))     # AI
        insim.on_ISP_PLL(_pll(plid=20))                # AI leaves
        assert insim.users[1]["plid"] == 10             # human's plid untouched
        assert 20 not in insim.players

    def test_pll_unknown_plid_does_not_raise(self, insim):
        insim.on_ISP_PLL(_pll(plid=99))  # should not raise

    def test_sends_nothing(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10))
        insim.on_ISP_PLL(_pll(plid=10))
        assert insim._sent == []
