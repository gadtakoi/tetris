import subprocess
import sys
from pathlib import Path

import pytest

import release_notes
from tetris_ui import __version__

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHANGELOG = """# Журнал изменений

Шапка.

## [Не выпущено]

### Добавлено
- Будущее.

## [2.0.0] — 2026-09-29

### Изменено
- Второе.

## [1.0.0] — 2026-09-27

### Добавлено
- Первое.
"""


def test_section_between_headings():
    assert release_notes.changelog_section(CHANGELOG, "2.0.0") == "### Изменено\n- Второе."


def test_last_section():
    assert release_notes.changelog_section(CHANGELOG, "1.0.0") == "### Добавлено\n- Первое."


def test_missing_or_empty_section():
    assert release_notes.changelog_section(CHANGELOG, "1.0") is None
    assert release_notes.changelog_section("## [1.0.0] — 2026-09-27\n\n", "1.0.0") is None
    assert release_notes.changelog_section("## [1.0.0]", "1.0.0") is None


def test_tag_must_match_the_version(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(f"## [{__version__}] — 2026-09-29\n\n- Новое.\n", encoding="utf-8")
    assert release_notes.release_notes(f"v{__version__}", changelog) == "- Новое.\n"
    with pytest.raises(ValueError, match="does not match"):
        release_notes.release_notes(__version__, changelog)  # without "v"
    with pytest.raises(ValueError, match="does not match"):
        release_notes.release_notes("v0.0.1", changelog)


def test_changelog_without_the_version(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [0.0.1] — 2026-09-29\n\n- Старое.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no section"):
        release_notes.release_notes(f"v{__version__}", changelog)


def test_current_version_has_release_notes():
    notes = release_notes.release_notes(f"v{__version__}")
    assert notes.strip() and not notes.startswith("## ")


def test_command_line():
    result = subprocess.run(
        [sys.executable, "release_notes.py", f"v{__version__}"],
        cwd=PROJECT_ROOT, capture_output=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == release_notes.release_notes(f"v{__version__}")
    wrong = subprocess.run(
        [sys.executable, "release_notes.py", "v0.0.0"],
        cwd=PROJECT_ROOT, capture_output=True, encoding="utf-8",
    )
    assert wrong.returncode == 1 and "does not match" in wrong.stderr
