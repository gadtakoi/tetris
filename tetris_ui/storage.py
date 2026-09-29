"""Loading and saving the signed high score table, the installation ID, the settings and the
sound check report in the user's data folder."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from pathlib import Path

from tetris.highscores import HighScores
from tetris_ui import signing
from tetris_ui.cli import warn
from tetris_ui.settings import Settings

# Its own constant, not the exe name: renaming the game must not change where the data is.
APP_DIR_NAME = "tetris_shmetris"
HIGH_SCORES_FILE = "highscores.json"
INSTALL_ID_FILE = "install-id"
SETTINGS_FILE = "settings.json"
SOUND_CHECK_FILE = "sound-check.json"

_INSTALL_ID = re.compile(r"[0-9a-f]{32}")


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


def install_id_path() -> Path:
    """Where the installation ID is kept, next to the high score table it signs."""
    return data_dir() / INSTALL_ID_FILE


def settings_path() -> Path:
    """Where the sound settings are kept, next to the high score table."""
    return data_dir() / SETTINGS_FILE


def sound_check_path() -> Path:
    """Where the sound check report is kept, next to the settings."""
    return data_dir() / SOUND_CHECK_FILE


def load_install_id(path: Path) -> str:
    """The installation ID from the file; if there is none or it is not 32 lowercase hex
    digits, a new random one, written back to the file.

    The new ID is returned even if it could not be written, so the game still starts; a
    table saved with it then only holds for this session.
    """
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        text = ""
    if _INSTALL_ID.fullmatch(text):
        return text
    install_id = secrets.token_hex(16)
    _write_atomic(path, install_id + "\n", "installation ID")
    return install_id


def load(path: Path, install_id: str) -> HighScores:
    """Read the table signed for this installation.

    A missing, unreadable or malformed file gives an empty table silently. A table of
    another format, without a signature or with a signature that does not match (edited
    by hand, or copied from another installation) gives an empty table with a warning.
    The file itself is left as it is until the table is saved again.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return HighScores()
    if not isinstance(data, dict):
        return HighScores()
    records = data.get("entries")
    if data.get("version") != signing.FORMAT_VERSION or not signing.is_valid(
        data.get("sig"), install_id, records
    ):
        warn(f"high scores in {path} failed the integrity check; starting with an empty table")
        return HighScores()
    return HighScores.from_records(records)


def save(scores: HighScores, path: Path, install_id: str) -> bool:
    """Write the table signed for this installation, atomically; report failure instead
    of raising."""
    records = scores.to_records()
    text = json.dumps(
        {
            "version": signing.FORMAT_VERSION,
            "entries": records,
            "sig": signing.signature(install_id, records),
        },
        ensure_ascii=False,
        indent=2,
    )
    return _write_atomic(path, text, "high scores")


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
