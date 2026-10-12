"""Everything about the generated packets that the specification does not say mechanically.

This file is data, written by hand and kept small on purpose: each entry exists because the C
header cannot express it. scripts/generate_packets.py stops with an error when the specification
contains something these tables do not cover (a new variable-size packet, a name that is not a
valid identifier, two classes with the same name), so an entry is only added when generation asks
for it.
"""

from __future__ import annotations

# Fields named like these are spare bytes: always zero, not exposed (D3). SpClose is not spare:
# it carries the closing speed.
PADDING_NAMES = r"^(Zero|Sp[0-9]|Spare[0-9]?|SpA|SpB|SpW|SpF[0-9])$"

# Variable-size packets whose last field is text: packet -> (field, maximum size in bytes).
# Size grows in steps of 4 bytes with the text, which always ends with at least one zero.
TAIL_TEXT: dict[str, tuple[str, int]] = {
    "IS_MSO": ("Msg", 128),
    "IS_III": ("Msg", 64),
    "IS_ACR": ("Text", 64),
    "IS_MTC": ("Text", 128),  # declared only in a comment: Text[TEXT_SIZE]
    "IS_BTN": ("Text", 240),  # declared only in a comment: Text[TEXT_SIZE]
}

# Variable-size packets whose last field is an array: packet -> (array field, counter field).
# The counter is filled in from the length of the list; None = the items simply fill the packet.
TAIL_ARRAY: dict[str, tuple[str, str | None]] = {
    "IS_NLP": ("Info", "NumP"),
    "IS_MCI": ("Info", "NumC"),
    "IS_PLH": ("HCaps", "NumP"),
    "IS_MAL": ("SkinID", "NumM"),
    "IS_IPB": ("BanIPs", "NumB"),
    "IS_AXM": ("Info", "NumO"),
    "IS_AIC": ("Inputs", None),
}

# Structs in InSim.txt that are not InSim packets, and the module they go to. Every struct of
# OutSimPack.txt goes to _outsim.
MODULES: dict[str, str] = {
    "OutSimPack": "_outsim",
    "OutGaugePack": "_outgauge",
}

# Trailing fields that LFS only sends in some configurations ("optional - only if OutSim ID is
# specified"): they are None when absent.
OPTIONAL_TAIL: dict[str, str] = {
    "OutSimPack": "ID",
    "OutGaugePack": "ID",
}

# Single chars at the start of a struct that are a fixed marker, not data: struct -> the marker.
MAGIC: dict[str, str] = {
    "OutSimPack2": "LFST",  # char L; char F; char S; char T;
}

# Name of the field that holds the options of a struct with "// if (OSOpts & OSO_x)" parts. It is
# the name the specification uses in those comments; it is not part of the bytes.
OPTIONS_FIELD = "OSOpts"

# Groups of #defines (named by their first #define) whose class name is not their prefix,
# because the prefix is already taken by another class.
GROUP_NAMES: dict[str, str] = {
    "ISB_LMB": "ISB_CLICK",  # click flags in IS_BTC; ISB is the button style
    "PMO_FILE_END": "PMOF",  # PMOFlags in IS_AXM; PMO is the action enum
    "OCO_INDEX_MAIN": "OCO_INDEX",  # Index in IS_OCO; OCO is the action enum
}

# Values that only appear in comments, by prefix -> the class they join.
COMMENT_VALUES: dict[str, str] = {
    "CS": "CS",  # AIInputVal.Input: CS_MSX 0, CS_THROTTLE 1, ...
    "HOSTF": "HOSTF",  # IS_STA / IS_RST Flags
    "AXO": "OCO_INDEX",  # IS_OCO Index: AXO_START_LIGHTS1 149, ...
}

# Class docstrings where the comment above the values in the specification does not describe them.
CLASS_DOCS: dict[str, str] = {
    "OCO_INDEX": "Index byte of IS_OCO: which start lights to override",
    "OSO": "Parts of OutSimPack2 chosen by OutSim Opts in cfg.txt (hexadecimal; 1ff = all of them)",
}

# Class prefixes whose members keep their full C name (the prefix is not stripped).
KEEP_PREFIX: frozenset[str] = frozenset({"AXO"})

# Member names that would not be valid Python identifiers once the prefix is removed.
MEMBER_NAMES: dict[str, str] = {
    "PENALTY_30": "SECONDS_30",
    "PENALTY_45": "SECONDS_45",
    "JRR_2": "UNUSED_2",  # placeholders in the C enum, kept so the numbering stays visible
    "JRR_3": "UNUSED_3",
    "JRR_6": "UNUSED_6",
    "JRR_7": "UNUSED_7",
    "OCO_1": "UNUSED_1",
    "OCO_2": "UNUSED_2",
    "OCO_3": "UNUSED_3",
    "DL_18": "BIT_18",
    "DL_19": "BIT_19",
    "DL_20": "BIT_20",
    "DL_21": "BIT_21",
    "DL_22": "BIT_22",
    "DL_23": "BIT_23",
}
