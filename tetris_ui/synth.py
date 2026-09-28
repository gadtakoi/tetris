"""Tiny PCM synthesizer in pure Python: 22050 Hz, 16-bit, mono, no files.

Every note is a soft triangle wave; most notes also fade out after their attack.
"""

from __future__ import annotations

import re
import sys
from array import array
from collections.abc import Iterable, Sequence

SAMPLE_RATE = 22050
PEAK = 26214  # 80 % of the 16-bit full scale
ATTACK_MS = 4
RELEASE_MS = 12

Samples = array  # array('h')

_NOTE_OFFSETS = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
_NOTE_RE = re.compile(r"^([A-G])([#b]?)(\d)$")


def ms_to_samples(ms: float) -> int:
    """Number of samples in `ms` milliseconds at SAMPLE_RATE."""
    return round(ms * SAMPLE_RATE / 1000)


def note_freq(note: str) -> float:
    """Frequency of a note name such as "A4", "C#5" or "Eb3" (A4 = 440 Hz)."""
    match = _NOTE_RE.match(note)
    if match is None:
        raise ValueError(f"bad note {note!r}")
    letter, accidental, octave = match.groups()
    semitones = _NOTE_OFFSETS[letter] + {"#": 1, "b": -1, "": 0}[accidental]
    semitones += 12 * (int(octave) - 4)
    return 440.0 * 2 ** (semitones / 12)


def silence(length: int) -> Samples:
    """`length` samples of silence."""
    return array("h", bytes(2 * length))


def tone(
    freq: float,
    length: int,
    volume: float = 0.5,
    decay_ms: float | None = None,
) -> Samples:
    """One triangle-wave note of `length` samples that starts and ends at zero amplitude.

    The note rises for ATTACK_MS and falls to zero over its last RELEASE_MS. With
    `decay_ms` it also fades in between: after the attack its level halves every
    `decay_ms`. Without it the level stays even, as level_up has always sounded.
    """
    if not 0 <= volume <= 1:
        raise ValueError("volume must be within 0..1")
    if decay_ms is not None and decay_ms <= 0:
        raise ValueError("decay_ms must be positive")
    amplitude = volume * PEAK
    attack = max(1, min(ms_to_samples(ATTACK_MS), length // 4))
    release = max(1, min(ms_to_samples(RELEASE_MS), length // 2))
    release_start = length - 1 - release
    fade = 0.5 ** (1000 / (decay_ms * SAMPLE_RATE)) if decay_ms else 1.0  # per sample
    step = freq / SAMPLE_RATE
    out = array("h", bytes(2 * length))
    phase = 0.0
    level = 1.0
    for i in range(length):
        value = 4 * phase - 1 if phase < 0.5 else 3 - 4 * phase
        phase += step
        if phase >= 1.0:
            phase -= 1.0
        # The envelope by parts: a linear rise, the (fading) level, a linear fall that
        # reaches exactly zero at the end. Without decay the level stays exactly 1.0.
        if i < attack:
            envelope = i / attack
        else:
            level *= fade
            envelope = level if i <= release_start else level * (length - 1 - i) / release
        out[i] = int(amplitude * value * envelope)
    return out


def concat(parts: Iterable[Samples]) -> Samples:
    """Join sample arrays one after another."""
    out = array("h")
    for part in parts:
        out.extend(part)
    return out


def mix(*tracks: Samples) -> Samples:
    """Sum tracks sample by sample (padding shorter ones), clipped to PEAK."""
    length = max(len(track) for track in tracks)
    out = array("h", bytes(2 * length))
    for track in tracks:
        for i, value in enumerate(track):
            out[i] = max(-PEAK, min(PEAK, out[i] + value))
    return out


def sequence(
    notes: Sequence[tuple[str, float]],
    samples_per_beat: float,
    volume: float,
    decay_ms: float | None = None,
) -> Samples:
    """Render (note, beats) pairs back to back; "R" is a rest. Each note fades by
    `decay_ms` if given (see tone()).

    Note boundaries are rounded from the running beat position, so the total
    length is exactly round(total_beats * samples_per_beat).
    """
    parts = []
    position = 0.0
    start = 0
    for note, beats in notes:
        position += beats
        end = round(position * samples_per_beat)
        length = end - start
        if note == "R":
            parts.append(silence(length))
        else:
            parts.append(tone(note_freq(note), length, volume, decay_ms))
        start = end
    return concat(parts)


def to_bytes(samples: Samples) -> bytes:
    """Little-endian 16-bit PCM, as pygame.mixer.Sound(buffer=...) expects."""
    data = array("h", samples)
    if sys.byteorder == "big":
        data.byteswap()
    return data.tobytes()


# --- Sound effects ---------------------------------------------------------


def _notes(
    names: Sequence[str], ms_each: float, volume: float, decay_ms: float | None = None
) -> Samples:
    """Named notes of `ms_each` milliseconds each, one after another, each fading by
    `decay_ms` if given."""
    length = ms_to_samples(ms_each)
    return concat(tone(note_freq(n), length, volume, decay_ms) for n in names)


# The volumes keep the effects that start together within full scale: clear or tetris
# with level_up, lock with game_over (see the audio spec, "Сведение без перегрузки").


def effect_move() -> Samples:
    """A soft short tick for a successful shift (30 ms)."""
    return tone(note_freq("A5"), ms_to_samples(30), 0.4, decay_ms=12)


def effect_rotate() -> Samples:
    """A soft two-note chirp for a successful rotation (50 ms)."""
    return _notes(["E5", "B5"], 25, 0.45, decay_ms=12)


def effect_lock() -> Samples:
    """A soft low knock for a piece locking without clearing lines (100 ms)."""
    return tone(note_freq("G3"), ms_to_samples(100), 0.5, decay_ms=30)


def effect_clear() -> Samples:
    """A C major arpeggio for clearing one to three lines (240 ms)."""
    return _notes(["C5", "E5", "G5"], 80, 0.65, decay_ms=45)


def effect_tetris() -> Samples:
    """A longer rising arpeggio for clearing four lines (500 ms)."""
    return _notes(["C5", "E5", "G5", "C6", "E6"], 100, 0.65, decay_ms=55)


def effect_level_up() -> Samples:
    """A rising scale for reaching a new level (400 ms), even and unchanged: the sound
    every other one is modelled on."""
    return _notes(["C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6"], 50, 0.5)


def effect_hold() -> Samples:
    """Two quick falling notes for putting a piece on hold (120 ms)."""
    return _notes(["G5", "D5"], 60, 0.5, decay_ms=25)


def effect_game_over() -> Samples:
    """A falling melody over a bass line when the game ends (1200 ms)."""
    lead = _notes(["E5", "D5", "C5", "B4", "A4", "E4"], 200, 0.4, decay_ms=100)
    bass = _notes(["A3", "G3", "F3", "E3", "D3", "A2"], 200, 0.3, decay_ms=120)
    return mix(lead, bass)


EFFECTS = {
    "move": effect_move,
    "rotate": effect_rotate,
    "lock": effect_lock,
    "clear": effect_clear,
    "tetris": effect_tetris,
    "level_up": effect_level_up,
    "game_over": effect_game_over,
    "hold": effect_hold,
}
