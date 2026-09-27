"""Scoring rules: classic points per line clear and level from total lines."""

from __future__ import annotations

# Base points for clearing 1-4 lines with a single lock.
LINE_CLEAR_POINTS: dict[int, int] = {1: 40, 2: 100, 3: 300, 4: 1200}
LINES_PER_LEVEL = 10


def points_for(lines_cleared: int, level: int) -> int:
    """Points for one lock that cleared the given number of lines at a level."""
    if lines_cleared == 0:
        return 0
    if lines_cleared not in LINE_CLEAR_POINTS:
        raise ValueError(f"cannot clear {lines_cleared} lines at once")
    return LINE_CLEAR_POINTS[lines_cleared] * (level + 1)


def level_for(total_lines: int) -> int:
    return total_lines // LINES_PER_LEVEL
