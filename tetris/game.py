"""Game state and piece control: moves, rotation, drops, gravity, locking, scoring and game over."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from enum import Enum

from tetris.board import Board, Cell
from tetris.gravity import FRAMES_PER_SECOND, frames_per_row
from tetris.pieces import ROTATION_COUNT, PieceType, shape_cells, spawn_position
from tetris.randomizer import Randomizer
from tetris.scoring import level_for, points_for


# Gravity time is kept in integer units of 1/60 ms, so frame-based intervals stay exact.
_UNITS_PER_MS = FRAMES_PER_SECOND
_MS_PER_SECOND = 1000


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
        self.score = 0
        self.lines = 0
        self.level = 0
        self.last_cleared = 0  # lines removed by the most recent lock
        self._gravity_time = 0  # accumulated time, in 1/60 ms
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
        result = self._advance()
        if result is StepResult.MOVED:
            self._gravity_time = 0  # a player's drop restarts the gravity interval
        return result

    def hard_drop(self) -> StepResult:
        """Drop the active piece straight to the lowest valid row and lock it."""
        if self.is_over:
            return StepResult.REJECTED
        self.active = self._dropped()
        self._lock()
        return StepResult.LOCKED

    def ghost_cells(self) -> tuple[Cell, ...]:
        """Cells where the active piece would lock if dropped straight down."""
        if self.is_over:
            return ()
        return self._dropped().cells()

    def tick(self, dt_ms: int) -> None:
        """Advance time by dt_ms milliseconds, applying gravity steps as they fall due."""
        if dt_ms < 0:
            raise ValueError(f"dt_ms must not be negative, got {dt_ms}")
        if self.is_over:
            return
        self._gravity_time += dt_ms * _UNITS_PER_MS
        # A lock spawns the next piece, which resets the time and ends the loop.
        while not self.is_over and self._gravity_time >= self._gravity_interval():
            self._gravity_time -= self._gravity_interval()
            self._advance()

    def _gravity_interval(self) -> int:
        """Gravity interval of the current level, in 1/60 ms."""
        return frames_per_row(self.level) * _MS_PER_SECOND

    def _advance(self) -> StepResult:
        """Move the active piece down one row, or lock it if it cannot move."""
        if self.is_over:
            return StepResult.REJECTED
        if self._try(replace(self.active, row=self.active.row + 1)):
            return StepResult.MOVED
        self._lock()
        return StepResult.LOCKED

    def _dropped(self) -> ActivePiece:
        """The active piece moved straight down as far as it fits."""
        piece = self.active
        while self._fits(below := replace(piece, row=piece.row + 1)):
            piece = below
        return piece

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
        cleared = self.board.clear_full_rows()
        self.last_cleared = cleared
        self.score += points_for(cleared, self.level)  # level before this lock
        self.lines += cleared
        self.level = level_for(self.lines)
        self._spawn(self.next_type)

    def _spawn(self, piece_type: PieceType) -> None:
        self._gravity_time = 0
        piece = ActivePiece.spawn(piece_type)
        if not self._fits(piece):
            self.is_over = True  # block out
            return
        self.active = piece
        self.next_type = self._randomizer.next()
