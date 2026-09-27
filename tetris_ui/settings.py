"""Sound settings that survive restarts: music and effects switches, music volume."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

VOLUME_STEP = 10
MIN_VOLUME = 0
MAX_VOLUME = 100
DEFAULT_VOLUME = 50
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


@dataclass(frozen=True)
class Settings:
    """What the player chose for sound; the defaults apply on first launch.

    music_volume is a percentage from 0 to 100 in steps of VOLUME_STEP.
    """

    music_on: bool = True
    sound_on: bool = True
    music_volume: int = DEFAULT_VOLUME

    def with_volume_step(self, steps: int) -> Settings:
        """Settings with the music volume moved by `steps` steps, kept within 0..100."""
        volume = self.music_volume + steps * VOLUME_STEP
        return replace(self, music_volume=max(MIN_VOLUME, min(MAX_VOLUME, volume)))

    def to_json(self) -> str:
        """The settings as the JSON text stored in settings.json."""
        return json.dumps(
            {
                "version": FORMAT_VERSION,
                "music_on": self.music_on,
                "sound_on": self.sound_on,
                "music_volume": self.music_volume,
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
        return cls(
            music_on=music_on if _is_bool(music_on) else defaults.music_on,
            sound_on=sound_on if _is_bool(sound_on) else defaults.sound_on,
            music_volume=volume if _is_volume(volume) else defaults.music_volume,
        )
