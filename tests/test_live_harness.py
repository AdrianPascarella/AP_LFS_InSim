"""The live test harness (tests/live/harness.py) against the fake LFS, so it keeps working
between the runs against the real game."""

import asyncio
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from harness import Session, name_of, passed

from lfs_insim.packets import IS_MSO, IS_SMALL, IS_TINY, IS_VER, SMALL, TINY
from lfs_insim.testing import FakeLFS


@pytest.fixture
def restore_logging() -> Iterator[None]:
    level = logging.getLogger("lfs_insim").level
    yield
    logging.getLogger("lfs_insim").setLevel(level)


def test_name_of_gives_the_subtype() -> None:
    assert name_of(IS_TINY(SubT=TINY.REPLY)) == "TINY_REPLY"
    assert name_of(IS_SMALL(SubT=SMALL.RTP)) == "SMALL_RTP"
    assert name_of(IS_SMALL(SubT=200)) == "SMALL_200"
    assert name_of(IS_VER()) == "IS_VER"


def test_session_records_checks_and_both_directions(restore_logging: None) -> None:
    async def scenario() -> dict[str, Any]:
        async with FakeLFS() as lfs:
            s = Session("test", port=lfs.port)
            try:
                async with s:
                    assert await s.connected(2)
                    since = s.mark()
                    s.insim.send(IS_TINY(ReqI=7, SubT=TINY.PING))
                    await s.expect_check(
                        "ping", IS_TINY, lambda p: p.SubT == TINY.REPLY, since=since, timeout=2
                    )
                    await lfs.send(IS_MSO(UCID=0, Msg="hello"))
                    assert await s.expect(IS_MSO, since=since, timeout=2) is not None
                    assert await s.expect(IS_MSO, lambda p: p.Msg == "bye", timeout=0.1) is None
                    s.check("skipped", None, "did not happen")
                return s.report()
            finally:
                s.recorder.uninstall()

    data = asyncio.run(scenario())
    assert [(c["name"], c["status"]) for c in data["checks"]] == [
        ("ping", "PASS"),
        ("skipped", "SKIP"),
    ]
    assert data["sent_count"] == {"IS_ISI": 1, "TINY_CLOSE": 1, "TINY_PING": 1}
    received = data["received_count"]
    assert received["IS_VER"] == 1 and received["TINY_REPLY"] == 1
    assert received["IS_MSO"] == 1
    assert passed(data)


def test_a_failed_check_fails_the_run() -> None:
    data: dict[str, Any] = {
        "checks": [{"ok": False}],
        "unreadable": [],
        "content_changes": [],
        "sent_errors": [],
    }
    assert not passed(data)
    data["checks"] = [{"ok": None}, {"ok": True}]
    assert passed(data)
