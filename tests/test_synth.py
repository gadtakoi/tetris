import time
from array import array

import pytest

from tetris_ui import music, synth


@pytest.mark.parametrize("name", sorted(synth.EFFECTS))
def test_effect_format_length_and_peak(name):
    samples = synth.EFFECTS[name]()
    assert isinstance(samples, array) and samples.typecode == "h"
    limit_ms = 1500 if name == "game_over" else 600
    assert 0 < len(samples) <= synth.ms_to_samples(limit_ms)
    assert max(abs(s) for s in samples) <= 26214


@pytest.mark.parametrize("notes", [music.MELODY, music.BASS])
def test_voices_span_64_beats(notes):
    assert sum(beats for _, beats in notes) == 64


def test_music_length_and_loop_edges():
    samples = music.render_music()
    assert len(samples) == round(16 * 4 * 60 / 140 * 22050)
    assert samples[0] == 0 and samples[-1] == 0
    assert max(abs(s) for s in samples) <= 26214


def test_synthesis_is_deterministic():
    first = [synth.to_bytes(f()) for f in synth.EFFECTS.values()]
    second = [synth.to_bytes(f()) for f in synth.EFFECTS.values()]
    assert first == second
    assert synth.to_bytes(music.render_music()) == synth.to_bytes(music.render_music())


def test_full_synthesis_is_fast_enough():
    start = time.perf_counter()
    for effect in synth.EFFECTS.values():
        effect()
    music.render_music()
    assert time.perf_counter() - start < 3


def test_note_frequencies():
    assert synth.note_freq("A4") == 440
    assert synth.note_freq("A5") == 880
    assert synth.note_freq("C#5") == synth.note_freq("Db5")
    with pytest.raises(ValueError):
        synth.note_freq("H2")


def test_to_bytes_is_16_bit_little_endian():
    assert synth.to_bytes(array("h", [1, -2])) == b"\x01\x00\xfe\xff"


def test_mix_clips_to_peak():
    loud = array("h", [20000, -20000])
    assert list(synth.mix(loud, loud)) == [26214, -26214]
