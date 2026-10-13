"""lfs_insim.testing (W10.9): the example in docs/testing.md runs and passes."""

import re
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "docs" / "testing.md"


def test_the_documented_example_passes() -> None:
    code = re.findall(r"```python\n(.*?)```", PAGE.read_text("utf-8"), re.DOTALL)[0]
    namespace: dict[str, object] = {}
    exec(compile(code, str(PAGE), "exec"), namespace)
    test = namespace["test_hello_is_answered"]
    assert callable(test)
    test()


def test_misuse_is_an_error_not_an_assert() -> None:
    import pytest

    from lfs_insim.testing import FakeLFS

    with pytest.raises(RuntimeError, match="never been started"):
        _ = FakeLFS().port
