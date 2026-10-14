"""Every note of spec_overrides.NOTES (what was seen in the game) reaches the generated code."""

from pathlib import Path

import pytest
import spec_overrides

PACKETS = Path(__file__).resolve().parent.parent / "src" / "lfs_insim" / "packets"


def generated_text() -> str:
    text = "".join(path.read_text(encoding="utf-8") for path in PACKETS.glob("_*.py"))
    return " ".join(text.replace('"""', " ").split())  # docstrings wrap: compare words only


@pytest.mark.parametrize("key", sorted(spec_overrides.NOTES))
def test_note_is_in_a_docstring(key: str) -> None:
    note = " ".join(spec_overrides.NOTES[key].split())
    assert note in generated_text(), f"the note of {key} is not in the generated packets"


def test_is_aic_warns_that_it_takes_the_car() -> None:
    from lfs_insim.packets import IS_AIC

    assert "takes the car from the AI driver" in " ".join((IS_AIC.__doc__ or "").split())
