"""W8.5: IS_REO, IS_HCP and IS_IPB, the packets whose sending always failed in the previous
project (fixed-length lists and nested structures; LEGADO.md P21). Bytes as InSim.txt lays them out,
and sent through the fake LFS both ways."""

import asyncio
from ipaddress import IPv4Address

import pytest

from lfs_insim import InSim
from lfs_insim.packets import IS_HCP, IS_IPB, IS_PIT, IS_REO, CarHCP, PacketError, unpack_insim
from lfs_insim.testing import FakeLFS

REO = IS_REO(ReqI=1, NumP=3, PLID=[5, 2, 9] + [0] * 45)
HCP = IS_HCP(ReqI=1, Info=[CarHCP(H_Mass=10, H_TRes=20)] + [CarHCP() for _ in range(31)])
IPB = IS_IPB(ReqI=1, BanIPs=[IPv4Address("1.2.3.4"), IPv4Address("10.0.0.255")])


def test_reo_bytes() -> None:
    # Size/4, ISP_REO (36), ReqI, NumP, then 48 PLIDs
    assert REO.pack() == bytes([52 // 4, 36, 1, 3, 5, 2, 9]) + bytes(45)
    assert unpack_insim(REO.pack()) == REO


def test_hcp_bytes() -> None:
    # Size/4, ISP_HCP (56), ReqI, Zero, then 32 CarHCP of H_Mass and H_TRes
    assert HCP.pack() == bytes([68 // 4, 56, 1, 0, 10, 20]) + bytes(62)
    assert unpack_insim(HCP.pack()) == HCP


def test_ipb_bytes() -> None:
    # Size/4, ISP_IPB (67), ReqI, NumB, 4 spare, then NumB addresses in network order
    expected = bytes([16 // 4, 67, 1, 2, 0, 0, 0, 0, 1, 2, 3, 4, 10, 0, 0, 255])
    assert IPB.pack() == expected
    assert unpack_insim(expected) == IPB
    assert IS_IPB().pack() == bytes([2, 67, 0, 0, 0, 0, 0, 0])  # no bans: the list is cleared


def test_a_short_list_is_filled_with_zeros_where_zero_means_none() -> None:
    # PLID 0 is no player and a zero CarHCP no handicap, so the rest can be left out (U9, S18).
    assert IS_REO(ReqI=1, NumP=3, PLID=[5, 2, 9]).pack() == REO.pack()
    assert IS_HCP(ReqI=1, Info=[CarHCP(H_Mass=10, H_TRes=20)]).pack() == HCP.pack()
    assert IS_REO(PLID=[]).pack() == IS_REO().pack()


def test_too_many_items_is_still_an_error() -> None:
    with pytest.raises(PacketError, match="at most 48 items, got 49"):
        IS_REO(PLID=[1] * 49).pack()
    with pytest.raises(PacketError, match="at most 32 items, got 33"):
        IS_HCP(Info=[CarHCP() for _ in range(33)]).pack()


def test_other_fixed_lists_must_be_complete() -> None:
    # Tyres: 0 is a real tyre (R1), so a missing wheel is not filled in.
    with pytest.raises(PacketError, match="expected 4 items, got 2"):
        IS_PIT(Tyres=[1, 2]).pack()


def test_sent_to_lfs_and_received_from_it() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            got: list[object] = []
            insim.on.IS_REO(got.append)
            insim.on.IS_IPB(got.append)
            async with insim:
                await lfs.wait_connected()
                insim.send(REO)
                insim.send(HCP)
                insim.send(IPB)
                assert await lfs.wait_for(IS_REO) == REO
                assert await lfs.wait_for(IS_HCP) == HCP
                assert await lfs.wait_for(IS_IPB) == IPB
                await lfs.send(REO, IPB)  # both ways: LFS sends them too
                async with asyncio.timeout(2):
                    while len(got) < 2:
                        await asyncio.sleep(0.01)
            assert got == [REO, IPB]

    asyncio.run(main())
