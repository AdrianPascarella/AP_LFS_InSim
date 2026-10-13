"""Handlers of one subtype: `@insim.on.IS_TINY(TINY.MPE)`, `IS_SMALL(SMALL.STP, ...)` (W7.7)."""

import asyncio
import re
import textwrap
from pathlib import Path

import pytest
from fake_lfs import FakeLFS
from mypy import api as mypy_api

from lfs_insim import InSim, received
from lfs_insim.packets import IS_ISI, IS_NPL, IS_SMALL, IS_TINY, SMALL, TINY


def test_only_the_chosen_subtypes_reach_the_handler() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            got: list[str] = []

            @insim.on.IS_TINY(TINY.MPE)
            def one(packet: received.IS_TINY) -> None:
                got.append(f"mpe {packet.ReqI}")

            @insim.on.IS_TINY(TINY.MPE, TINY.CLR)
            async def two(packet: received.IS_TINY) -> None:
                got.append(f"mpe-or-clr {packet.SubT}")

            @insim.on.IS_TINY
            def every(packet: received.IS_TINY) -> None:
                got.append("any")

            @insim.on(IS_TINY, TINY.CLR)
            def long_form(packet: IS_TINY) -> None:
                got.append("long clr")

            @insim.on.IS_SMALL(SMALL.STP, SMALL.RTP)
            def small(packet: received.IS_SMALL) -> None:
                got.append(f"small {packet.SubT} {packet.UVal}")

            @insim.on(IS_NPL)
            def plain(packet: IS_NPL) -> None:
                got.append("npl")

            async with insim:
                await lfs.wait_for(IS_ISI)
                await lfs.send(
                    IS_TINY(ReqI=1, SubT=TINY.MPE),
                    IS_TINY(ReqI=2, SubT=TINY.CLR),
                    IS_TINY(ReqI=3, SubT=TINY.NCN),
                    IS_SMALL(ReqI=4, SubT=SMALL.RTP, UVal=9),
                    IS_SMALL(ReqI=5, SubT=SMALL.SSP, UVal=8),
                    IS_SMALL(ReqI=6, SubT=SMALL.STP, UVal=7),
                    IS_NPL(PName="Bob"),
                )
                async with asyncio.timeout(2):
                    while "npl" not in got:
                        await asyncio.sleep(0.01)
                await asyncio.sleep(0.05)
            assert sorted(got) == sorted(
                [
                    "mpe 1",  # only MPE
                    "mpe-or-clr 9",  # MPE and CLR, an async handler
                    "mpe-or-clr 12",
                    "any",
                    "any",
                    "any",  # every subtype, as before
                    "long clr",  # the long form, CLR only
                    "small 6 9",  # RTP and STP, not SSP
                    "small 5 7",
                    "npl",
                ]
            ), got

    asyncio.run(main())


def test_a_subtype_of_another_enum_or_a_packet_without_subtypes_is_an_error() -> None:
    insim = InSim()
    with pytest.raises(TypeError, match="IS_TINY subtypes are TINY"):
        insim.on.IS_TINY(SMALL.STP)  # type: ignore[call-overload]
    with pytest.raises(TypeError, match="IS_SMALL subtypes are SMALL"):
        insim.on(IS_SMALL, TINY.MPE)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="IS_NPL has no subtypes"):
        insim.on(IS_NPL, TINY.MPE)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="IS_TINY subtypes are TINY"):
        insim.on(IS_TINY, 9)  # type: ignore[call-overload]


def test_the_type_checker_checks_the_subtype(tmp_path: Path) -> None:
    code = textwrap.dedent(
        """
        from lfs_insim import InSim, received
        from lfs_insim.packets import IS_NPL, SMALL, TINY

        insim = InSim()

        @insim.on.IS_TINY(TINY.MPE, TINY.CLR)
        def fine(packet: received.IS_TINY) -> None: ...
        @insim.on.IS_TINY
        def bare(packet: received.IS_TINY) -> None: ...
        @insim.on.IS_SMALL(SMALL.STP)
        def small(packet: received.IS_SMALL) -> None: ...
        @insim.on.IS_TINY(SMALL.STP)
        def mixed(packet: received.IS_TINY) -> None: ...
        @insim.on.IS_TINY(TINY.MPE)
        def wrong(packet: received.IS_SMALL) -> None: ...
        insim.on(IS_NPL, TINY.MPE)
        insim.on.IS_NPL(TINY.MPE)
        """
    )
    source = tmp_path / "use.py"
    source.write_text(code, encoding="utf-8")
    out, _, _ = mypy_api.run([str(source), "--no-incremental", "--strict"])
    # 13: SMALL on IS_TINY; 15: handler of another packet (at its decorator); 17, 18: no subtypes
    errors = sorted({int(n) for n in re.findall(r"use\.py:(\d+): error", out)})
    assert errors == [13, 15, 17, 18], out
