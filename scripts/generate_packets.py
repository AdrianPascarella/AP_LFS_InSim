"""Generate the packet classes of lfs_insim from the downloaded specification.

    .venv/Scripts/python scripts/fetch_spec.py          first, to fill spec/cache/
    .venv/Scripts/python scripts/generate_packets.py    write the generated modules
    .venv/Scripts/python scripts/generate_packets.py --check
                                                        exit 1 if they are not up to date

Input: spec/cache/InSim.txt and spec/cache/OutSimPack.txt (only copied where LFS is installed),
read by spec_parser, plus the hand-written exceptions in spec_overrides. The enums are built by
generate_enums. Output (tracked by git, never edited by hand):

  src/lfs_insim/packets/_enums.py     enums and flags of InSim.txt (TINY.NCN, ISF.MCI)
  src/lfs_insim/packets/_insim.py     InSim packets and the structures inside them
  src/lfs_insim/packets/_outgauge.py  OutGaugePack
  src/lfs_insim/packets/_outsim.py    OutSimPack, OutSimPack2 and OSO   (need OutSimPack.txt)
  src/lfs_insim/packets/__init__.py   the public names                  (need OutSimPack.txt)

Without OutSimPack.txt, as in the CI, the last two are skipped and the rest is still checked.
The code is passed through `ruff format`, so the dev tools must be installed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import spec_overrides as overrides
from generate_enums import (
    EnumClass,
    collect_enums,
    docstring,
    emit_enums,
    enum_classes,
    enum_import,
    member_name,
    prefix_of,
)
from spec_parser import Field, Spec, SpecError, Struct, parse

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
class Column:
    """One field of a generated class: its layout entry and, if public, its dataclass field."""

    name: str
    codec: str
    annotation: str | None = None  # None = filled in by the library, not a dataclass field
    default: str = ""
    doc: str = ""


def item_codec(item: Field, struct_names: set[str]) -> tuple[str, str, str]:
    """(codec, annotation, default) of one value of the field's type."""
    if item.name in overrides.SKIN_IDS or "SkinID" in item.comment:
        if item.name not in overrides.SKIN_IDS or item.ctype != "unsigned":
            raise SpecError(f"{item.name} holds a SkinID: check SKIN_IDS")
        return "_c.SkinID()", "str", '"000000"'
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


def magic_fields(struct: Struct) -> int:
    """How many leading fields form the struct's MAGIC marker (0 if it has none)."""
    magic = overrides.MAGIC.get(struct.name)
    if magic is None:
        return 0
    head = struct.fields[: len(magic)]
    if [(f.ctype, f.name, f.count) for f in head] != [("char", c, None) for c in magic]:
        raise SpecError(f"{struct.name} does not start with the chars of {magic!r}")
    if len({f.condition for f in head}) != 1:
        raise SpecError(f"{struct.name}: the chars of {magic!r} have different conditions")
    return len(magic)


def columns(struct: Struct, struct_names: set[str]) -> list[Column]:
    """The layout of a struct: its plain columns, with optional and conditional parts wrapped."""
    optional = overrides.OPTIONAL_TAIL.get(struct.name)
    skip = magic_fields(struct)
    result: list[Column] = []
    if any(item.condition for item in struct.fields):
        doc = "OSO_x options LFS sends this packet with (OutSim Opts in cfg.txt); not in the bytes"
        result.append(Column(overrides.OPTIONS_FIELD, "_c.Options()", "int", "0", doc))
    if skip:
        magic = overrides.MAGIC[struct.name].encode("ascii")
        plain = [Column("Magic", f"_c.Magic({magic!r})")]
        plain += plain_columns(struct, struct_names)[skip:]
    else:
        plain = plain_columns(struct, struct_names)
    items = [struct.fields[0], *struct.fields[skip:]] if skip else list(struct.fields)
    for index, (item, col) in enumerate(zip(items, plain, strict=True)):
        if item.name == optional:
            if index != len(items) - 1:
                raise SpecError(f"{struct.name}.{item.name} is optional but not the last field")
            col = wrapped(col, "_c.Optional({})")
        elif "optional - only if" in item.comment:
            raise SpecError(f"{struct.name}.{item.name} is optional: add it to OPTIONAL_TAIL")
        if item.condition:
            cls = prefix_of(item.condition)
            option = f"{cls}.{member_name(cls, item.condition)}"
            col = wrapped(col, f'_c.When({option}, {{}}, of="{overrides.OPTIONS_FIELD}")')
        result.append(col)
    if optional is not None and optional not in {c.name for c in result}:
        raise SpecError(f"{struct.name} has no field {optional} (see OPTIONAL_TAIL)")
    return result


def wrapped(col: Column, codec: str) -> Column:
    """The column with its codec inside another one that can leave it out (value None)."""
    annotation = None if col.annotation is None else f"{col.annotation} | None"
    default = None if col.annotation is None else "None"
    return Column(col.name, codec.format(col.codec), annotation, default or "", col.doc)


def plain_columns(struct: Struct, struct_names: set[str]) -> list[Column]:
    """One column per field of the struct, as if every field were always present."""
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
        elif item.name in overrides.CAR_NAMES or "skin prefix" in item.comment:
            if item.name not in overrides.CAR_NAMES or (item.ctype, item.count) != ("char", 4):
                raise SpecError(f"{struct.name}.{item.name} names a car: check CAR_NAMES")
            doc = f"{item.comment}: an official car ('XFG'), a mod's SkinID ('5A1FB3') or ''"
            result.append(Column(item.name, "_c.CarName()", "str", '""', doc))
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


MODULE_DOCS = {
    "_insim": "InSim packets and the structures inside them.",
    "_outsim": "OutSim packets: OutSimPack, and OutSimPack2 with the parts chosen in OutSim Opts.",
    "_outgauge": "OutGauge packets.",
}


def emit_structs(
    module: str,
    structs: list[Struct],
    enums: list[EnumClass],
    local_enums: list[EnumClass],
    header: str,
) -> str:
    """A module of structs. `local_enums` are defined in it (they come from the same file)."""
    isp = {member_name("ISP", m.name) for c in enums if c.name == "ISP" for m in c.members}
    names = {s.name for s in structs}
    body: list[str] = []
    for struct in structs:
        is_packet = struct.name.startswith("IS_")
        cols = columns(struct, names)
        if is_packet:
            base = "InSimPacket"
        elif any(c.codec.startswith("_c.When(") for c in cols):
            base = "OptionalParts"
        else:
            base = "Structure"
        body.append(f"\n\n@dataclass(kw_only=True)\nclass {struct.name}({base}):\n")
        body.append(docstring(struct.comment or struct.name, "    "))
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
    if packet_names:
        body.append(f"\n\n_c.register({packet_names})\n")
    text = enum_classes(local_enums) + "".join(body)
    out = [header, f'"""{MODULE_DOCS[module]}"""\n\n']
    out.append("from __future__ import annotations\n\n")
    out.append(enum_import(text))
    out.append("from dataclasses import dataclass")
    out.append(", field\n" if "field(" in text else "\n")
    if "IPv4Address" in text:
        out.append("from ipaddress import IPv4Address\n")
    out.append("\n")
    out.append("from lfs_insim.packets import _codec as _c\n")
    bases = [b for b in ("InSimPacket", "OptionalParts", "Structure") if f"({b})" in text]
    out.append(f"from lfs_insim.packets._codec import {', '.join(bases)}\n")
    used = [c.name for c in enums if re.search(rf"\b{c.name}\.", text) and c not in local_enums]
    if used:
        out.append(f"from lfs_insim.packets._enums import {', '.join(used)}\n")
    types = [t for t in ("Vec", "Vector") if re.search(rf"\b{t}\b", text)]
    if types:
        out.append(f"from lfs_insim.packets._types import {', '.join(types)}\n")
    exported = names | {c.name for c in local_enums}
    out.append(f"\n__all__ = {sorted(exported)!r}\n")
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


def read_spec(name: str) -> Spec | None:
    source = CACHE_DIR / name
    if not source.exists():
        return None
    return parse(source.read_text(encoding="utf-8"), name)


def generate() -> tuple[dict[Path, str], list[Path]]:
    """The generated modules (path -> content), and those skipped for lack of OutSimPack.txt.

    OutSimPack.txt only exists where LFS is installed (P3). Without it, the modules that come from
    InSim.txt alone are still generated: that is what the CI can check.
    """
    insim = read_spec("InSim.txt")
    if insim is None:
        raise SpecError(f"{CACHE_DIR / 'InSim.txt'} not found: run scripts/fetch_spec.py first")
    outsim = read_spec("OutSimPack.txt")
    checked = json.loads(CHECKED_FILE.read_text(encoding="utf-8"))["insim"]
    source = (
        f"# Generated by scripts/generate_packets.py from the InSim specification of LFS "
        f"{checked['lfs_version']} (InSim {checked['insim_version']})"
    )
    rule = "# Do not edit: change the generator or scripts/spec_overrides.py and run it again.\n"
    header = f"{source}.\n{rule}"
    enums = collect_enums(insim)
    by_module: dict[str, list[Struct]] = {"_insim": [], "_outsim": [], "_outgauge": []}
    for struct in insim.structs.values():
        by_module[overrides.MODULES.get(struct.name, "_insim")].append(struct)
    files = {
        PACKAGE_DIR / "_enums.py": emit_enums(enums, header),
        **{
            PACKAGE_DIR / f"{module}.py": emit_structs(module, by_module[module], enums, [], header)
            for module in ("_insim", "_outgauge")
        },
    }
    skipped = [PACKAGE_DIR / "_outsim.py", PACKAGE_DIR / "__init__.py"]
    if outsim is not None:
        header = f"{source}\n# and LFS's docs/OutSimPack.txt.\n{rule}"
        outsim_enums = collect_enums(outsim)
        clash = {c.name for c in enums} & {c.name for c in outsim_enums}
        if clash:
            raise SpecError(f"classes in both InSim.txt and OutSimPack.txt: {sorted(clash)}")
        by_module["_outsim"] += outsim.structs.values()
        files[PACKAGE_DIR / "_outsim.py"] = emit_structs(
            "_outsim", by_module["_outsim"], enums, outsim_enums, header
        )
        modules = {
            "_codec": ["PacketError"],
            "_enums": sorted(c.name for c in enums),
            **{module: sorted(s.name for s in structs) for module, structs in by_module.items()},
            "_types": ["Vec", "Vector"],
        }
        modules["_outsim"] = sorted(modules["_outsim"] + [c.name for c in outsim_enums])
        files[PACKAGE_DIR / "__init__.py"] = emit_init(modules, header)
        skipped = []
    return {path: ruff(text, path) for path, text in files.items()}, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report out-of-date files")
    args = parser.parse_args()
    try:
        files, skipped = generate()
    except SpecError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for path in skipped:
        print(f"  {path.relative_to(ROOT).as_posix()}: skipped (needs spec/cache/OutSimPack.txt)")
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
