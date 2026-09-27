import pytest

from tetris.board import HEIGHT, VISIBLE_HEIGHT, WIDTH, Board
from tetris.pieces import PieceType


def test_new_board_dimensions():
    assert (WIDTH, HEIGHT) == (10, 22)
    assert VISIBLE_HEIGHT == 20
    assert len(Board().visible_rows()) == 20


def test_new_board_is_empty():
    board = Board()
    cells = [board.get(c, r) for r in range(HEIGHT) for c in range(WIDTH)]
    assert len(cells) == 220
    assert all(cell is None for cell in cells)


def test_cell_stores_piece_type():
    board = Board()
    board.place([(4, 21)], PieceType.T)
    assert board.get(4, 21) is PieceType.T


def test_empty_cell_inside_board_is_free():
    assert Board().is_free(0, 21)


def test_occupied_cell_is_not_free():
    board = Board()
    board.place([(3, 10)], PieceType.Z)
    assert not board.is_free(3, 10)


@pytest.mark.parametrize("cell", [(-1, 10), (10, 10), (5, 22), (5, -1)])
def test_out_of_bounds_cells_are_not_free(cell):
    assert not Board().is_free(*cell)


def test_visible_rows_are_rows_2_to_21():
    board = Board()
    board.place([(0, 0), (0, 1)], PieceType.I)  # hidden rows
    board.place([(1, 2)], PieceType.S)  # first visible row
    board.place([(2, 21)], PieceType.L)  # last visible row
    rows = board.visible_rows()
    assert len(rows) == 20
    assert rows[0][1] is PieceType.S
    assert rows[-1][2] is PieceType.L
    assert all(cell is not PieceType.I for row in rows for cell in row)


def test_visible_rows_are_copies():
    board = Board()
    board.visible_rows()[0][0] = PieceType.T
    assert board.get(0, 2) is None
