"""Plays the synthesized effects and music through pygame.mixer, or nothing."""

from __future__ import annotations

import pygame

from tetris_ui import music, synth
from tetris_ui.input import Controller, Sound

MUSIC_CHANNEL = 0
MIXER_BUFFER = 512


class SilentAudio:
    """Stand-in when no audio device is available: drops every sound."""

    enabled = False

    def sync(self, controller: Controller) -> None:
        """Drop this frame's sound events."""
        controller.drain_sounds()


class Audio:
    """Plays the effects and the music on an open pygame mixer.

    `effects` maps every Sound to its synthesized pygame Sound and `music_sound` is the
    whole melody loop. The music gets a reserved channel of its own, so effects never
    cut it off; its volume follows the controller's music volume.
    """

    enabled = True

    def __init__(self, effects: dict[Sound, pygame.mixer.Sound], music_sound: pygame.mixer.Sound) -> None:
        self._effects = effects
        self._music = music_sound
        pygame.mixer.set_reserved(1)  # effects never steal the music channel
        self._channel = pygame.mixer.Channel(MUSIC_CHANNEL)
        self._volume: float | None = None  # music channel volume last applied
        self._generation: int | None = None  # music generation now loaded on the channel
        self._paused = False

    @classmethod
    def create(cls) -> Audio | SilentAudio:
        """Open the mixer in the synthesizer's format; fall back to silence on failure."""
        pygame.mixer.quit()  # pygame.init() may have opened it in another format
        try:
            pygame.mixer.init(synth.SAMPLE_RATE, -16, 1, MIXER_BUFFER)
        except pygame.error:
            return SilentAudio()
        effects = {
            sound: pygame.mixer.Sound(buffer=synth.to_bytes(synth.EFFECTS[sound.value]()))
            for sound in Sound
        }
        music_sound = pygame.mixer.Sound(buffer=synth.to_bytes(music.render_music()))
        return cls(effects, music_sound)

    @property
    def music_busy(self) -> bool:
        """Whether music is playing right now (started and not paused)."""
        return self._generation is not None and not self._paused

    def sync(self, controller: Controller) -> None:
        """Play this frame's effects and bring the music in line with the controller."""
        sounds = controller.drain_sounds()
        if controller.sound_on:
            for sound in sounds:
                self._effects[sound].play()
        volume = controller.music_volume / 100
        if volume != self._volume:  # applies at once, even to music already playing
            self._channel.set_volume(volume)
            self._volume = volume
        state, generation = controller.music_state, controller.music_generation
        if state == "stopped":
            if self._generation is not None:
                self._channel.stop()
                self._generation = None
                self._paused = False
        elif state == "playing":
            if self._generation != generation:
                self._channel.play(self._music, loops=-1)
                self._generation = generation
                self._paused = False
            elif self._paused:
                self._channel.unpause()
                self._paused = False
        elif self._generation == generation and not self._paused:  # "paused"
            self._channel.pause()
            self._paused = True
