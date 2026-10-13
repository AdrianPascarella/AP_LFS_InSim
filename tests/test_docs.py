"""The public docs (README.md and docs/*.md): their code is valid, their links are not broken."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAGES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


def ids(pages: list[Path]) -> list[str]:
    return [page.relative_to(ROOT).as_posix() for page in pages]


def anchor(heading: str) -> str:
    """The GitHub anchor of a heading: lower case, spaces to hyphens, punctuation removed."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


@pytest.mark.parametrize("page", PAGES, ids=ids(PAGES))
def test_code_blocks_are_python_and_import_what_exists(page: Path) -> None:
    for code in re.findall(r"```python\n(.*?)```", page.read_text(encoding="utf-8"), re.DOTALL):
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, ast.Import | ast.ImportFrom):
                exec(compile(ast.Module([node], []), str(page), "exec"), {})


@pytest.mark.parametrize("page", PAGES, ids=ids(PAGES))
def test_relative_links_point_somewhere(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if target.startswith(("http://", "https://", "#")):
            continue
        path, _, fragment = target.partition("#")
        destination = (page.parent / path).resolve()
        assert destination.exists(), f"{page.name}: {target} does not exist"
        if fragment and destination.suffix == ".md":
            headings = re.findall(r"^#+ (.*)$", destination.read_text(encoding="utf-8"), re.M)
            assert fragment in [anchor(h) for h in headings], f"{page.name}: no #{fragment}"
