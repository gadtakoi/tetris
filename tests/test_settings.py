import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tetris_ui.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def settings_json(**fields) -> str:
    data = {"version": 1, "music_on": True, "sound_on": True, "music_volume": 50}
    data.update(fields)
    return json.dumps(data)


def test_defaults():
    assert Settings() == Settings(music_on=True, sound_on=True, music_volume=50, sfx_volume=100)


def test_volume_steps_and_bounds():
    assert Settings().with_volume_step(1).music_volume == 60
    assert Settings().with_volume_step(-1).music_volume == 40
    assert Settings(music_volume=100).with_volume_step(1).music_volume == 100
    assert Settings(music_volume=0).with_volume_step(-1).music_volume == 0


def test_json_round_trip():
    settings = Settings(music_on=False, sound_on=True, music_volume=70)
    assert Settings.from_json(settings.to_json()) == settings


@pytest.mark.parametrize("text", [
    "not json",
    json.dumps([1, 2, 3]),
    settings_json(version=2, music_on=False),
    json.dumps({"music_on": False}),
])
def test_unreadable_text_gives_defaults(text):
    assert Settings.from_json(text) == Settings()


def test_invalid_field_is_replaced_alone():
    text = settings_json(music_on=False, sound_on=True, music_volume=55)
    assert Settings.from_json(text) == Settings(music_on=False, sound_on=True, music_volume=50)


@pytest.mark.parametrize("volume", ["abc", -10, 110, True, 50.0, None])
def test_invalid_volume_falls_back(volume):
    loaded = Settings.from_json(settings_json(music_on=False, music_volume=volume))
    assert loaded == Settings(music_on=False, music_volume=50)


@pytest.mark.parametrize("flag", [1, 0, "true", None])
def test_invalid_switch_falls_back(flag):
    loaded = Settings.from_json(settings_json(sound_on=flag, music_volume=30))
    assert loaded == Settings(sound_on=True, music_volume=30)


def test_settings_module_does_not_import_pygame():
    code = "import sys, tetris_ui.settings; assert 'pygame' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


# --- Effects volume --------------------------------------------------------


def test_effects_volume_steps_and_bounds():
    assert Settings().with_sfx_volume_step(-1).sfx_volume == 90
    assert Settings().with_sfx_volume_step(1).sfx_volume == 100
    assert Settings(sfx_volume=0).with_sfx_volume_step(-1).sfx_volume == 0
    assert Settings().with_sfx_volume_step(-1).music_volume == 50  # music untouched


def test_file_without_effects_volume_gives_100():
    text = settings_json(music_on=False, music_volume=55)  # no sfx_volume at all
    assert Settings.from_json(text) == Settings(music_on=False, music_volume=50, sfx_volume=100)


@pytest.mark.parametrize("volume", ["abc", -10, 110, 55, True])
def test_invalid_effects_volume_falls_back_alone(volume):
    loaded = Settings.from_json(settings_json(music_volume=30, sfx_volume=volume))
    assert loaded == Settings(music_volume=30, sfx_volume=100)


def test_effects_volume_round_trip():
    settings = Settings(sfx_volume=40)
    assert Settings.from_json(settings.to_json()) == settings


def test_unknown_fields_are_ignored():
    text = settings_json(sfx_volume=70, language="ru")
    assert Settings.from_json(text).sfx_volume == 70


# --- Game settings ---------------------------------------------------------


def test_game_settings_defaults():
    settings = Settings()
    assert (settings.language, settings.start_level, settings.ghost, settings.autorepeat) == (
        "en", 0, True, "normal")


def test_game_settings_round_trip():
    settings = Settings(language="ru", start_level=5, ghost=False, autorepeat="fast")
    assert Settings.from_json(settings.to_json()) == settings


def test_file_without_game_settings():
    text = settings_json(music_on=False, music_volume=30, sfx_volume=70)
    assert Settings.from_json(text) == Settings(music_on=False, music_volume=30, sfx_volume=70)


@pytest.mark.parametrize(("field", "value"), [
    ("start_level", 25), ("start_level", -1), ("start_level", True), ("start_level", 5.0),
    ("language", "de"), ("language", None),
    ("ghost", 0), ("ghost", "false"),
    ("autorepeat", "turbo"), ("autorepeat", 1),
])
def test_invalid_game_field_falls_back_alone(field, value):
    good = {"language": "ru", "start_level": 7, "ghost": False, "autorepeat": "slow"}
    loaded = Settings.from_json(settings_json(music_volume=30, **{**good, field: value}))
    expected = {**good, field: getattr(Settings(), field)}
    assert loaded == Settings(music_volume=30, **expected)


def test_saving_one_group_keeps_the_other():
    sound_changed = Settings(start_level=5, ghost=False).with_volume_step(-2)
    game_changed = replace(Settings(music_on=False, sfx_volume=40), autorepeat="slow")
    for settings in (sound_changed, game_changed):
        assert Settings.from_json(settings.to_json()) == settings
