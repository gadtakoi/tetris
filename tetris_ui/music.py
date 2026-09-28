"""Background music: an original 16-bar A-minor loop at 140 BPM, played softly on triangle
waves whose notes fade like a mallet's."""

from __future__ import annotations

from tetris_ui.synth import SAMPLE_RATE, Samples, mix, sequence

TEMPO_BPM = 140
BEATS = 64  # 16 bars of 4/4
SAMPLES_PER_BEAT = SAMPLE_RATE * 60 / TEMPO_BPM  # 9450 samples

# (note, beats); "R" is a rest. Four bars per line.
MELODY: tuple[tuple[str, float], ...] = (
    ("A4", 1), ("C5", .5), ("E5", .5), ("A5", 1), ("G5", .5), ("E5", .5),
    ("F5", 1), ("E5", .5), ("D5", .5), ("E5", 2),
    ("D5", 1), ("C5", .5), ("B4", .5), ("C5", 1), ("A4", 1),
    ("B4", .5), ("C5", .5), ("D5", 1), ("E5", 2),

    ("A4", 1), ("C5", .5), ("E5", .5), ("A5", 1), ("B5", .5), ("C6", .5),
    ("B5", 1), ("A5", .5), ("G5", .5), ("A5", 2),
    ("F5", 1), ("E5", .5), ("D5", .5), ("C5", 1), ("B4", 1),
    ("A4", 3), ("R", 1),

    ("E5", .5), ("F5", .5), ("G5", 1), ("C5", 1), ("E5", 1),
    ("D5", .5), ("E5", .5), ("F5", 1), ("B4", 2),
    ("C5", .5), ("D5", .5), ("E5", 1), ("A4", 1), ("C5", 1),
    ("B4", 1), ("G#4", 1), ("E4", 2),

    ("A4", .5), ("B4", .5), ("C5", 1), ("D5", .5), ("E5", .5), ("F5", 1),
    ("E5", 1), ("D5", .5), ("C5", .5), ("B4", 2),
    ("C5", 1), ("B4", .5), ("A4", .5), ("G#4", 1), ("B4", 1),
    ("A4", 3), ("R", 1),
)

# One chord per bar, played as root - fifth - octave - fifth quarter notes.
_BASS_PATTERNS = {
    "Am": ("A2", "E3", "A3", "E3"),
    "Dm": ("D3", "A3", "D4", "A3"),
    "E": ("E2", "B2", "E3", "B2"),
    "C": ("C3", "G3", "C4", "G3"),
    "G": ("G2", "D3", "G3", "D3"),
    "F": ("F2", "C3", "F3", "C3"),
}
CHORDS = (
    "Am", "Dm", "Am", "E",
    "Am", "E", "Dm", "Am",
    "C", "G", "Am", "E",
    "F", "G", "E", "Am",
)
BASS: tuple[tuple[str, float], ...] = tuple(
    (note, 1) for chord in CHORDS for note in _BASS_PATTERNS[chord]
)


def render_music() -> Samples:
    """The whole loop; it starts and ends at zero, so looping has no click.

    The two volumes add up to less than 1, so mixing the voices never clips. Short notes
    keep most of their level, long ones fade out before the next.
    """
    lead = sequence(MELODY, SAMPLES_PER_BEAT, 0.5, decay_ms=350)
    bass = sequence(BASS, SAMPLES_PER_BEAT, 0.45, decay_ms=300)
    return mix(lead, bass)
