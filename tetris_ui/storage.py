"""Loading and saving the high score table in the user's data folder."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from tetris.highscores import HighScores

APP_DIR_NAME = "tetris"
HIGH_SCORES_FILE = "highscores.json"


def data_dir() -> Path:
    """TETRIS_DATA_DIR if set, else %APPDATA%\\tetris, else ~/.local/share/tetris."""
    override = os.environ.get("TETRIS_DATA_DIR")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def high_scores_path() -> Path:
    return data_dir() / HIGH_SCORES_FILE


def load(path: Path) -> HighScores:
    """Read the table; a missing or unreadable file gives an empty table."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return HighScores()
    return HighScores.from_json(text)


def save(scores: HighScores, path: Path) -> bool:
    """Write the table atomically; report failure instead of raising."""
    tmp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(scores.to_json())
        os.replace(tmp_name, path)
        return True
    except OSError as error:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)
        if sys.stderr is not None:
            print(f"tetris: could not save high scores to {path}: {error}", file=sys.stderr)
        return False
