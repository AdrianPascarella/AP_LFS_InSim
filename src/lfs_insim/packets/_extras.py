"""Hand-written additions to generated packets.

scripts/generate_packets.py adds each class here as a base of the packet that EXTRAS in
scripts/spec_overrides.py names. They hold properties only, never fields: the fields and the
binary layout come from the specification.
"""

from __future__ import annotations


class MSOText:
    """For IS_MSO: the text that the user typed."""

    Msg: str
    TextStart: int

    @property
    def text(self) -> str:
        """What the user typed, without the "Name : " that LFS puts before it.

        For a system message (UserType 0) it is the whole message. LFS's ^ codes (colours...)
        are kept, as in Msg: `lfs_insim.text.strip_colours()` removes the colours.
        """
        return self.Msg[self.TextStart :]
