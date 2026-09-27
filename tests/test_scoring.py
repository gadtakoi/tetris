import pytest

from tetris.scoring import level_for, points_for


@pytest.mark.parametrize(
    ("lines", "points"), [(1, 40), (2, 100), (3, 300), (4, 1200)]
)
def test_points_at_level_0(lines, points):
    assert points_for(lines, 0) == points


def test_double_at_level_2():
    assert 500 + points_for(2, 2) == 800


def test_triple_at_level_9():
    assert points_for(3, 9) == 3000


def test_no_lines_no_points():
    assert points_for(0, 0) == 0
    assert points_for(0, 7) == 0


@pytest.mark.parametrize("lines", [5, -1])
def test_impossible_line_count_is_rejected(lines):
    with pytest.raises(ValueError):
        points_for(lines, 0)


@pytest.mark.parametrize(
    ("total_lines", "level"), [(0, 0), (9, 0), (10, 1), (13, 1), (205, 20)]
)
def test_level_for(total_lines, level):
    assert level_for(total_lines) == level
