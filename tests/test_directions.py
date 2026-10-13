"""Which way each packet travels: base classes, docstrings, what on() and send() accept (W7.2)."""

import re
import textwrap
from pathlib import Path

import pytest
import spec_parser
from mypy import api as mypy_api
from spec_directions import packet_directions

from lfs_insim import InSim, packets, received, sent
from lfs_insim.packets import (
    IS_MST,
    IS_NPL,
    IS_TINY,
    IS_VER,
    BothWaysPacket,
    InfoPacket,
    InstructionPacket,
)

CACHE = Path(__file__).resolve().parent.parent / "spec" / "cache"
BASES = {"info": InfoPacket, "instruction": InstructionPacket, "both ways": BothWaysPacket}


def test_each_packet_has_the_base_of_its_direction() -> None:
    assert IS_NPL.__bases__ == (InfoPacket,)
    assert IS_MST.__bases__ == (InstructionPacket,)
    assert IS_TINY.__bases__ == (BothWaysPacket,)
    assert issubclass(BothWaysPacket, InfoPacket) and issubclass(BothWaysPacket, InstructionPacket)


@pytest.mark.skipif(not (CACHE / "InSim.txt").exists(), reason="run scripts/fetch_spec.py first")
def test_every_packet_has_the_direction_of_the_specification() -> None:
    spec = spec_parser.parse((CACHE / "InSim.txt").read_text(encoding="utf-8"), "InSim.txt")
    for name, direction in packet_directions(spec).items():
        cls = getattr(packets, name)
        assert BASES[direction] in cls.__bases__, name
        assert f"({direction}:" in (cls.__doc__ or ""), name


def test_the_docstring_says_who_sends_it() -> None:
    assert (IS_VER.__doc__ or "").endswith("(info: LFS sends it)")
    assert "(instruction: your program sends it)" in (IS_MST.__doc__ or "")


def test_on_refuses_a_packet_that_lfs_never_sends() -> None:
    insim = InSim()
    with pytest.raises(TypeError, match="IS_MST is an instruction: LFS never sends it"):
        insim.on(IS_MST)  # type: ignore[type-var]
    with pytest.raises(TypeError, match="not a packet class"):
        insim.on(IS_NPL())  # type: ignore[arg-type]
    insim.on(IS_NPL)(print)
    insim.on(IS_TINY)(print)  # both ways


def test_send_refuses_a_packet_that_only_lfs_sends() -> None:
    insim = InSim()
    # Not connected: the direction is checked first.
    with pytest.raises(TypeError, match="IS_NPL is info: LFS sends it"):
        insim.send(IS_NPL())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="IS_VER is info"):
        insim.send(IS_TINY(), IS_VER())  # type: ignore[arg-type]
    with pytest.raises(ConnectionError):  # the right direction: only the connection is missing
        insim.send(IS_MST(Msg="hi"), IS_TINY())


def test_the_type_checker_sees_the_direction(tmp_path: Path) -> None:
    code = textwrap.dedent(
        """
        from lfs_insim import InSim
        from lfs_insim.packets import IS_MST, IS_NPL, IS_TINY

        insim = InSim()
        insim.on(IS_NPL)
        insim.on(IS_TINY)
        insim.on(IS_MST)
        insim.send(IS_MST(Msg="hi"), IS_TINY())
        insim.send(IS_NPL())
        """
    )
    source = tmp_path / "use.py"
    source.write_text(code, encoding="utf-8")
    out, _, status = mypy_api.run([str(source), "--no-incremental", "--strict"])
    assert status == 1
    assert re.findall(r"use\.py:(\d+): error", out) == ["8", "10"], out  # on(IS_MST), send(IS_NPL)


def test_received_and_sent_list_the_same_classes_by_direction() -> None:
    every = [getattr(packets, name) for name in packets.__all__ if name.startswith("IS_")]
    by_name = {cls.__name__: cls for cls in every}
    for module, base in ((received, InfoPacket), (sent, InstructionPacket)):
        listed = {name: getattr(module, name) for name in module.__all__}
        assert listed == {name: cls for name, cls in by_name.items() if issubclass(cls, base)}
        assert all(cls is getattr(packets, name) for name, cls in listed.items())  # not copies
    assert received.IS_NPL is IS_NPL and sent.IS_MST is IS_MST
    assert received.IS_TINY is sent.IS_TINY is IS_TINY  # both ways: in both
    assert not hasattr(received, "IS_MST") and not hasattr(sent, "IS_NPL")


def test_lfs_insim_received_works_after_a_plain_import() -> None:
    import lfs_insim

    assert lfs_insim.received.IS_VER is IS_VER
    assert lfs_insim.sent.IS_TINY is IS_TINY
