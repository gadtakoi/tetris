"""Print the CHANGELOG.md section of a release tag, for the text of a GitHub release.

The GitHub release workflow (.github/workflows/release.yml) runs it before building: the tag
must be "v" + tetris_ui.__version__, and CHANGELOG.md must have a section for that version.
Otherwise the script exits with a non-zero code and the release is not made.

Usage:
    python release_notes.py v3.0.0 > notes.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from tetris_ui import __version__  # no pygame: the package imports nothing

PROJECT_ROOT = Path(__file__).resolve().parent
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"
# A section heading of CHANGELOG.md: "## [3.0.0] — 2026-09-29" or "## [Не выпущено]".
SECTION = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)


def changelog_section(text: str, version: str) -> str | None:
    """The body of the section of version in a changelog, without its heading and blank
    lines around it; None if there is no such section or it is empty."""
    headings = list(SECTION.finditer(text))
    for index, heading in enumerate(headings):
        if heading.group(1) == version:
            line_end = text.find("\n", heading.end())
            start = len(text) if line_end == -1 else line_end + 1
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            return body or None
    return None


def release_notes(tag: str, changelog: Path = CHANGELOG) -> str:
    """The release text for tag; ValueError if the tag is not "v" + __version__ or the
    changelog has no section for it."""
    if tag != f"v{__version__}":
        raise ValueError(f"tag {tag} does not match the game's version v{__version__}")
    section = changelog_section(changelog.read_text(encoding="utf-8"), __version__)
    if section is None:
        raise ValueError(f"{changelog.name} has no section [{__version__}]")
    return section + "\n"


def main(argv: list[str] | None = None) -> int:
    """Print the release text for the tag in argv; return 0, or 1 with a message on error."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python release_notes.py v<version>", file=sys.stderr)
        return 1
    try:
        notes = release_notes(args[0])
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
