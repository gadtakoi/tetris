"""Relative links in docs/ point to files and folders that exist."""

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parent.parent / "docs"
DOC_FILES = sorted(DOCS.glob("*.md"))
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def relative_links(path: Path) -> list[str]:
    """Link targets in a Markdown file, without web links and in-page anchors."""
    targets = LINK.findall(path.read_text(encoding="utf-8"))
    return [
        target.split("#", 1)[0]
        for target in targets
        if not target.startswith(("http://", "https://", "mailto:", "#"))
    ]


def test_docs_exist():
    names = {path.name for path in DOC_FILES}
    assert {"README.md", "architecture.md", "game-logic.md", "interface.md", "build.md",
            "user-guide.md"} <= names


@pytest.mark.parametrize("doc", DOC_FILES, ids=lambda path: path.name)
def test_relative_links_resolve(doc):
    links = relative_links(doc)
    assert links, f"{doc.name} links to nothing"
    broken = [link for link in links if not (doc.parent / link).exists()]
    assert not broken, f"{doc.name}: broken links {broken}"
