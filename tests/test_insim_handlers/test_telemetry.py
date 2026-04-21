"""Tests for ISP_MCI handler."""
from lfs_insim.packets import ISP_MCI, ISP_NPL
from lfs_insim.packets.structures import CompCar
from lfs_insim.insim_enums import PTYPE


def _npl_human(plid=10, ucid=1) -> ISP_NPL:
    p = ISP_NPL()
    p.PLID = plid
    p.UCID = ucid
    p.PType = 0
    p.CName = "XFG"
    p.Plate = "TEST"
    p.PName = ""
    return p


def _mci(cars: list[tuple[int, int, int, int]]) -> ISP_MCI:
    """Build ISP_MCI with a list of (plid, speed, node, lap) tuples."""
    p = ISP_MCI()
    p.NumC = len(cars)
    p.Info = []
    for plid, speed, node, lap in cars:
        car = CompCar()
        car.PLID = plid
        car.Speed = speed
        car.Node = node
        car.Lap = lap
        car.X = car.Y = car.Z = 0
        car.Direction = car.Heading = car.AngVel = 0
        car.Position = 0
        car.Info = 0
        car.Sp3 = 0
        p.Info.append(car)
    return p


class TestOnISP_MCI:
    def test_does_not_raise_for_tracked_car(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10))
        insim.on_ISP_MCI(_mci([(10, 5000, 100, 1)]))

    def test_does_not_raise_for_unknown_car(self, insim):
        insim.on_ISP_MCI(_mci([(99, 5000, 100, 1)]))  # plid 99 not in players

    def test_does_not_raise_for_empty_packet(self, insim):
        insim.on_ISP_MCI(_mci([]))

    def test_sends_nothing(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10))
        insim.on_ISP_MCI(_mci([(10, 5000, 100, 1)]))
        assert insim._sent == []

    def test_multiple_cars_processed(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10))
        insim.on_ISP_NPL(_npl_human(plid=11, ucid=2))
        insim.on_ISP_MCI(_mci([(10, 1000, 50, 0), (11, 2000, 51, 0)]))

    def test_unknown_cars_silently_skipped(self, insim):
        insim.on_ISP_NPL(_npl_human(plid=10))
        # plid 99 not in players — should not raise, should not affect state
        insim.on_ISP_MCI(_mci([(10, 1000, 50, 0), (99, 9999, 0, 0)]))
