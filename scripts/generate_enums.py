"""Enums and flags for the generated packets (part of scripts/generate_packets.py).

Turns the C enums, groups of #defines and values listed in comments of the specification into
IntEnum and IntFlag classes, named as spec_overrides says.
"""

from __future__ import annotations

import keyword
import re
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field, replace

import spec_overrides as overrides
from spec_parser import Define, Spec, SpecError


@dataclass
class EnumClass:
    name: str
    doc: str
    members: list[Define]
    from_c_enum: bool  # values of a C enum or a comment (never flags) rather than #defines
    fields: list[str] = field(default_factory=list)  # "IS_NPL.PType": named only in its comment


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


def with_note(text: str, key: str) -> str:
    """The text from the specification, then what was seen in the game (overrides.NOTES)."""
    return ". ".join(filter(None, (text, overrides.NOTES.get(key))))


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

    commented = [(key, cls, bit_members, False) for key, cls in overrides.BIT_COMMENTS.items()]
    commented += [(key, cls, value_members, True) for key, cls in overrides.VALUE_COMMENTS.items()]
    for (struct_name, field_name), target, read, never_flags in commented:
        struct = spec.structs.get(struct_name)
        if struct is None:
            continue  # another specification (OutSimPack.txt)
        item = next((f for f in struct.fields if f.name == field_name), None)
        if item is None:
            raise SpecError(
                f"{struct_name}.{field_name} is gone (see BIT_COMMENTS / VALUE_COMMENTS)"
            )
        members = read(target, item.comment, struct.line)
        known = classes.get(target)
        if known is None or not known.fields:
            add(target, "", members, never_flags, struct_name)
        elif [(m.name, m.value) for m in known.members] != [(m.name, m.value) for m in members]:
            raise SpecError(f"{struct_name}.{field_name}: not the same values as {known.fields}")
        classes[target].fields.append(f"{struct_name}.{field_name}")

    if "AIInputVal" in spec.structs:  # not in another specification (OutSimPack.txt)
        input_values(spec, classes, add)

    for cls in classes.values():
        cls.members.sort(key=lambda m: m.value)
    return list(classes.values())


def input_values(spec: Spec, classes: dict[str, EnumClass], add: Callable[..., None]) -> None:
    """The classes of AIInputVal.Value (LISTED_VALUES, HAND_VALUES), named in each CS_x input."""
    inputs = {value.name: value for value in spec.comment_values if value.name.startswith("CS_")}
    paragraphs = {lines[0]: (line, lines[1:]) for line, lines in spec.paragraphs}
    named: dict[str, str] = {}  # CS_x -> the class of its values
    for key, target in overrides.LISTED_VALUES.items():
        if key in inputs:
            comment = inputs[key].comment
            start = FIRST_VALUE.search(comment)
            text = comment[start.start() :] if start else comment
            add(target, "", value_members(target, text, inputs[key].line), True, key)
            named[key] = target
            classes[target].fields.append("AIInputVal.Value")
        elif key in paragraphs:
            line, lines = paragraphs[key]
            add(target, "", value_members(target, " / ".join(lines), line), True, key)
            classes[target].fields.append("AIInputVal.Value")
            named.update({n: target for n, v in inputs.items() if v.comment == target.lower()})
        else:
            raise SpecError(f"{key!r} is gone from the specification (see LISTED_VALUES)")
    for key, (target, members) in overrides.HAND_VALUES.items():
        if key not in inputs:
            raise SpecError(f"{key} is gone from the specification (see HAND_VALUES)")
        line = inputs[key].line
        add(target, "", [Define(n, v, c, line) for n, v, c in members], True, key)
        classes[target].fields.append("AIInputVal.Value")
        named[key] = target
    cs = classes["CS"]
    cs.members = [
        replace(m, comment=f"{m.comment}. Values: {named[m.name]}") if m.name in named else m
        for m in cs.members
    ]


BIT = re.compile(r"^bit (\d+): ([A-Za-z][A-Za-z ]*?)\s*(\([^)]*\))?$")  # an aside in brackets


def bit_members(cls: str, comment: str, line: int) -> list[Define]:
    """The bits of a comment like "bit 0: female / bit 1: AI", named as cls_FEMALE, cls_AI."""
    members = []
    for part in comment.split("/"):
        match = BIT.match(part := part.strip())
        if match is None:
            raise SpecError(f"line {line}: {part!r} is not 'bit N: name' (see BIT_COMMENTS)")
        bit, words, _ = match.groups()
        name = "_".join(words.upper().split())
        members.append(Define(f"{cls}_{name}", 1 << int(bit), part, line))
    return members


# "0 = off", "1: cancel", "1 - processed", "1 hard left"; "5: left+" (renamed in MEMBER_NAMES)
VALUE = re.compile(r"^(\d+)\s*(?:[=:-]\s*)?([A-Za-z][A-Za-z0-9 +]*?)\s*(\([^)]*\))?$")
# Where the values start in the comment of a CS_x input ("hold siren - 1:fast / 2:slow")
FIRST_VALUE = re.compile(r"\d+\s*(?:[=:-]\s*)?[A-Za-z]")


def value_members(cls: str, comment: str, line: int) -> list[Define]:
    """The values of a comment like "0 = off / 1 = weak", named as cls_OFF, cls_WEAK."""
    members = []
    for part in comment.split("/"):
        match = VALUE.match(part := part.strip())
        if match is None:
            raise SpecError(f"line {line}: {part!r} is not 'N = name' (see VALUE_COMMENTS)")
        value, words, _ = match.groups()
        name = "_".join(words.upper().split())
        members.append(Define(f"{cls}_{name}", int(value), part, line))
    return members


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
        if cls.fields:
            kind = "Values" if cls.from_c_enum else "Bits"
            names = (
                f"{kind} of {' and '.join(cls.fields)}, as InSim.txt describes them in a comment "
                "(no C names)."
            )
        else:
            names = f"C names: {', '.join(n + '_x' for n in c_names)}."
        out.append(docstring(doc + names, "    "))
        seen: set[str] = set()
        for member in cls.members:
            name = member_name(cls.name, member.name)
            if name in seen:
                raise SpecError(f"{member.name}: {cls.name}.{name} is defined twice")
            seen.add(name)
            out.append(f"\n    {name} = {member.value}\n")
            out.append(docstring(with_note(member.comment, f"{cls.name}.{name}"), "    "))
    return "".join(out)
