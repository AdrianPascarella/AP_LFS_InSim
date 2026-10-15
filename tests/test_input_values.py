"""Values of AIInputVal.Value named from the comments of IS_AIC (W12): CS.INDICATORS takes
INDICATORS.LEFT, the inputs marked 'toggle' take TOGGLE.ON, CS.GEAR takes GEAR.FIRST."""

import pytest
import spec_overrides
import spec_parser
from generate_enums import collect_enums, value_members
from spec_parser import SpecError
from test_notes import docstring_of

from lfs_insim.packets import (
    CS,
    GEAR,
    HEADLIGHTS,
    INDICATORS,
    IS_AIC,
    LOOK,
    SIREN,
    STEER,
    TOGGLE,
    AIInputVal,
    unpack_insim,
)


def test_the_classes() -> None:
    assert [(m.name, int(m)) for m in STEER] == [
        ("HARD_LEFT", 1),
        ("CENTRE", 32768),
        ("HARD_RIGHT", 65535),
    ]
    assert [m.name for m in HEADLIGHTS] == ["OFF", "SIDE", "LOW", "HIGH"] and int(
        HEADLIGHTS.OFF
    ) == 1
    assert [m.name for m in SIREN] == ["FAST", "SLOW"]
    assert [m.name for m in INDICATORS] == ["CANCEL", "LEFT", "RIGHT", "HAZARD"]
    assert [(m.name, int(m)) for m in LOOK] == [
        ("NONE", 0),
        ("LEFT", 4),
        ("FAR_LEFT", 5),  # "5: left+"
        ("RIGHT", 6),
        ("FAR_RIGHT", 7),
    ]
    assert [(m.name, int(m)) for m in TOGGLE] == [("TOGGLE", 1), ("OFF", 2), ("ON", 3)]
    assert (GEAR.REVERSE, GEAR.NEUTRAL, GEAR.FIRST, GEAR.SEQUENTIAL) == (0, 1, 2, 255)
    assert GEAR.FIRST + 2 == GEAR.THIRD


def test_each_input_names_the_class_of_its_values() -> None:
    def doc(member: str) -> str:
        return docstring_of(f"CS.{member}")

    assert "Values: INDICATORS" in doc("INDICATORS")
    for toggle in ("IGNITION", "EXTRALIGHT", "PITSPEED", "TCDISABLE", "FOGREAR", "FOGFRONT"):
        assert "Values: TOGGLE" in doc(toggle)
    assert "Values: GEAR" in doc("GEAR")
    assert "Values:" not in doc("THROTTLE")


def test_an_ai_control_packet_with_them() -> None:
    inputs = [
        AIInputVal(Input=CS.MSX, Value=STEER.CENTRE),
        AIInputVal(Input=CS.INDICATORS, Value=INDICATORS.HAZARD),
        AIInputVal(Input=CS.IGNITION, Value=TOGGLE.ON),
        AIInputVal(Input=CS.GEAR, Value=GEAR.FIRST),
    ]
    packet = unpack_insim(IS_AIC(PLID=2, Inputs=inputs).pack())
    assert isinstance(packet, IS_AIC)
    assert [(i.Input, i.Value) for i in packet.Inputs] == [
        (0, 32768),
        (13, 4),
        (5, 3),
        (14, 2),
    ]


def test_values_without_a_separator_or_with_a_plus() -> None:
    def read(comment: str) -> list[tuple[str, int]]:
        return [(m.name, m.value) for m in value_members("X", comment, 1)]

    assert read("1 hard left / 65535 hard right") == [("X_HARD_LEFT", 1), ("X_HARD_RIGHT", 65535)]
    assert read("4: left / 5: left+") == [("X_LEFT", 4), ("X_LEFT+", 5)]


SPEC = """
struct AIInputVal // There is an array of these in the AIC packet below
{
	byte	Input;		// Select input value to set
	byte	Time;		// Time to hold (optional, hundredths of a second)
	word	Value;		// Value to set
};

// CS_MSX			 0 - steer: 1 hard left / 32768 centre / 65535 hard right
// CS_IGNITION		 5 - toggle
// CS_SIREN			 8 - %s
// CS_GEAR			14 - for shifter (leave at 255 for sequential control)

// Inputs marked 'toggle' accept the following Values:
// 1 toggle
// 2 switch off
// 3 switch on

// Special values for Input

#define CS_STOP_CONTROL		255
"""


TOGGLE_LINE = "Inputs marked 'toggle' accept the following Values:"


@pytest.fixture(autouse=True)
def only_these_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The inputs of SPEC, for the tests that read it; the others use the generated code."""
    listed = {"CS_MSX": "STEER", "CS_SIREN": "SIREN", TOGGLE_LINE: "TOGGLE"}
    monkeypatch.setattr(spec_overrides, "LISTED_VALUES", listed)


def classes(siren: str) -> dict[str, list[tuple[str, int]]]:
    spec = spec_parser.parse(SPEC % siren, "x")
    return {c.name: [(m.name, m.value) for m in c.members] for c in collect_enums(spec)}


def test_read_from_the_specification() -> None:
    found = classes("hold siren - 1:fast / 2:slow")
    assert found["SIREN"] == [("SIREN_FAST", 1), ("SIREN_SLOW", 2)]
    assert found["TOGGLE"] == [
        ("TOGGLE_TOGGLE", 1),
        ("TOGGLE_SWITCH_OFF", 2),
        ("TOGGLE_SWITCH_ON", 3),
    ]
    assert found["GEAR"][-1] == ("GEAR_SEQUENTIAL", 255)


def test_a_comment_that_changed_stops_the_generation() -> None:
    with pytest.raises(SpecError, match="VALUE_COMMENTS"):
        classes("hold siren - fast or slow")


@pytest.mark.parametrize("key", ["CS_GONE", "Inputs marked 'gone' accept the following Values:"])
def test_an_input_or_paragraph_that_is_gone_stops_the_generation(
    monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    monkeypatch.setitem(spec_overrides.LISTED_VALUES, key, "GONE")
    with pytest.raises(SpecError, match="LISTED_VALUES"):
        classes("hold siren - 1:fast / 2:slow")


def test_the_toggle_inputs_are_found_by_their_comment() -> None:
    spec = spec_parser.parse(SPEC % "hold siren - 1:fast / 2:slow", "x")
    cs = next(c for c in collect_enums(spec) if c.name == "CS")
    docs = {m.name: m.comment for m in cs.members}
    assert docs["CS_IGNITION"] == "toggle. Values: TOGGLE"
    assert docs["CS_GEAR"].endswith("Values: GEAR") and "Values" not in docs["CS_STOP_CONTROL"]
