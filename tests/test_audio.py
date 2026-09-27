import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest

pygame = pytest.importorskip("pygame")

from tests.helpers import ScriptedRng  # noqa: E402
from tetris.game import Game  # noqa: E402
from tetris.pieces import PieceType  # noqa: E402
from tetris_ui import app, music, synth  # noqa: E402
from tetris_ui.audio import MIXER_BUFFER, Audio, SilentAudio  # noqa: E402
from tetris_ui.input import Controller, Key, Sound  # noqa: E402
from tetris_ui.settings import Settings  # noqa: E402


@pytest.fixture(scope="module")
def pcm():
    """Synthesize every sound once for the module; synthesis takes most of a second."""
    effects = {sound: synth.to_bytes(synth.EFFECTS[sound.value]()) for sound in Sound}
    return effects, synth.to_bytes(music.render_music())


@pytest.fixture
def audio(pcm):
    """A fresh mixer and Audio for each test.

    Some tests shut pygame down (pygame.quit), which invalidates every Sound, so
    sharing one Audio across tests would crash whichever test runs after them.
    """
    pygame.init()
    pygame.mixer.quit()
    pygame.mixer.init(synth.SAMPLE_RATE, -16, 1, MIXER_BUFFER)
    effects, music_pcm = pcm
    yield Audio(
        {sound: pygame.mixer.Sound(buffer=data) for sound, data in effects.items()},
        pygame.mixer.Sound(buffer=music_pcm),
    )
    pygame.quit()


class RecordingSound:
    def __init__(self) -> None:
        self.plays = 0

    def play(self) -> None:
        self.plays += 1


def controller_with(*pieces: PieceType) -> Controller:
    return Controller(Game(rng=ScriptedRng(pieces)))


def test_audio_opens_on_dummy_driver():
    pygame.init()
    try:
        created = Audio.create()
        assert isinstance(created, Audio)
        assert pygame.mixer.get_init()[:2] == (22050, -16)
    finally:
        pygame.quit()


def test_effects_play_only_when_sound_is_on(audio, monkeypatch):
    recorders = {sound: RecordingSound() for sound in Sound}
    monkeypatch.setattr(audio, "_effects", recorders)
    controller = controller_with(PieceType.T, PieceType.T)
    controller.key_down(Key.LEFT)
    audio.sync(controller)
    assert recorders[Sound.MOVE].plays == 1
    controller.key_down(Key.TOGGLE_SOUND)
    controller.key_down(Key.LEFT)
    audio.sync(controller)
    assert recorders[Sound.MOVE].plays == 1
    assert controller.drain_sounds() == []  # drained even when silent


def test_music_follows_play_pause_and_game_over(audio):
    controller = controller_with(PieceType.O)
    audio.sync(controller)
    assert audio.music_busy
    controller.key_down(Key.PAUSE)
    audio.sync(controller)
    assert not audio.music_busy
    controller.key_down(Key.PAUSE)
    audio.sync(controller)
    assert audio.music_busy
    while not controller.game.is_over:
        controller.key_down(Key.HARD_DROP)
    audio.sync(controller)
    assert not audio.music_busy


def test_music_toggle_stops_and_restarts(audio):
    channel = pygame.mixer.Channel(0)
    controller = controller_with(PieceType.O)
    audio.sync(controller)
    assert audio.music_busy and channel.get_busy()
    controller.key_down(Key.TOGGLE_MUSIC)
    audio.sync(controller)
    assert not audio.music_busy and not channel.get_busy()
    controller.key_down(Key.TOGGLE_MUSIC)
    audio.sync(controller)
    assert audio.music_busy and channel.get_busy()


def test_music_channel_is_free_after_game_over(audio):
    channel = pygame.mixer.Channel(0)
    controller = controller_with(PieceType.O)
    audio.sync(controller)
    assert channel.get_busy()
    while not controller.game.is_over:
        controller.key_down(Key.HARD_DROP)
    audio.sync(controller)
    assert not channel.get_busy()


def test_mixer_failure_gives_silent_audio(monkeypatch):
    def broken_init(*args, **kwargs):
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "init", broken_init)
    pygame.init()
    try:
        silent = Audio.create()
        assert isinstance(silent, SilentAudio)
        controller = controller_with(PieceType.T, PieceType.T)
        controller.key_down(Key.LEFT)
        silent.sync(controller)
        assert controller.drain_sounds() == []
        controller.key_down(Key.TOGGLE_MUSIC)
        assert not controller.music_on
    finally:
        pygame.quit()


def test_main_runs_without_audio_device(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))

    def broken_init(*args, **kwargs):
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "init", broken_init)
    assert app.main(max_frames=3) == 0


# --- Music volume ----------------------------------------------------------

MIXER_STEP = 1 / 128  # SDL keeps channel volume in 128 steps


def test_default_music_volume(audio):
    controller = controller_with(PieceType.O)
    audio.sync(controller)
    assert pygame.mixer.Channel(0).get_volume() == pytest.approx(0.5, abs=MIXER_STEP)


def test_volume_change_applies_to_playing_music(audio):
    channel = pygame.mixer.Channel(0)
    controller = controller_with(PieceType.O)
    audio.sync(controller)
    generation = controller.music_generation
    controller.key_down(Key.VOLUME_UP)
    controller.key_down(Key.VOLUME_UP)
    audio.sync(controller)
    assert channel.get_volume() == pytest.approx(0.7, abs=MIXER_STEP)
    assert channel.get_busy() and audio.music_busy
    assert controller.music_generation == generation  # the melody was not restarted


def test_zero_volume_is_silent_music():
    controller = Controller(Game(rng=ScriptedRng([PieceType.O])), settings=Settings(music_volume=0))
    assert controller.music_state == "playing"
    assert controller.music_volume == 0


def test_effects_ignore_music_volume(audio, monkeypatch):
    recorders = {sound: RecordingSound() for sound in Sound}
    monkeypatch.setattr(audio, "_effects", recorders)
    controller = Controller(
        Game(rng=ScriptedRng([PieceType.T, PieceType.T])), settings=Settings(music_volume=0)
    )
    controller.key_down(Key.LEFT)
    audio.sync(controller)
    assert recorders[Sound.MOVE].plays == 1
