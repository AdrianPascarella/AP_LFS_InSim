"""Download the official InSim specification and compare it with the checked version.

    .venv/Scripts/python scripts/fetch_spec.py            download and compare
    .venv/Scripts/python scripts/fetch_spec.py --accept   also record the result as checked

Sources:

  insim   https://www.lfs.net/programmer/insim (the header file inside the page's <pre> block)
  outsim  <LFS folder>/docs/OutSimPack.txt (not published on the web; only read, and only if the
          file exists on this machine)

The extracted text goes to spec/cache/ (ignored by git). The version and fingerprint that the
library was checked against live in spec/checked.json (tracked by git). A failed download never
touches the previous copy in spec/cache/.

Exit code: 0 = matches the checked version, 1 = differs (review it, then --accept),
2 = could not read a source.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = ROOT / "spec"
CACHE_DIR = SPEC_DIR / "cache"
CHECKED_FILE = SPEC_DIR / "checked.json"
INSIM_URL = "https://www.lfs.net/programmer/insim"
DEFAULT_LFS_DIR = Path("C:/LFS")
TIMEOUT_SECONDS = 30

PRE_BLOCK = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL | re.IGNORECASE)
CHANGE_HEADING = re.compile(r"^// (\d+\.\d+[A-Z]\d*)\s*$", re.MULTILINE)
INSIM_VERSION = re.compile(r"^const int INSIM_VERSION = (\d+);", re.MULTILINE)


class SpecError(Exception):
    """A source could not be read or did not look like the specification."""


@dataclass(frozen=True)
class SpecInfo:
    """What is recorded about one source in spec/checked.json."""

    source: str
    sha256: str
    lfs_version: str | None = None
    insim_version: int | None = None

    def to_json(self) -> dict[str, str | int]:
        data: dict[str, str | int] = {"source": self.source, "sha256": self.sha256}
        if self.lfs_version is not None:
            data["lfs_version"] = self.lfs_version
        if self.insim_version is not None:
            data["insim_version"] = self.insim_version
        return data


def normalize(text: str) -> str:
    """Use LF line endings and a single trailing newline, so the fingerprint is stable."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(lines).strip("\n") + "\n"


def extract_insim(page: str) -> str:
    """Return the InSim header text from the HTML page of lfs.net."""
    blocks = PRE_BLOCK.findall(page)
    if len(blocks) != 1:
        raise SpecError(f"expected exactly one <pre> block in the page, found {len(blocks)}")
    raw = blocks[0]
    tag = re.search(r"<[A-Za-z/][^>]*>", raw)
    if tag is not None:
        raise SpecError(f"unexpected HTML tag inside the specification: {tag.group(0)}")
    text = normalize(html.unescape(raw))
    if INSIM_VERSION.search(text) is None:
        raise SpecError("the <pre> block does not contain INSIM_VERSION; the page changed")
    return text


def describe_insim(text: str) -> SpecInfo:
    """Fingerprint the InSim text and read its versions (the first entry of the change list)."""
    insim = INSIM_VERSION.search(text)
    changes = text.find("// CHANGES")
    heading = CHANGE_HEADING.search(text, changes) if changes >= 0 else None
    return SpecInfo(
        source=INSIM_URL,
        sha256=fingerprint(text),
        lfs_version=heading.group(1) if heading else None,
        insim_version=int(insim.group(1)) if insim else None,
    )


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def download(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "lfs-insim spec check"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body: bytes = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SpecError(f"could not download {url}: {error}") from error
    return body.decode(charset)


def read_outsim(lfs_dir: Path) -> str | None:
    """Return OutSimPack.txt from the LFS installation, or None if it is not there."""
    path = lfs_dir / "docs" / "OutSimPack.txt"
    if not path.is_file():
        return None
    # Old ANSI text file: latin-1 maps every byte, so reading never fails.
    return normalize(path.read_bytes().decode("latin-1"))


def write_atomic(path: Path, text: str) -> None:
    """Replace the file only once the new content is fully written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def load_checked() -> dict[str, dict[str, str | int]]:
    if not CHECKED_FILE.is_file():
        return {}
    data: dict[str, dict[str, str | int]] = json.loads(CHECKED_FILE.read_text(encoding="utf-8"))
    return data


def compare(name: str, info: SpecInfo, checked: dict[str, dict[str, str | int]]) -> bool:
    recorded = checked.get(name)
    versions = f"LFS {info.lfs_version}, INSIM_VERSION {info.insim_version}"
    label = f"{name} ({versions})" if info.lfs_version else name
    if recorded is None:
        print(f"  {label}: not checked yet (sha256 {info.sha256[:12]})")
        return False
    if recorded.get("sha256") == info.sha256:
        print(f"  {label}: matches the checked version")
        return True
    print(f"  {label}: CHANGED since the checked version")
    print(f"    checked: {recorded}")
    print(f"    now:     {info.to_json()}")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--accept", action="store_true", help="record the result as checked")
    parser.add_argument("--lfs-dir", type=Path, default=DEFAULT_LFS_DIR, help="LFS folder")
    args = parser.parse_args(argv)

    found: dict[str, SpecInfo] = {}
    try:
        insim_text = extract_insim(download(INSIM_URL))
    except SpecError as error:
        print(f"ERROR: {error}")
        print("  the previous copy in spec/cache/ was left untouched")
        return 2
    write_atomic(CACHE_DIR / "InSim.txt", insim_text)
    found["insim"] = describe_insim(insim_text)

    outsim_text = read_outsim(args.lfs_dir)
    if outsim_text is None:
        print(f"  outsim: skipped ({args.lfs_dir / 'docs' / 'OutSimPack.txt'} not found)")
    else:
        write_atomic(CACHE_DIR / "OutSimPack.txt", outsim_text)
        found["outsim"] = SpecInfo(
            source="<LFS>/docs/OutSimPack.txt", sha256=fingerprint(outsim_text)
        )

    checked = load_checked()
    matches = [compare(name, info, checked) for name, info in found.items()]
    if args.accept:
        checked.update({name: info.to_json() for name, info in found.items()})
        write_atomic(CHECKED_FILE, json.dumps(checked, indent=2) + "\n")
        print(f"recorded as checked in {CHECKED_FILE.relative_to(ROOT).as_posix()}")
        return 0
    return 0 if all(matches) else 1


if __name__ == "__main__":
    sys.exit(main())
