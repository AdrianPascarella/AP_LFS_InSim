"""Generate the packet classes of lfs_insim from the downloaded specification.

    .venv/Scripts/python scripts/fetch_spec.py          first, to fill spec/cache/
    .venv/Scripts/python scripts/generate_packets.py    write the generated modules
    .venv/Scripts/python scripts/generate_packets.py --check
                                                        exit 1 if they are not up to date

Input: spec/cache/InSim.txt, read by spec_parser, plus the hand-written exceptions in
spec_overrides. Output (tracked by git, never edited by hand):

  src/lfs_insim/packets/_enums.py    enums and flags (TINY.NCN, ISF.MCI)
  src/lfs_insim/packets/_insim.py    InSim packets and the structures inside them
  src/lfs_insim/packets/__init__.py  the public names

The code is passed through `ruff format`, so the dev tools must be installed.
"""

from __future__ import annotations

import argparse
import json
import keyword
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import spec_overrides as overrides
from spec_parser import Define, Field, Spec, SpecError, Struct, parse

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "spec" / "cache"
PACKAGE_DIR = ROOT / "src" / "lfs_insim" / "packets"
CHECKED_FILE = ROOT / "spec" / "checked.json"

SCALARS = {"byte": "B", "word": "H", "short": "h", "unsigned": "I", "int": "i", "float": "f"}
SIZES = {"B": 1, "H": 2, "h": 2, "I": 4, "i": 4, "f": 4, "b": 1}
BUILTIN_CLASSES = {"Vec": "Vec", "Vector": "Vector"}
PADDING = re.compile(overrides.PADDING_NAMES)
HAND_WRITTEN = {"PacketError": "_codec", "Vec": "_types", "Vector": "_types"}


@dataclass
class EnumClass:
    name: str
    doc: str
    members: list[Define]
    from_c_enum: bool  # values of a C enum (never flags) rather than #defines


def docstring(text: str, indent: str) -> str:
    """A docstring literal (with its indentation) for text taken from the specification."""
    text = " ".join(text.split()).replace("\\", "\\\\").replace('"', '\\"')
    if not text:
        return ""
    lines = textwrap.wrap(text, width=96 - len(indent))
    if len(lines) == 1:
        return f'{indent}"""{lines[0]}"""\n'
    body = "\n".join(indent + line for line in lines)
    return f'{indent}"""\n{body}\n{indent}"""\n'


def prefix_of(name: str) -> str:
    return name.split("_", 1)[0]


def collect_enums(spec: Spec) -> list[EnumClass]:
    classes: dict[str, EnumClass] = {}

    def add(name: str, doc: str, members: list[Define], from_c_enum: bool, where: str) -> None:
        if name in classes:
            raise SpecError(f"{where}: class {name} already exists (see GROUP_NAMES)")
        classes[name] = EnumClass(name, doc, members, from_c_enum)

    for enum in spec.enums:
        members = [Define(m.name, m.value, m.comment, enum.line) for m in enum.members]
        prefixes = {prefix_of(m.name) for m in members}
        if len(prefixes) != 1:
            raise SpecError(f"line {enum.line}: enum mixes prefixes {sorted(prefixes)}")
        add(prefixes.pop(), enum.comment or enum.heading, members, True, f"line {enum.line}")

    for group in spec.define_groups:
        runs: list[list[Define]] = []
        for define in group.defines:
            if runs and prefix_of(runs[-1][0].name) == prefix_of(define.name):
                runs[-1].append(define)
            else:
                runs.append([define])
        for index, run in enumerate(runs):
            first = run[0].name
            name = overrides.GROUP_NAMES.get(first, prefix_of(first))
            add(name, group.heading if index == 0 else "", run, False, f"line {run[0].line}")

    for value in spec.comment_values:
        prefix = prefix_of(value.name)
        if prefix not in overrides.COMMENT_VALUES:
            continue
        target = overrides.COMMENT_VALUES[prefix]
        if target not in classes:
            classes[target] = EnumClass(target, "", [], False)
        classes[target].members.append(value)

    for cls in classes.values():
        cls.members.sort(key=lambda m: m.value)
    return list(classes.values())


def member_name(cls: str, name: str) -> str:
    if name in overrides.MEMBER_NAMES:
        return overrides.MEMBER_NAMES[name]
    prefix = prefix_of(name)
    if name.startswith(cls + "_"):
        short = name[len(cls) + 1 :]
    elif prefix in overrides.KEEP_PREFIX:
        short = name
    else:
        short = name[len(prefix) + 1 :]
    if not short.isidentifier() or keyword.iskeyword(short) or short.startswith("_"):
        raise SpecError(f"{name}: {short!r} is not a valid member name (see MEMBER_NAMES)")
    return short


def is_flags(cls: EnumClass) -> bool:
    if cls.from_c_enum:
        return False
    singles = {m.value for m in cls.members if m.value > 0 and m.value & (m.value - 1) == 0}
    combined = 0
    for value in singles:
        combined |= value
    return all(
        m.value in singles or (m.value > 0 and m.value & ~combined == 0) for m in cls.members
    )


def emit_enums(classes: list[EnumClass], header: str) -> str:
    out = [header, '"""Enums and flags of the InSim specification (TINY.NCN, ISF.MCI)."""\n\n']
    out.append("from enum import IntEnum, IntFlag\n\n")
    out.append(f"__all__ = {sorted(c.name for c in classes)!r}\n")
    for cls in classes:
        base = "IntFlag" if is_flags(cls) else "IntEnum"
        c_names = sorted({prefix_of(m.name) for m in cls.members})
        doc = overrides.CLASS_DOCS.get(cls.name, cls.doc).rstrip(":").strip()
        doc = f"{doc}. " if doc else ""
        out.append(f"\n\nclass {cls.name}({base}):\n")
        out.append(docstring(f"{doc}C names: {', '.join(n + '_x' for n in c_names)}.", "    "))
        seen: set[str] = set()
        for member in cls.members:
            name = member_name(cls.name, member.name)
            if name in seen:
                raise SpecError(f"{member.name}: {cls.name}.{name} is defined twice")
            seen.add(name)
            out.append(f"\n    {name} = {member.value}\n")
            out.append(docstring(member.comment, "    "))
    return "".join(out)


@dataclass
class Column:
    """One field of a generated class: its layout entry and, if public, its dataclass field."""

    name: str
    codec: str
    annotation: str | None = None  # None = filled in by the library, not a dataclass field
    default: str = ""
    doc: str = ""


def item_codec(item: Field, struct_names: set[str]) -> tuple[str, str, str]:
    """(codec, annotation, default) of one value of the field's type."""
    if item.ctype in SCALARS:
        fmt = SCALARS[item.ctype]
        return f'_c.Scalar("{fmt}")', "float" if fmt == "f" else "int", "0.0" if fmt == "f" else "0"
    if item.ctype == "char":
        return '_c.Scalar("b")', "int", "0"  # a single char is a signed byte (CarContact.Steer)
    if item.ctype == "in_addr":
        return "_c.IPv4()", "IPv4Address", "field(default_factory=lambda: IPv4Address(0))"
    cls = BUILTIN_CLASSES.get(item.ctype, item.ctype)
    if cls in BUILTIN_CLASSES.values() or cls in struct_names:
        return f"_c.Nested({cls})", cls, f"field(default_factory={cls})"
    raise SpecError(f"no codec for type {item.ctype}")


def columns(struct: Struct, struct_names: set[str]) -> list[Column]:
    is_packet = struct.name.startswith("IS_")
    tail_text = overrides.TAIL_TEXT.get(struct.name)
    tail_array = overrides.TAIL_ARRAY.get(struct.name)
    if "variable size" in struct.comment and tail_text is None and tail_array is None:
        raise SpecError(f"{struct.name} has a variable size: add it to TAIL_TEXT or TAIL_ARRAY")
    result: list[Column] = []
    for index, item in enumerate(struct.fields):
        last = index == len(struct.fields) - 1
        if is_packet and index < 2:
            if item.name != ("Size", "Type")[index]:
                raise SpecError(f"{struct.name}: field {index} is {item.name}")
            result.append(Column(item.name, "_c." + item.name.upper()))
        elif tail_text is not None and item.name == tail_text[0]:
            if not last or item.ctype != "char":
                raise SpecError(f"{struct.name}.{item.name} is not trailing text")
            result.append(
                Column(item.name, f"_c.TailText({tail_text[1]})", "str", '""', item.comment)
            )
        elif item.commented_out:
            raise SpecError(f"{struct.name}.{item.name} is commented out: add it to TAIL_TEXT")
        elif tail_array is not None and item.name == tail_array[1]:
            fmt = SCALARS.get(item.ctype)
            if fmt is None:
                raise SpecError(f"{struct.name}.{item.name} is not a number")
            result.append(Column(item.name, f'_c.Count("{fmt}", of="{tail_array[0]}")'))
        elif tail_array is not None and item.name == tail_array[0]:
            if not last or item.count is None:
                raise SpecError(f"{struct.name}.{item.name} is not a trailing array")
            codec, annotation, _ = item_codec(item, struct_names)
            count = f', count="{tail_array[1]}"' if tail_array[1] else ""
            result.append(
                Column(
                    item.name,
                    f"_c.TailArray({codec}, {item.count}{count})",
                    f"list[{annotation}]",
                    "field(default_factory=list)",
                    item.comment,
                )
            )
        elif PADDING.match(item.name):
            fmt = "b" if item.ctype == "char" else SCALARS[item.ctype]
            result.append(Column(item.name, f"_c.Pad({SIZES[fmt] * (item.count or 1)})"))
        elif item.ctype == "char" and item.count is not None:
            terminated = "last byte" in item.comment
            codec = (
                f"_c.Text({item.count})"
                if terminated
                else f"_c.Text({item.count}, terminated=False)"
            )
            result.append(Column(item.name, codec, "str", '""', item.comment))
        elif item.count is not None:
            codec, annotation, default = item_codec(item, struct_names)
            if default.startswith("field("):
                factory = f"[{annotation}() for _ in range({item.count})]"
            else:
                factory = f"[{default}] * {item.count}"
            result.append(
                Column(
                    item.name,
                    f"_c.Array({codec}, {item.count})",
                    f"list[{annotation}]",
                    f"field(default_factory=lambda: {factory})",
                    item.comment,
                )
            )
        else:
            codec, annotation, default = item_codec(item, struct_names)
            result.append(Column(item.name, codec, annotation, default, item.comment))
    return result


def emit_insim(spec: Spec, enums: list[EnumClass], header: str) -> str:
    isp = {member_name("ISP", m.name) for c in enums if c.name == "ISP" for m in c.members}
    structs = [s for s in spec.structs.values() if s.name not in overrides.NOT_INSIM]
    names = {s.name for s in structs}
    body: list[str] = []
    for struct in structs:
        is_packet = struct.name.startswith("IS_")
        base = "InSimPacket" if is_packet else "Structure"
        body.append(f"\n\n@dataclass(kw_only=True)\nclass {struct.name}({base}):\n")
        body.append(docstring(struct.comment or struct.name, "    "))
        cols = columns(struct, names)
        for col in cols:
            if col.annotation is not None:
                body.append(f"\n    {col.name}: {col.annotation} = {col.default}\n")
                body.append(docstring(col.doc, "    "))
        if is_packet:
            if struct.name[3:] not in isp:
                raise SpecError(f"{struct.name} has no ISP_{struct.name[3:]} value")
            body.append(f"\n    _TYPE = ISP.{struct.name[3:]}\n")
        layout = "".join(f'        ("{c.name}", {c.codec}),\n' for c in cols)
        body.append(f"    _LAYOUT = (\n{layout}    )\n")
    packet_names = ", ".join(s.name for s in structs if s.name.startswith("IS_"))
    body.append(f"\n\n_c.register({packet_names})\n")
    text = "".join(body)
    out = [header, '"""InSim packets and the structures inside them."""\n\n']
    out.append("from __future__ import annotations\n\n")
    out.append("from dataclasses import dataclass, field\n")
    if "IPv4Address" in text:
        out.append("from ipaddress import IPv4Address\n")
    out.append("\n")
    out.append("from lfs_insim.packets import _codec as _c\n")
    out.append("from lfs_insim.packets._codec import InSimPacket, Structure\n")
    out.append("from lfs_insim.packets._enums import ISP\n")
    out.append("from lfs_insim.packets._types import Vec, Vector\n\n")
    out.append(f"__all__ = {sorted(s.name for s in structs)!r}\n")
    return "".join(out) + text


def emit_init(modules: dict[str, list[str]], header: str) -> str:
    out = [
        header,
        '"""InSim, OutSim and OutGauge packets, with the names of the specification."""\n\n',
    ]
    everything: list[str] = []
    for module, names in modules.items():
        everything += names
        out.append(f"from lfs_insim.packets.{module} import {', '.join(names)}\n")
    out.append(f"\n__all__ = {sorted(everything)!r}\n")
    return "".join(out)


def ruff(text: str, path: Path) -> str:
    """Sort imports and __all__ the way the lint expects, then format."""
    for command in (["check", "--fix", "--select", "I001,RUF022", "--quiet"], ["format"]):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", *command, "--stdin-filename", str(path), "-"],
            input=text.encode("utf-8"),
            capture_output=True,
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            raise SpecError(f"ruff {command[0]} failed on {path.name}: {result.stderr.decode()}")
        text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    return text


def generate() -> dict[Path, str]:
    """The generated modules: path -> content."""
    source = CACHE_DIR / "InSim.txt"
    if not source.exists():
        raise SpecError(f"{source} not found: run scripts/fetch_spec.py first")
    spec = parse(source.read_text(encoding="utf-8"), "InSim.txt")
    checked = json.loads(CHECKED_FILE.read_text(encoding="utf-8"))["insim"]
    header = (
        f"# Generated by scripts/generate_packets.py from the InSim specification of LFS "
        f"{checked['lfs_version']} (InSim {checked['insim_version']}).\n"
        "# Do not edit: change the generator or scripts/spec_overrides.py and run it again.\n"
    )
    enums = collect_enums(spec)
    insim = emit_insim(spec, enums, header)
    structs = [s.name for s in spec.structs.values() if s.name not in overrides.NOT_INSIM]
    modules = {
        "_codec": ["PacketError"],
        "_enums": sorted(c.name for c in enums),
        "_insim": sorted(structs),
        "_types": ["Vec", "Vector"],
    }
    files = {
        PACKAGE_DIR / "_enums.py": emit_enums(enums, header),
        PACKAGE_DIR / "_insim.py": insim,
        PACKAGE_DIR / "__init__.py": emit_init(modules, header),
    }
    return {path: ruff(text, path) for path, text in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report out-of-date files")
    args = parser.parse_args()
    try:
        files = generate()
    except SpecError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    stale = []
    for path, text in files.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            stale.append(path)
            if not args.check:
                path.write_bytes(text.encode("utf-8"))
    for path in stale:
        verb = "out of date" if args.check else "written"
        print(f"  {path.relative_to(ROOT).as_posix()}: {verb}")
    if not stale:
        print("  generated packets are up to date")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
