"""Every note of spec_overrides.NOTES (what was seen in the game) reaches the docstrings."""

import pytest
import spec_overrides

from lfs_insim import packets


def words(text: str | None) -> str:
    return " ".join((text or "").split())  # docstrings wrap: compare words only


def docstring_of(key: str) -> str:
    """The docstring a note goes to: a packet ("IS_AIC") or an enum member ("SMALL.SSP")."""
    if "." not in key:
        return words(getattr(packets, key).__doc__)
    enum_name, member = key.split(".")
    source = packets._enums.__file__
    with open(source, encoding="utf-8") as file:
        text = file.read()
    start = text.index(f"\nclass {enum_name}(")
    start = text.index(f"\n    {member} = ", start)
    end = text.find("\n\n", text.index('"""', start) + 3)
    return words(text[start:end].replace('\\"', '"'))


@pytest.mark.parametrize("key", sorted(spec_overrides.NOTES))
def test_note_is_in_its_docstring(key: str) -> None:
    assert words(spec_overrides.NOTES[key]) in docstring_of(key)


def test_is_aic_warns_that_it_disables_the_ai() -> None:
    assert "disables the AI driver completely" in words(packets.IS_AIC.__doc__)
