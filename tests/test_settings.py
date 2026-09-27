import json
import subprocess
import sys
from pathlib import Path

import pytest

from tetris_ui.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def settings_json(**fields) -> str:
    data = {"version": 1, "music_on": True, "sound_on": True, "music_volume": 50}
    data.update(fields)
    return json.dumps(data)


def test_defaults():
    assert Settings() == Settings(music_on=True, sound_on=True, music_volume=50)


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
