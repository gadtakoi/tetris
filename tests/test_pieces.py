import pytest

from tetris.pieces import (
    ROTATION_COUNT,
    PieceType,
    kick_offsets,
    shape_cells,
    spawn_position,
)


def _board_cells(piece_type: PieceType, rotation: int = 0) -> set[tuple[int, int]]:
    """Cells of a freshly spawned piece as (col, row) on the board."""
    col, row = spawn_position(piece_type)
    return {(col + c, row + r) for r, c in shape_cells(piece_type, rotation)}


@pytest.mark.parametrize("piece_type", list(PieceType))
@pytest.mark.parametrize("rotation", range(ROTATION_COUNT))
def test_every_piece_has_four_distinct_cells(piece_type, rotation):
    cells = shape_cells(piece_type, rotation)
    assert len(cells) == 4
    assert len(set(cells)) == 4


def test_exactly_seven_piece_types():
    assert {p.value for p in PieceType} == {"I", "O", "T", "S", "Z", "J", "L"}


def test_t_shape_in_orientation_0():
    assert set(shape_cells(PieceType.T, 0)) == {(0, 1), (1, 0), (1, 1), (1, 2)}


def test_t_rotated_clockwise():
    assert set(shape_cells(PieceType.T, 1)) == {(0, 1), (1, 1), (1, 2), (2, 1)}


def test_i_rotated_clockwise():
    assert set(shape_cells(PieceType.I, 1)) == {(0, 2), (1, 2), (2, 2), (3, 2)}


@pytest.mark.parametrize("piece_type", list(PieceType))
@pytest.mark.parametrize("start", range(ROTATION_COUNT))
def test_four_rotations_return_original_shape(piece_type, start):
    assert shape_cells(piece_type, start + 4) == shape_cells(piece_type, start)


@pytest.mark.parametrize("piece_type", list(PieceType))
@pytest.mark.parametrize("start", range(ROTATION_COUNT))
def test_ccw_undoes_cw(piece_type, start):
    cw = (start + 1) % ROTATION_COUNT
    back = (cw + 3) % ROTATION_COUNT
    assert back == start
    assert shape_cells(piece_type, back) == shape_cells(piece_type, start)


@pytest.mark.parametrize("rotation", range(ROTATION_COUNT))
def test_o_does_not_change_on_rotation(rotation):
    assert shape_cells(PieceType.O, rotation) == shape_cells(PieceType.O, 0)


def test_spawn_t():
    assert _board_cells(PieceType.T) == {(4, 2), (3, 3), (4, 3), (5, 3)}


def test_spawn_i():
    assert _board_cells(PieceType.I) == {(3, 2), (4, 2), (5, 2), (6, 2)}


def test_spawn_o():
    assert _board_cells(PieceType.O) == {(4, 2), (5, 2), (4, 3), (5, 3)}


@pytest.mark.parametrize("piece_type", list(PieceType))
def test_spawned_pieces_occupy_top_two_visible_rows(piece_type):
    rows = {row for _, row in _board_cells(piece_type)}
    assert rows <= {2, 3}


# --- SRS kick tables -------------------------------------------------------

TRANSITIONS = [(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (3, 0), (0, 3)]


@pytest.mark.parametrize("piece_type", [PieceType.I, PieceType.T])  # I table, JLSTZ table
@pytest.mark.parametrize("transition", TRANSITIONS)
def test_kicks_start_in_place_then_four_offsets(piece_type, transition):
    offsets = kick_offsets(piece_type, *transition)
    assert offsets[0] == (0, 0)
    assert len(offsets) == 5


@pytest.mark.parametrize("piece_type", [PieceType.I, PieceType.J, PieceType.L, PieceType.S, PieceType.T, PieceType.Z])
@pytest.mark.parametrize("transition", TRANSITIONS)
def test_reverse_rotation_negates_the_kicks(piece_type, transition):
    forward = kick_offsets(piece_type, *transition)
    backward = kick_offsets(piece_type, *reversed(transition))
    assert backward == tuple((-dx, -dy) for dx, dy in forward)


def test_jlstz_share_one_table():
    for transition in TRANSITIONS:
        tables = {kick_offsets(t, *transition) for t in (PieceType.J, PieceType.L, PieceType.S, PieceType.T, PieceType.Z)}
        assert len(tables) == 1


def test_o_never_kicks():
    for transition in TRANSITIONS:
        assert kick_offsets(PieceType.O, *transition) == ((0, 0),)


def test_kick_values_match_the_srs_tables():
    assert kick_offsets(PieceType.T, 0, 1) == ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2))
    assert kick_offsets(PieceType.I, 1, 2) == ((0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1))
