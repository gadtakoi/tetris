"""Loading and saving the high score table, the settings and the sound check report in the
user's data folder."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from tetris.highscores import HighScores
from tetris_ui.cli import warn
from tetris_ui.settings import Settings

# Its own constant, not the exe name: renaming the game must not change where the data is.
APP_DIR_NAME = "tetris_shmetris"
HIGH_SCORES_FILE = "highscores.json"
SETTINGS_FILE = "settings.json"
SOUND_CHECK_FILE = "sound-check.json"


def data_dir() -> Path:
    """TETRIS_DATA_DIR if set, else %APPDATA%\\tetris_shmetris, else
    ~/.local/share/tetris_shmetris."""
    override = os.environ.get("TETRIS_DATA_DIR")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def high_scores_path() -> Path:
    """Where the high score table is kept."""
    return data_dir() / HIGH_SCORES_FILE


def settings_path() -> Path:
    """Where the sound settings are kept, next to the high score table."""
    return data_dir() / SETTINGS_FILE


def sound_check_path() -> Path:
    """Where the sound check report is kept, next to the settings."""
    return data_dir() / SOUND_CHECK_FILE


def load(path: Path) -> HighScores:
    """Read the table; a missing or unreadable file gives an empty table."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return HighScores()
    return HighScores.from_json(text)


def save(scores: HighScores, path: Path) -> bool:
    """Write the table atomically; report failure instead of raising."""
    return _write_atomic(path, scores.to_json(), "high scores")


def load_settings(path: Path) -> Settings:
    """Read the sound settings; a missing or unreadable file gives the defaults."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Settings()
    return Settings.from_json(text)


def save_settings(settings: Settings, path: Path) -> bool:
    """Write the sound settings atomically; report failure instead of raising."""
    return _write_atomic(path, settings.to_json(), "settings")


def save_sound_check(text: str, path: Path) -> bool:
    """Write the sound check report atomically; report failure instead of raising."""
    return _write_atomic(path, text, "sound check report")


def _write_atomic(path: Path, text: str, what: str) -> bool:
    """Write text through a temporary file in the same folder, then swap it in.

    An interrupted write never leaves a half-written file behind. Returns False
    (after a warning) if the file could not be written.
    """
    tmp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(text)
        os.replace(tmp_name, path)
        return True
    except OSError as error:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)
        warn(f"could not save {what} to {path}: {error}")
        return False
