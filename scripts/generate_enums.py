"""Enums and flags for the generated packets (part of scripts/generate_packets.py).

Turns the C enums, groups of #defines and values listed in comments of the specification into
IntEnum and IntFlag classes, named as spec_overrides says.
"""

from __future__ import annotations

import keyword
import textwrap
from dataclasses import dataclass

import spec_overrides as overrides
from spec_parser import Define, Spec, SpecError


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
    body = enum_classes(classes)
    out = [header, '"""Enums and flags of InSim and OutGauge (TINY.NCN, ISF.MCI, OG.KM)."""\n\n']
    out.append(enum_import(body) + "\n")
    out.append(f"__all__ = {sorted(c.name for c in classes)!r}\n")
    return "".join(out) + body


def enum_import(text: str) -> str:
    bases = [b for b in ("IntEnum", "IntFlag") if f"({b})" in text]
    return f"from enum import {', '.join(bases)}\n" if bases else ""


def enum_classes(classes: list[EnumClass]) -> str:
    """The class statements of these enums and flags."""
    out: list[str] = []
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
