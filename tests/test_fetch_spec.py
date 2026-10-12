import json

import fetch_spec
import pytest
from fetch_spec import SpecError

HEADER = """#ifndef _ISPACKETS_H_
const int INSIM_VERSION = 10;

// CHANGES
// =======

// 0.8C27
// ------
// Something new

// 0.8B (INSIM_VERSION increased to 10)
// ----
"""


def page(body: str) -> str:
    return f'<html><body><div><pre style="tab-size: 4">\n{body}</pre></div></body></html>'


def test_extracts_the_pre_block_and_unescapes_entities() -> None:
    text = fetch_spec.extract_insim(page(HEADER + "if (a &amp;&amp; b &lt; c) &quot;x&quot;\r\n"))
    assert text.startswith("#ifndef _ISPACKETS_H_\n")
    assert 'if (a && b < c) "x"\n' in text
    assert "\r" not in text


def test_reads_lfs_and_insim_versions_from_the_change_list() -> None:
    info = fetch_spec.describe_insim(fetch_spec.extract_insim(page(HEADER)))
    assert info.lfs_version == "0.8C27"
    assert info.insim_version == 10


def test_fingerprint_ignores_line_endings() -> None:
    lf = fetch_spec.extract_insim(page(HEADER))
    crlf = fetch_spec.extract_insim(page(HEADER.replace("\n", "\r\n")))
    assert fetch_spec.fingerprint(lf) == fetch_spec.fingerprint(crlf)


@pytest.mark.parametrize(
    ("html", "reason"),
    [
        ("<html>no spec here</html>", "found 0"),
        (page(HEADER) + page(HEADER), "found 2"),
        (page(HEADER + "<b>bold</b>\n"), "unexpected HTML tag"),
        (page("// just a comment\n"), "INSIM_VERSION"),
    ],
)
def test_rejects_a_page_that_does_not_look_like_the_specification(html: str, reason: str) -> None:
    with pytest.raises(SpecError, match=reason):
        fetch_spec.extract_insim(html)


def test_checked_file_records_the_insim_version() -> None:
    checked = json.loads(fetch_spec.CHECKED_FILE.read_text(encoding="utf-8"))
    assert checked["insim"]["source"] == fetch_spec.INSIM_URL
    assert len(checked["insim"]["sha256"]) == 64


@pytest.mark.network
def test_lfs_net_still_serves_the_checked_specification() -> None:
    """Fails when lfs.net publishes a new InSim version: review it and run --accept."""
    text = fetch_spec.extract_insim(fetch_spec.download(fetch_spec.INSIM_URL))
    info = fetch_spec.describe_insim(text)
    checked = json.loads(fetch_spec.CHECKED_FILE.read_text(encoding="utf-8"))["insim"]
    assert info.to_json() == checked
