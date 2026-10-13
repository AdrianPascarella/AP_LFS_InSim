"""insim.on.IS_XXX and insim.send.IS_XXX: one attribute per packet, by direction (W7.4)."""

import asyncio
import re
import textwrap
from pathlib import Path

from fake_lfs import FakeLFS
from mypy import api as mypy_api

from lfs_insim import InSim, received, sent
from lfs_insim.packets import IS_ISI, IS_MST, IS_NPL, IS_TINY, TINY


def test_on_and_send_list_the_packets_of_their_direction() -> None:
    insim = InSim()
    on = {name for name in dir(type(insim.on)) if name.startswith("IS_")}
    send = {name for name in dir(type(insim.send)) if name.startswith("IS_")}
    assert on == set(received.__all__)
    assert send == set(sent.__all__)
    assert "IS_MST" not in on and "IS_NPL" not in send
    assert "IS_TINY" in on and "IS_TINY" in send  # both ways


def test_send_shortcut_shows_the_packet_and_its_fields() -> None:
    insim = InSim()
    assert insim.send.IS_MST.__name__ == "IS_MST"
    assert insim.send.IS_MST.__doc__ == IS_MST.__doc__


def test_every_form_reaches_lfs_and_the_handler() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            got: list[str] = []

            @insim.on.IS_NPL
            def shortcut(packet: received.IS_NPL) -> None:
                got.append("on.IS_NPL " + packet.PName)

            @insim.on(IS_NPL)
            def called(packet: IS_NPL) -> None:
                got.append("on(IS_NPL) " + packet.PName)

            @insim.on(received.IS_TINY)
            def tiny(packet: IS_TINY) -> None:
                got.append(f"on(received.IS_TINY) {packet.ReqI}")

            async with insim:
                await lfs.wait_for(IS_ISI)  # connected: sending works from here
                insim.send.IS_MST(Msg="shortcut")
                insim.send(IS_MST(Msg="called"), sent.IS_MST(Msg="module"))
                assert (await lfs.wait_for(IS_MST)).Msg == "shortcut"
                assert (await lfs.wait_for(IS_MST)).Msg == "called"
                assert (await lfs.wait_for(IS_MST)).Msg == "module"
                await lfs.send(IS_NPL(PName="Bob"), IS_TINY(ReqI=7, SubT=TINY.NONE))
                async with asyncio.timeout(2):
                    while len(got) < 3:
                        await asyncio.sleep(0.01)
            assert got == ["on.IS_NPL Bob", "on(IS_NPL) Bob", "on(received.IS_TINY) 7"]

    asyncio.run(main())


def test_the_type_checker_sees_the_fields_and_the_direction(tmp_path: Path) -> None:
    code = textwrap.dedent(
        """
        from lfs_insim import InSim, received

        insim = InSim()

        @insim.on.IS_NPL
        def joined(packet: received.IS_NPL) -> None: ...
        @insim.on.IS_NPL
        def wrong(packet: received.IS_LAP) -> None: ...
        insim.on.IS_MST
        insim.send.IS_MST(Msg="hi")
        insim.send.IS_MST(Msg=3)
        insim.send.IS_MST(Bogus=1)
        insim.send.IS_NPL(PName="x")
        reveal_type(insim.send.IS_MST)
        """
    )
    source = tmp_path / "use.py"
    source.write_text(code, encoding="utf-8")
    out, _, _ = mypy_api.run([str(source), "--no-incremental", "--strict"])
    # 8: wrong packet for the handler (reported at its decorator); 10: LFS never sends IS_MST;
    # 12: Msg is a str; 13: no such field; 14: a program never sends IS_NPL.
    assert re.findall(r"use\.py:(\d+): error", out) == ["8", "10", "12", "13", "14"], out
    assert re.search(r'use\.py:15: note: Revealed type is "def \(\*, ReqI: .*Msg: .*\)"', out), out
