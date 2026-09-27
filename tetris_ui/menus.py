"""Menu items and the settings screen rules, without pygame.

The controller keeps only which row is selected; the rows, their labels and values, and
how each setting changes live here, so the controller and the layout share them.
"""

from __future__ import annotations

from dataclasses import replace

from tetris_ui.settings import (
    AUTOREPEAT_SPEEDS,
    LANGUAGES,
    MAX_START_LEVEL,
    Settings,
)

NEW_GAME, HIGH_SCORES, SETTINGS, CONTROLS, QUIT = (
    "New game", "High scores", "Settings", "Controls", "Quit",
)
MAIN_ITEMS = (NEW_GAME, HIGH_SCORES, SETTINGS, CONTROLS, QUIT)
CONTINUE, MAIN_MENU = "Continue", "Main menu"
PAUSE_ITEMS = (CONTINUE, MAIN_MENU)

# Auto-repeat presets: (delay before the first repeat, interval between repeats) in ms.
AUTOREPEAT: dict[str, tuple[int, int]] = {
    "slow": (220, 70),
    "normal": (170, 50),
    "fast": (120, 30),
}

# The settings screen rows in order; a "Back" row follows them.
SETTING_ROWS = (
    "language",
    "music_on",
    "music_volume",
    "sound_on",
    "sfx_volume",
    "start_level",
    "ghost",
    "autorepeat",
)
BACK = "Back"
SETTINGS_ROW_COUNT = len(SETTING_ROWS) + 1  # the setting rows and Back

_LABELS = {
    "language": "Language",
    "music_on": "Music",
    "music_volume": "Music volume",
    "sound_on": "Sound",
    "sfx_volume": "Sound volume",
    "start_level": "Start level",
    "ghost": "Ghost",
    "autorepeat": "Autorepeat",
}
_LANGUAGE_NAMES = {"en": "English", "ru": "Русский"}


def setting_label(row: str) -> str:
    """The name of a settings row as shown on screen, e.g. "Music volume"."""
    return _LABELS[row]


def setting_value(settings: Settings, row: str) -> str:
    """The current value of a settings row as shown on screen, e.g. "50%" or "On"."""
    value = getattr(settings, row)
    if row == "language":
        return _LANGUAGE_NAMES[value]
    if row in ("music_volume", "sfx_volume"):
        return f"{value}%"
    if row == "start_level":
        return str(value)
    if row == "autorepeat":
        return value.capitalize()
    return "On" if value else "Off"


def setting_line(settings: Settings, row: str) -> str:
    """A settings row as one line: "<label>: <value>"."""
    return f"{setting_label(row)}: {setting_value(settings, row)}"


def step_setting(settings: Settings, row: str, steps: int) -> Settings:
    """Settings with one row moved `steps` values forward (negative: back).

    Volumes and the start level stay within their range; switches, the language and
    the auto-repeat speed go round.
    """
    if row == "music_volume":
        return settings.with_volume_step(steps)
    if row == "sfx_volume":
        return settings.with_sfx_volume_step(steps)
    if row == "start_level":
        level = max(0, min(MAX_START_LEVEL, settings.start_level + steps))
        return replace(settings, start_level=level)
    if row == "language":
        return replace(settings, language=_cycle(LANGUAGES, settings.language, steps))
    if row == "autorepeat":
        return replace(settings, autorepeat=_cycle(AUTOREPEAT_SPEEDS, settings.autorepeat, steps))
    value = getattr(settings, row)
    return replace(settings, **{row: value if steps % 2 == 0 else not value})


def _cycle(values: tuple[str, ...], current: str, steps: int) -> str:
    """The value `steps` places after `current` in `values`, going round."""
    return values[(values.index(current) + steps) % len(values)]
