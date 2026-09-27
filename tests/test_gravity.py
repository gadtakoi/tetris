import pytest

from tetris.gravity import FRAMES_PER_SECOND, frames_per_row


@pytest.mark.parametrize(
    ("level", "frames"),
    [
        (0, 48), (1, 43), (2, 38), (3, 33), (4, 28),
        (5, 23), (6, 18), (7, 13), (8, 8), (9, 6),
        (10, 5), (12, 5),
        (13, 4), (15, 4),
        (16, 3), (18, 3),
        (19, 2), (28, 2),
        (29, 1), (50, 1),
    ],
)
def test_frames_per_row(level, frames):
    assert frames_per_row(level) == frames


@pytest.mark.parametrize(("level", "interval_ms"), [(0, 800), (9, 100)])
def test_interval_in_milliseconds(level, interval_ms):
    assert frames_per_row(level) * 1000 / FRAMES_PER_SECOND == interval_ms
