"""Read the C header text of the InSim specification into a plain model.

    model = spec_parser.parse(text, source="InSim.txt")

The input is what scripts/fetch_spec.py leaves in spec/cache/: InSim.txt (InSim, OutSim and
OutGauge) and OutSimPack.txt (OutSimPack2). The parser understands exactly the constructs those
files use (struct, enum, #define, const int) and raises SpecError, with the line number, on
anything else. Nothing is skipped silently: when lfs.net adds a construct, generation stops.

Naming, grouping into Python classes and variable-size layouts are not decided here; that is the
job of the generator and its hand-written exceptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

PRIMITIVE_TYPES = frozenset({"char", "byte", "word", "short", "unsigned", "int", "float"})
# Types used by the specification but only described in comments, never declared as a struct.
BUILTIN_TYPES = frozenset({"Vec", "Vector", "in_addr"})

STRUCT_START = re.compile(r"^struct\s+(\w+)\s*(?://\s*(.*))?$")
ENUM_START = re.compile(r"^enum\s*(?://\s*(.*))?$")
DEFINE = re.compile(r"^#define\s+(\w+)(?:\s+([^/]+?))?\s*(?://\s*(.*))?$")
CONST = re.compile(r"^const\s+int\s+(\w+)\s*=\s*([^;]+);\s*(?://\s*(.*))?$")
FIELD = re.compile(r"^(\w+)\s+(\w+)\s*(?:\[\s*(\w+)\s*\])?\s*;\s*(?://\s*(.*))?$")
ENUM_MEMBER = re.compile(r"^(\w+)\s*(?:=\s*([^,/]+?))?\s*,?\s*(?://\s*(.*))?$")
CONDITION = re.compile(r"^if\s*\(\s*\w+\s*&\s*(\w+)\s*\)$")
HEADER_GUARD = re.compile(r"^#(?:ifndef|endif)\b")
INT_LITERAL = re.compile(r"^(?:0[xX][0-9a-fA-F]+|\d+)$")
OR_EXPRESSION = re.compile(r"^\(\s*\w+(?:\s*\|\s*\w+)+\s*\)$")


class SpecError(Exception):
    """The specification contains something this parser does not understand."""


@dataclass(frozen=True)
class Field:
    ctype: str
    name: str
    comment: str
    count: int | None = None  # array length; None = not an array (or a symbolic length)
    count_name: str | None = None  # the symbol in the brackets, when it is not a literal
    commented_out: bool = False  # e.g. "// char Text[TEXT_SIZE];": variable trailing text
    condition: str | None = None  # OutSimPack2: present only if this OSO_ option is set


@dataclass(frozen=True)
class Struct:
    name: str
    comment: str
    heading: str  # the comment paragraph just above, if any
    fields: tuple[Field, ...]
    line: int


@dataclass(frozen=True)
class EnumMember:
    name: str
    value: int
    comment: str


@dataclass(frozen=True)
class Enum:
    comment: str
    heading: str
    members: tuple[EnumMember, ...]
    line: int


@dataclass(frozen=True)
class Define:
    name: str
    value: int
    comment: str
    line: int


@dataclass(frozen=True)
class DefineGroup:
    """Consecutive #defines, separated only by blank or comment lines."""

    heading: str
    defines: tuple[Define, ...]


@dataclass(frozen=True)
class Constant:
    name: str
    value: int
    comment: str
    line: int


@dataclass
class Spec:
    source: str
    structs: dict[str, Struct] = field(default_factory=dict)
    enums: list[Enum] = field(default_factory=list)
    define_groups: list[DefineGroup] = field(default_factory=list)
    constants: dict[str, Constant] = field(default_factory=dict)


class _Parser:
    def __init__(self, text: str, source: str) -> None:
        self.lines = text.splitlines()
        self.spec = Spec(source)
        self.index = 0
        self.paragraph: list[str] = []  # last top-level comment paragraph
        self.blanks_after_paragraph = 0
        self.group: list[Define] = []
        self.group_heading = ""
        self.values: dict[str, int] = {}  # every define and constant seen so far

    def error(self, message: str, line: int | None = None) -> SpecError:
        number = self.index + 1 if line is None else line
        return SpecError(f"{self.spec.source}:{number}: {message}")

    def heading(self) -> str:
        return " ".join(self.paragraph) if self.blanks_after_paragraph <= 1 else ""

    def close_group(self) -> None:
        if self.group:
            self.spec.define_groups.append(DefineGroup(self.group_heading, tuple(self.group)))
            self.group = []

    def value(self, expression: str) -> int:
        expression = expression.strip()
        if INT_LITERAL.match(expression):
            return int(expression, 0)
        if OR_EXPRESSION.match(expression):
            result = 0
            for name in expression.strip("()").split("|"):
                result |= self.symbol(name.strip())
            return result
        raise self.error(f"unsupported value {expression!r}")

    def symbol(self, name: str) -> int:
        if name not in self.values:
            raise self.error(f"unknown symbol {name!r}")
        return self.values[name]

    def parse(self) -> Spec:
        while self.index < len(self.lines):
            raw = self.lines[self.index]
            code = raw.strip()
            if not code:
                self.blanks_after_paragraph += 1
            elif code.startswith("//"):
                if self.blanks_after_paragraph > 0 or not self.paragraph:
                    self.paragraph = []
                self.paragraph.append(code[2:].strip())
                self.blanks_after_paragraph = 0
            else:
                self.statement(code)
                self.paragraph = []
                self.blanks_after_paragraph = 0
            self.index += 1
        self.close_group()
        self.check_types()
        return self.spec

    def statement(self, code: str) -> None:
        if HEADER_GUARD.match(code):
            return
        if match := DEFINE.match(code):
            name, value, comment = match.groups()
            if value is None:  # the header guard: #define _ISPACKETS_H_
                if not name.startswith("_"):
                    raise self.error(f"#define {name} has no value")
                return
            if not self.group:
                self.group_heading = self.heading()
            define = Define(name, self.value(value), comment or "", self.index + 1)
            self.values[name] = define.value
            self.group.append(define)
            return
        self.close_group()
        if match := CONST.match(code):
            name, value, comment = match.groups()
            constant = Constant(name, self.value(value), comment or "", self.index + 1)
            self.values[name] = constant.value
            self.spec.constants[name] = constant
        elif match := STRUCT_START.match(code):
            self.struct(match.group(1), match.group(2) or "")
        elif match := ENUM_START.match(code):
            self.enum(match.group(1) or "")
        else:
            raise self.error(f"unexpected statement {code!r}")

    def body(self) -> list[tuple[int, str]]:
        """Lines between '{' and '};' (stripped, blanks removed), leaving index on '};'."""
        start = self.index + 1
        self.index += 1
        if self.index >= len(self.lines) or self.lines[self.index].strip() != "{":
            raise self.error("expected '{'", start)
        lines: list[tuple[int, str]] = []
        while True:
            self.index += 1
            if self.index >= len(self.lines):
                raise self.error("block never closed", start)
            code = self.lines[self.index].strip()
            if code == "};":
                return lines
            if code:
                lines.append((self.index + 1, code))

    def struct(self, name: str, comment: str) -> None:
        line, heading = self.index + 1, self.heading()
        if name in self.spec.structs:
            raise self.error(f"struct {name} defined twice")
        fields: list[Field] = []
        condition: str | None = None
        for number, code in self.body():
            commented_out = False
            if code.startswith("//"):
                inner = code[2:].strip()
                if match := CONDITION.match(inner):
                    condition = match.group(1)
                    continue
                code, commented_out = inner, True
            match = FIELD.match(code)
            if match is None:
                raise self.error(f"unexpected line in struct {name}: {code!r}", number)
            ctype, field_name, count, field_comment = match.groups()
            item = self.field(ctype, field_name, count, field_comment or "", commented_out, number)
            fields.append(replace(item, condition=condition))
        self.spec.structs[name] = Struct(name, comment, heading, tuple(fields), line)

    def field(
        self,
        ctype: str,
        name: str,
        count: str | None,
        comment: str,
        commented_out: bool,
        line: int,
    ) -> Field:
        if count is None:
            return Field(ctype, name, comment, commented_out=commented_out)
        if INT_LITERAL.match(count):
            return Field(ctype, name, comment, int(count, 0), commented_out=commented_out)
        if count in self.values:
            return Field(ctype, name, comment, self.values[count], count, commented_out)
        if commented_out:  # e.g. Text[TEXT_SIZE]: the length is described in the comments
            return Field(ctype, name, comment, None, count, commented_out)
        raise self.error(f"unknown array length {count!r}", line)

    def enum(self, comment: str) -> None:
        line, heading = self.index + 1, self.heading()
        members: list[EnumMember] = []
        next_value = 0
        for number, code in self.body():
            match = ENUM_MEMBER.match(code)
            if match is None or code.startswith("//"):
                raise self.error(f"unexpected line in enum: {code!r}", number)
            name, value, member_comment = match.groups()
            if value is not None:
                next_value = self.value(value)
            members.append(EnumMember(name, next_value, member_comment or ""))
            self.values[name] = next_value
            next_value += 1
        if not members:
            raise self.error("empty enum", line)
        self.spec.enums.append(Enum(comment, heading, tuple(members), line))

    def check_types(self) -> None:
        known = PRIMITIVE_TYPES | BUILTIN_TYPES | self.spec.structs.keys()
        for struct in self.spec.structs.values():
            for item in struct.fields:
                if item.ctype not in known:
                    raise self.error(
                        f"struct {struct.name}: field {item.name} has unknown type {item.ctype!r}",
                        struct.line,
                    )


def parse(text: str, source: str) -> Spec:
    """Parse one specification file. Raises SpecError on anything not understood."""
    return _Parser(text, source).parse()
