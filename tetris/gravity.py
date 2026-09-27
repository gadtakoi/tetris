"""Gravity speed: classic frames-per-row table by level at 60 frames per second."""

from __future__ import annotations

FRAMES_PER_SECOND = 60

# Frames per row for levels 0-9.
_FRAMES_BY_LEVEL = (48, 43, 38, 33, 28, 23, 18, 13, 8, 6)
# (first level of the range, frames per row) for levels 10 and above.
_FRAMES_BY_RANGE = ((29, 1), (19, 2), (16, 3), (13, 4), (10, 5))


def frames_per_row(level: int) -> int:
    """Frames the active piece waits before gravity moves it one row down."""
    if level < len(_FRAMES_BY_LEVEL):
        return _FRAMES_BY_LEVEL[level]
    for first_level, frames in _FRAMES_BY_RANGE:
        if level >= first_level:
            return frames
    raise AssertionError("unreachable")
