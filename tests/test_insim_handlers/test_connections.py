"""Tests for ISP_NCN and ISP_CNL handlers."""
from lfs_insim.packets import ISP_NCN, ISP_CNL


def _ncn(ucid=1, uname="TestUser", pname="Test Player") -> ISP_NCN:
    p = ISP_NCN()
    p.UCID = ucid
    p.UName = uname
    p.PName = pname
    return p


def _cnl(ucid=1) -> ISP_CNL:
    p = ISP_CNL()
    p.UCID = ucid
    return p


class TestOnISP_NCN:
    def test_user_added_to_dict(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        assert 1 in insim.users

    def test_uname_stored(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        assert insim.users[1]["uname"] == "Alice"

    def test_pname_stored(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1, pname="Alice P"))
        assert insim.users[1]["pname"] == "Alice P"

    def test_plid_starts_none(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        assert insim.users[1]["plid"] is None

    def test_multiple_users_independent(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        insim.on_ISP_NCN(_ncn(ucid=2, uname="Bob"))
        assert insim.users[1]["uname"] == "Alice"
        assert insim.users[2]["uname"] == "Bob"

    def test_duplicate_ucid_overwrites(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        insim.on_ISP_NCN(_ncn(ucid=1, uname="NewAlice"))
        assert insim.users[1]["uname"] == "NewAlice"


class TestOnISP_CNL:
    def test_user_removed(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        insim.on_ISP_CNL(_cnl(ucid=1))
        assert 1 not in insim.users

    def test_other_users_unaffected(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1, uname="Alice"))
        insim.on_ISP_NCN(_ncn(ucid=2, uname="Bob"))
        insim.on_ISP_CNL(_cnl(ucid=1))
        assert 2 in insim.users
        assert insim.users[2]["uname"] == "Bob"

    def test_cnl_unknown_ucid_does_not_raise(self, insim):
        insim.on_ISP_CNL(_cnl(ucid=99))  # should not raise

    def test_sends_nothing(self, insim):
        insim.on_ISP_NCN(_ncn(ucid=1))
        insim.on_ISP_CNL(_cnl(ucid=1))
        assert insim._sent == []
