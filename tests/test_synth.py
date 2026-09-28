import cmath
import hashlib
import math
import time
from array import array

import pytest

from tetris_ui import music, synth

# The share of power above a frequency is estimated as the audio spec says: frames of
# 1024 samples, 512 apart, each under a Hann window, the last one padded with zeros.
FRAME, HOP = 1024, 512
_HANN = [0.5 - 0.5 * math.cos(2 * math.pi * n / (FRAME - 1)) for n in range(FRAME)]
_TWIDDLES = [cmath.exp(-2j * math.pi * k / FRAME) for k in range(FRAME // 2)]
_BIT_REVERSED = [int(f"{i:010b}"[::-1], 2) for i in range(FRAME)]

# The last note of each effect but level_up, from the audio spec, in ms.
LAST_NOTE_MS = {"move": 30, "rotate": 25, "hold": 60, "lock": 100, "clear": 80,
                "tetris": 100, "game_over": 200}
# Effects that start in the same frame during a game.
TOGETHER = [("clear", "level_up"), ("tetris", "level_up"), ("lock", "game_over")]
# level_up as it was before update-sound-timbre; it must not change.
LEVEL_UP_SHA256 = "dacfac1534c2fed572dc06210eee43de0460ab1707f7a51781018c1292cf2eb4"


def _fft(values: list[float]) -> list[complex]:
    """Radix-2 FFT of FRAME values."""
    a = [complex(values[i]) for i in _BIT_REVERSED]
    size = 2
    while size <= FRAME:
        half, stride = size // 2, FRAME // size
        for start in range(0, FRAME, size):
            for k in range(half):
                t = _TWIDDLES[k * stride] * a[start + k + half]
                a[start + k + half] = a[start + k] - t
                a[start + k] += t
        size *= 2
    return a


def high_share(samples, cutoff: float = 2000) -> float:
    """Share of the power at positive frequencies from `cutoff` up, over all frames."""
    first_high = math.ceil(cutoff * FRAME / synth.SAMPLE_RATE)  # first bin at or above it
    total = high = 0.0
    start = 0
    while True:
        chunk = list(samples[start:start + FRAME])
        chunk += [0] * (FRAME - len(chunk))
        spectrum = _fft([value * weight for value, weight in zip(chunk, _HANN)])
        powers = [abs(c) ** 2 for c in spectrum[1:FRAME // 2]]  # bins 1..511
        total += sum(powers)
        high += sum(powers[first_high - 1:])
        if start + FRAME >= len(samples):
            return high / total
        start += HOP


def rms(samples) -> float:
    return math.sqrt(sum(value * value for value in samples) / len(samples))


def peak(samples) -> int:
    return max(abs(value) for value in samples)


def sine(freq: float, ms: float) -> list[float]:
    return [math.sin(2 * math.pi * freq * i / synth.SAMPLE_RATE)
            for i in range(synth.ms_to_samples(ms))]


def test_high_share_tells_low_from_high():
    assert high_share(sine(500, 200)) < 0.001
    assert high_share(sine(5000, 200)) > 0.999
    assert high_share(sine(500, 20)) < 0.001  # shorter than one frame


# --- Notes -------------------------------------------------------------------------


def level_at(samples, ms: float) -> float:
    """RMS over the 10 ms (ten periods of 1 kHz) centered at `ms`."""
    center = synth.ms_to_samples(ms)
    half = synth.ms_to_samples(5)
    return rms(samples[center - half:center + half])


def test_note_level_halves_every_decay_ms():
    note = synth.tone(1000, synth.ms_to_samples(400), 1.0, decay_ms=50)
    assert level_at(note, 250) / level_at(note, 200) == pytest.approx(0.5, rel=0.05)


def test_note_without_decay_keeps_an_even_level():
    note = synth.tone(1000, synth.ms_to_samples(400), 1.0)
    assert level_at(note, 300) == pytest.approx(level_at(note, 100), rel=0.01)


@pytest.mark.parametrize("decay_ms", [None, 12, 300])
def test_note_starts_and_ends_at_zero(decay_ms):
    note = synth.tone(synth.note_freq("E6"), synth.ms_to_samples(60), 0.8, decay_ms)
    assert note[0] == 0 and note[-1] == 0
    assert peak(note) > 0


@pytest.mark.parametrize("decay_ms", [0, -5])
def test_note_decay_must_be_positive(decay_ms):
    with pytest.raises(ValueError):
        synth.tone(440, 100, 0.5, decay_ms)


# --- Timbre (audio spec: "Тембр звуков", "Сведение без перегрузки") --------------


@pytest.mark.parametrize("name", sorted(synth.EFFECTS))
def test_effects_sound_soft(name):
    assert high_share(synth.EFFECTS[name]()) <= 0.03


@pytest.mark.parametrize(("name", "ms"), sorted(LAST_NOTE_MS.items()))
def test_effects_fade_out(name, ms):
    note = synth.EFFECTS[name]()[-synth.ms_to_samples(ms):]
    half = len(note) // 2
    assert rms(note[half:]) <= 0.6 * rms(note[:half])


def test_level_up_is_unchanged():
    data = synth.to_bytes(synth.effect_level_up())
    assert hashlib.sha256(data).hexdigest() == LEVEL_UP_SHA256


@pytest.mark.parametrize(("first", "second"), TOGETHER)
def test_effects_played_together_stay_within_full_scale(first, second):
    assert peak(synth.EFFECTS[first]()) + peak(synth.EFFECTS[second]()) <= 32767


@pytest.fixture(scope="module")
def melody():
    """The whole music loop, synthesized once for the module."""
    return music.render_music()


def test_music_sounds_soft(melody):
    assert high_share(melody) <= 0.03


def test_music_voices_mix_without_clipping(melody):
    assert peak(melody) < 26214


# --- Format ------------------------------------------------------------------------


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
