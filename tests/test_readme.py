"""The README's first program is examples/hello.py, which test_examples.py runs (fake LFS)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_example_is_hello_py() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```python\n(.*?)```", readme, re.DOTALL)
    assert block is not None
    hello = (ROOT / "examples" / "hello.py").read_text(encoding="utf-8")
    code = hello.split('"""', 2)[2].lstrip("\n")  # without the module docstring
    assert block.group(1).strip() == code.strip()
