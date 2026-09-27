"""The playfield: a 10x22 grid whose top two rows are a hidden buffer."""

from __future__ import annotations

from collections.abc import Iterable

from tetris.pieces import PieceType

WIDTH = 10
HEIGHT = 22
HIDDEN_ROWS = 2
VISIBLE_HEIGHT = HEIGHT - HIDDEN_ROWS

# A board cell as (col, row); row grows downward.
Cell = tuple[int, int]


class Board:
    """The 10 x 22 playfield of locked cells.

    Each cell is empty (None) or holds the type of the piece locked there. Cells are
    addressed as (col, row) with row growing downward; rows 0-1 are the hidden spawn
    buffer above the 20 visible rows.
    """

    def __init__(self) -> None:
        self._grid: list[list[PieceType | None]] = [
            [None] * WIDTH for _ in range(HEIGHT)
        ]

    @staticmethod
    def in_bounds(col: int, row: int) -> bool:
        """Whether (col, row) lies inside the grid, hidden rows included."""
        return 0 <= col < WIDTH and 0 <= row < HEIGHT

    def get(self, col: int, row: int) -> PieceType | None:
        """Return the piece type occupying a cell, or None if it is empty."""
        return self._grid[row][col]

    def is_free(self, col: int, row: int) -> bool:
        """A cell is free if it is inside the board and empty."""
        return self.in_bounds(col, row) and self._grid[row][col] is None

    def place(self, cells: Iterable[Cell], piece_type: PieceType) -> None:
        """Mark the given cells as occupied by piece_type; the caller checks they fit."""
        for col, row in cells:
            self._grid[row][col] = piece_type

    def clear_full_rows(self) -> int:
        """Remove every full row, shift the rest down; return how many were removed."""
        kept = [row for row in self._grid if any(cell is None for cell in row)]
        cleared = HEIGHT - len(kept)
        self._grid = [[None] * WIDTH for _ in range(cleared)] + kept
        return cleared

    def visible_rows(self) -> list[list[PieceType | None]]:
        """Return copies of the visible rows (2-21), top to bottom."""
        return [list(row) for row in self._grid[HIDDEN_ROWS:]]
