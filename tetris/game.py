"""Game state and piece control: moves, rotation, locking and game over."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from enum import Enum

from tetris.board import Board, Cell
from tetris.pieces import ROTATION_COUNT, PieceType, shape_cells, spawn_position
from tetris.randomizer import Randomizer


class StepResult(Enum):
    MOVED = "moved"
    LOCKED = "locked"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ActivePiece:
    type: PieceType
    rotation: int
    col: int  # column of the bounding box's left edge; may be negative
    row: int  # row of the bounding box's top edge

    @classmethod
    def spawn(cls, piece_type: PieceType) -> ActivePiece:
        col, row = spawn_position(piece_type)
        return cls(piece_type, 0, col, row)

    def cells(self) -> tuple[Cell, ...]:
        return tuple(
            (self.col + c, self.row + r)
            for r, c in shape_cells(self.type, self.rotation)
        )


class Game:
    def __init__(self, seed: int | None = None, rng: random.Random | None = None) -> None:
        self._randomizer = Randomizer(rng if rng is not None else random.Random(seed))
        self.new_game()

    def new_game(self) -> None:
        self.board = Board()
        self.is_over = False
        self.active = ActivePiece.spawn(self._randomizer.next())
        self.next_type = self._randomizer.next()

    def move_left(self) -> bool:
        return self._try(replace(self.active, col=self.active.col - 1))

    def move_right(self) -> bool:
        return self._try(replace(self.active, col=self.active.col + 1))

    def rotate_cw(self) -> bool:
        return self._rotate(1)

    def rotate_ccw(self) -> bool:
        return self._rotate(ROTATION_COUNT - 1)

    def step_down(self) -> StepResult:
        if self.is_over:
            return StepResult.REJECTED
        if self._try(replace(self.active, row=self.active.row + 1)):
            return StepResult.MOVED
        self._lock()
        return StepResult.LOCKED

    def _rotate(self, delta: int) -> bool:
        rotation = (self.active.rotation + delta) % ROTATION_COUNT
        return self._try(replace(self.active, rotation=rotation))

    def _fits(self, piece: ActivePiece) -> bool:
        return all(self.board.is_free(col, row) for col, row in piece.cells())

    def _try(self, candidate: ActivePiece) -> bool:
        """Replace the active piece with the candidate if it fits."""
        if self.is_over or not self._fits(candidate):
            return False
        self.active = candidate
        return True

    def _lock(self) -> None:
        self.board.place(self.active.cells(), self.active.type)
        self._spawn(self.next_type)

    def _spawn(self, piece_type: PieceType) -> None:
        piece = ActivePiece.spawn(piece_type)
        if not self._fits(piece):
            self.is_over = True  # block out
            return
        self.active = piece
        self.next_type = self._randomizer.next()
