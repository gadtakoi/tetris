import subprocess
import sys
from pathlib import Path

import pytest

from tetris_ui import menus
from tetris_ui.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_menu_items():
    assert menus.MAIN_ITEMS == ("New game", "High scores", "Settings", "Controls", "Quit")
    assert menus.PAUSE_ITEMS == ("Continue", "Main menu")


def test_default_setting_lines():
    lines = [menus.setting_line(Settings(), row) for row in menus.SETTING_ROWS]
    assert lines == [
        "Language: English",
        "Music: On",
        "Music volume: 50%",
        "Sound: On",
        "Sound volume: 100%",
        "Start level: 0",
        "Ghost: On",
        "Autorepeat: Normal",
    ]
    assert menus.SETTINGS_ROW_COUNT == 9


def test_autorepeat_presets():
    assert menus.AUTOREPEAT == {"slow": (220, 70), "normal": (170, 50), "fast": (120, 30)}


@pytest.mark.parametrize(("row", "start", "steps", "expected"), [
    ("music_volume", 50, 1, 60),
    ("music_volume", 100, 1, 100),
    ("music_volume", 0, -1, 0),
    ("sfx_volume", 100, -1, 90),
    ("sfx_volume", 100, 1, 100),
    ("sfx_volume", 0, -1, 0),
    ("start_level", 0, 2, 2),
    ("start_level", 19, 1, 19),
    ("start_level", 0, -1, 0),
])
def test_ranged_settings_stop_at_the_ends(row, start, steps, expected):
    settings = Settings(**{row: start})
    assert getattr(menus.step_setting(settings, row, steps), row) == expected


@pytest.mark.parametrize(("row", "start", "steps", "expected"), [
    ("language", "en", 1, "ru"),
    ("language", "ru", 1, "en"),
    ("language", "en", -1, "ru"),
    ("autorepeat", "fast", 1, "slow"),
    ("autorepeat", "slow", -1, "fast"),
    ("autorepeat", "normal", 1, "fast"),
    ("music_on", True, 1, False),
    ("music_on", False, -1, True),
    ("sound_on", True, -1, False),
    ("ghost", True, 1, False),
    ("ghost", False, 1, True),
])
def test_other_settings_go_round(row, start, steps, expected):
    settings = Settings(**{row: start})
    assert getattr(menus.step_setting(settings, row, steps), row) == expected


def test_step_changes_only_its_row():
    changed = menus.step_setting(Settings(), "start_level", 1)
    assert changed == Settings(start_level=1)


@pytest.mark.parametrize(("settings", "row", "value"), [
    (Settings(language="ru"), "language", "Русский"),
    (Settings(music_on=False), "music_on", "Off"),
    (Settings(sfx_volume=30), "sfx_volume", "30%"),
    (Settings(start_level=12), "start_level", "12"),
    (Settings(ghost=False), "ghost", "Off"),
    (Settings(autorepeat="slow"), "autorepeat", "Slow"),
])
def test_setting_values(settings, row, value):
    assert menus.setting_value(settings, row) == value


def test_menus_module_does_not_import_pygame():
    code = "import sys, tetris_ui.menus; assert 'pygame' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
