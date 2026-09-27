"""Settings that survive restarts: sound, language, start level, ghost and auto-repeat."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

VOLUME_STEP = 10
MIN_VOLUME = 0
MAX_VOLUME = 100
DEFAULT_VOLUME = 50
DEFAULT_SFX_VOLUME = 100
LANGUAGES = ("en", "ru")
MAX_START_LEVEL = 19
AUTOREPEAT_SPEEDS = ("slow", "normal", "fast")
FORMAT_VERSION = 1


def _is_bool(value: object) -> bool:
    """Whether value is a real bool (JSON true or false, not 0 or 1)."""
    return type(value) is bool


def _is_volume(value: object) -> bool:
    """Whether value is a valid volume: an int from 0 to 100 in steps of VOLUME_STEP."""
    return (
        type(value) is int
        and MIN_VOLUME <= value <= MAX_VOLUME
        and value % VOLUME_STEP == 0
    )


def _is_start_level(value: object) -> bool:
    """Whether value is a valid start level: an int from 0 to MAX_START_LEVEL."""
    return type(value) is int and 0 <= value <= MAX_START_LEVEL


def _step_volume(volume: int, steps: int) -> int:
    """A volume moved by `steps` steps of VOLUME_STEP, kept within MIN_VOLUME..MAX_VOLUME."""
    return max(MIN_VOLUME, min(MAX_VOLUME, volume + steps * VOLUME_STEP))


@dataclass(frozen=True)
class Settings:
    """What the player chose; the defaults apply on first launch.

    music_volume and sfx_volume are percentages from 0 to 100 in steps of VOLUME_STEP.
    language is one of LANGUAGES, start_level is 0..MAX_START_LEVEL, ghost switches the
    drop shadow, and autorepeat is one of AUTOREPEAT_SPEEDS.
    """

    music_on: bool = True
    sound_on: bool = True
    music_volume: int = DEFAULT_VOLUME
    sfx_volume: int = DEFAULT_SFX_VOLUME
    language: str = "en"
    start_level: int = 0
    ghost: bool = True
    autorepeat: str = "normal"

    def with_volume_step(self, steps: int) -> Settings:
        """Settings with the music volume moved by `steps` steps, kept within 0..100."""
        return replace(self, music_volume=_step_volume(self.music_volume, steps))

    def with_sfx_volume_step(self, steps: int) -> Settings:
        """Settings with the effects volume moved by `steps` steps, kept within 0..100."""
        return replace(self, sfx_volume=_step_volume(self.sfx_volume, steps))

    def to_json(self) -> str:
        """The settings as the JSON text stored in settings.json."""
        return json.dumps(
            {
                "version": FORMAT_VERSION,
                "music_on": self.music_on,
                "sound_on": self.sound_on,
                "music_volume": self.music_volume,
                "sfx_volume": self.sfx_volume,
                "language": self.language,
                "start_level": self.start_level,
                "ghost": self.ghost,
                "autorepeat": self.autorepeat,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> Settings:
        """Parse saved settings; each invalid field falls back to its default.

        Text that is not a JSON object of the current version gives the defaults.
        Never raises.
        """
        try:
            data = json.loads(text)
        except ValueError:
            return cls()
        if not isinstance(data, dict) or data.get("version") != FORMAT_VERSION:
            return cls()
        defaults = cls()
        music_on = data.get("music_on")
        sound_on = data.get("sound_on")
        volume = data.get("music_volume")
        sfx_volume = data.get("sfx_volume")
        language = data.get("language")
        start_level = data.get("start_level")
        ghost = data.get("ghost")
        autorepeat = data.get("autorepeat")
        return cls(
            music_on=music_on if _is_bool(music_on) else defaults.music_on,
            sound_on=sound_on if _is_bool(sound_on) else defaults.sound_on,
            music_volume=volume if _is_volume(volume) else defaults.music_volume,
            sfx_volume=sfx_volume if _is_volume(sfx_volume) else defaults.sfx_volume,
            language=language if language in LANGUAGES else defaults.language,
            start_level=start_level if _is_start_level(start_level) else defaults.start_level,
            ghost=ghost if _is_bool(ghost) else defaults.ghost,
            autorepeat=autorepeat if autorepeat in AUTOREPEAT_SPEEDS else defaults.autorepeat,
        )
