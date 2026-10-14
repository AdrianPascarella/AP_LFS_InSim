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

# Fields that name a car. For a mod, LFS puts its SkinID in CName as a 32-bit unsigned (Scawen,
# lfs.net forum thread "New InSim packet size byte and mod info"; InSim.txt only says "skin
# prefix"). Both are read as str: "XFG", or the SkinID's hex "5A1FB3".
# OutGaugePack.Car too ("Car name" in the spec): LFS 0.8C31 sends a mod's SkinID there (S12).
CAR_NAMES = frozenset({"CName", "Car"})  # char[4]: official car or SkinID
SKIN_IDS = frozenset({"SkinID"})  # unsigned: SkinID only

# Variable-size packets whose last field is text: packet -> (field, maximum size in bytes).
# Size grows in steps of 4 bytes with the text, which always ends with at least one zero.
TAIL_TEXT: dict[str, tuple[str, int]] = {
    "IS_MSO": ("Msg", 128),
    "IS_III": ("Msg", 64),
    "IS_ACR": ("Text", 64),
    "IS_MTC": ("Text", 128),  # declared only in a comment: Text[TEXT_SIZE]
    "IS_BTN": ("Text", 240),  # declared only in a comment: Text[TEXT_SIZE]
}

# Packets whose trailing text starts in the code page held by another field: packet -> that
# field (0.8C27: "Code page of message is now included in IS_MSO", Scawen, lfs.net forum thread
# "0.8C Downloads and Updates", post 2177567). Elsewhere text starts in Latin-1.
TEXT_CODE_PAGES: dict[str, str] = {
    "IS_MSO": "MSOData",
}

# Packets whose trailing text may start with a caption: packet -> name of the extra str field.
# InSim.txt, after IS_BTN: "If the first character of IS_BTN's Text field is zero, LFS will read
# the caption up to the second zero. The visible button text then follows that second zero."
CAPTIONS: dict[str, str] = {
    "IS_BTN": "Caption",
}

# Fields that give a byte offset into the packet's trailing text: packet -> field. They are
# exposed as an index into the str, since code page switches are not in it ("first character of
# the actual text", IS_MSO.TextStart).
TEXT_STARTS: dict[str, str] = {
    "IS_MSO": "TextStart",
}

# Hand-written classes added as a base of a generated packet, for properties that the
# specification does not give: packet -> class in src/lfs_insim/packets/_extras.py.
EXTRAS: dict[str, str] = {
    "IS_MSO": "MSOText",  # .text: what the user typed (W4.1)
    # Units (W8.3), with the scales the comments of InSim.txt give
    "CompCar": "CompCarUnits",  # .x_m, .speed_kmh, .heading_deg...
    "CarContact": "ContactUnits",  # 16 = 1 m, 128 = 180 degrees
    "CarContOBJ": "ContactUnits",
    "IS_CON": "ClosingSpeed",  # .closing_speed_mps
    "IS_OBH": "ClosingSpeed",
    "OutGaugePack": "GaugeUnits",  # .speed_kmh, .speed_mph
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

# Fixed arrays in which an item of zeros means none (PLID 0: no player; a zero CarHCP: no
# handicap): a shorter list is filled with zeros when sent. Not Tyres, where 0 is a real tyre.
ZERO_FILLED: dict[str, str] = {
    "IS_REO": "PLID",
    "IS_HCP": "Info",
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

# Fields whose bits are described only in their own comment, with no C names ("bit 0: female /
# bit 1: AI"): (struct, field) -> the IntFlag class they become. Its members are the words of the
# comment in capitals; a comment that no longer reads like that stops the generation.
BIT_COMMENTS: dict[tuple[str, str], str] = {
    ("IS_NPL", "PType"): "PTYPE",  # bit 0: female / bit 1: AI / bit 2: remote
    ("IS_NCN", "Flags"): "NCNF",  # bit 2: remote
    ("IS_SCH", "Flags"): "SCHF",  # bit 0: SHIFT / bit 1: CTRL
    ("PlayerHCap", "Flags"): "PLHF",  # bit 0: set Mass / bit 1: set TRes (...) / bit 7: silent
}

# Fields whose values are listed only in their own comment ("0 = off / 1 = weak / 2 = strong"):
# (struct, field) -> the IntEnum class they become, as BIT_COMMENTS. Two fields may share a class
# if their comments give the same values. Left out: IS_STA.ServerStatus ("> 1 = fail") and
# IS_NCI.License ("1:S1 ..."), whose comments do not list every value.
VALUE_COMMENTS: dict[tuple[str, str], str] = {
    ("IS_STA", "RaceInProg"): "RACING",  # 0 = no race / 1 = race / 2 = qualifying
    ("IS_STA", "Wind"): "WIND",  # 0 = off / 1 = weak / 2 = strong (IS_RST.Wind has no comment)
    ("IS_SFP", "OffOn"): "OFFON",  # 0 = off / 1 = on
    ("IS_FLG", "OffOn"): "OFFON",
    ("IS_ACR", "Result"): "ACR",  # 1 - processed / 2 - rejected / 3 - unknown command
    ("IS_ISM", "Host"): "ISM",  # 0 = guest / 1 = host
    ("IS_FLG", "Flag"): "FLG",  # 1 = given blue / 2 = causing yellow
    ("IS_HLV", "HLVC"): "HLVC",  # 0: ground / 1: wall / 4: speeding / 5: out of bounds
    ("IS_RIP", "MPR"): "REPLAY",  # 0 = SPR / 1 = MPR
}

# Class docstrings where the comment above the values in the specification does not describe them.
CLASS_DOCS: dict[str, str] = {
    "OCO_INDEX": "Index byte of IS_OCO: which start lights to override",
    "PTYPE": "Kind of player. FEMALE is not reported on a dedicated host",
    "NCNF": "Kind of connection",
    "SCHF": "Keys held with the key of IS_SCH",
    "PLHF": "Flags of PlayerHCap, in IS_PLH: which handicaps to set. SILENT shows no message",
    "RACING": "Whether a race is in progress",
    "WIND": "Wind (also IS_RST.Wind)",
    "OFFON": "Off or on",
    "ACR": "What LFS did with an admin command",
    "ISM": "Whether this computer is the host or a guest",
    "FLG": "Which flag a player is shown",
    "HLVC": "What a player did wrong on a hot lap",
    "REPLAY": "Kind of replay: single player (SPR) or multiplayer (MPR)",
    "OSO": "Parts of OutSimPack2 chosen by OutSim Opts in cfg.txt (hexadecimal; 1ff = all of them)",
}

# Class prefixes whose members keep their full C name (the prefix is not stripped).
KEEP_PREFIX: frozenset[str] = frozenset({"AXO"})

# Member names that would not be valid Python identifiers once the prefix is removed.
MEMBER_NAMES: dict[str, str] = {
    "FLG_GIVEN_BLUE": "BLUE",  # FLG.BLUE: the comment says "1 = given blue"
    "FLG_CAUSING_YELLOW": "YELLOW",
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
