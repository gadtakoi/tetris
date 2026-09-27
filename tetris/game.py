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
    """Outcome of moving the active piece down one row."""

    MOVED = "moved"
    LOCKED = "locked"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ActivePiece:
    """The falling piece: its type, orientation (0-3) and bounding box position.

    col and row are the top-left corner of the piece's bounding box on the board; col
    may be negative when the box overhangs the left wall. Instances are immutable, so a
    move builds a candidate and keeps it only if it fits.
    """

    type: PieceType
    rotation: int
    col: int  # column of the bounding box's left edge; may be negative
    row: int  # row of the bounding box's top edge

    @classmethod
    def spawn(cls, piece_type: PieceType) -> ActivePiece:
        """The piece of the given type in orientation 0 at its spawn position."""
        col, row = spawn_position(piece_type)
        return cls(piece_type, 0, col, row)

    def cells(self) -> tuple[Cell, ...]:
        """The four board cells (col, row) the piece covers."""
        return tuple(
            (self.col + c, self.row + r)
            for r, c in shape_cells(self.type, self.rotation)
        )


class Game:
    """A game of Tetris: the board, the falling and next pieces, score and gravity.

    Pass `seed` for a reproducible game or `rng` to script the piece sequence (tests).
    The game never reads a clock: time only moves through tick(). Commands report
    whether they did anything and are rejected once the game is over.
    """

    def __init__(self, seed: int | None = None, rng: random.Random | None = None) -> None:
        self._randomizer = Randomizer(rng if rng is not None else random.Random(seed))
        self.new_game()

    def new_game(self) -> None:
        """Start over: empty board, counters at zero, a new bag, fresh active and next pieces."""
        self._randomizer.reset()
        self.board = Board()
        self.is_over = False
        self.score = 0
        self.lines = 0
        self.level = 0
        self.last_cleared = 0  # lines removed by the most recent lock
        self.pieces_locked = 0
        self._gravity_time = 0  # accumulated time, in 1/60 ms
        self.active = ActivePiece.spawn(self._randomizer.next())
        self.next_type = self._randomizer.next()

    def move_left(self) -> bool:
        """Shift the active piece one column left; return whether it moved."""
        return self._try(replace(self.active, col=self.active.col - 1))

    def move_right(self) -> bool:
        """Shift the active piece one column right; return whether it moved."""
        return self._try(replace(self.active, col=self.active.col + 1))

    def rotate_cw(self) -> bool:
        """Rotate the active piece clockwise in place (no wall kicks); return whether it turned."""
        return self._rotate(1)

    def rotate_ccw(self) -> bool:
        """Rotate the active piece counterclockwise in place (no wall kicks); return whether it turned."""
        return self._rotate(ROTATION_COUNT - 1)

    def step_down(self) -> StepResult:
        """The player's soft drop: move the active piece one row down, or lock it.

        A successful move restarts the gravity interval, so gravity does not add a second
        step right after the player's one.
        """
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
        """Turn the active piece by `delta` quarter turns clockwise if the result fits."""
        rotation = (self.active.rotation + delta) % ROTATION_COUNT
        return self._try(replace(self.active, rotation=rotation))

    def _fits(self, piece: ActivePiece) -> bool:
        """Whether every cell of the piece is inside the board and empty."""
        return all(self.board.is_free(col, row) for col, row in piece.cells())

    def _try(self, candidate: ActivePiece) -> bool:
        """Replace the active piece with the candidate if it fits."""
        if self.is_over or not self._fits(candidate):
            return False
        self.active = candidate
        return True

    def _lock(self) -> None:
        """Lock the active piece and bring in the next one.

        The order matters: write the cells, clear full rows, add points at the level before
        this lock, update lines and level, then spawn the next piece (which may end the game).
        """
        self.pieces_locked += 1
        self.board.place(self.active.cells(), self.active.type)
        cleared = self.board.clear_full_rows()
        self.last_cleared = cleared
        self.score += points_for(cleared, self.level)  # level before this lock
        self.lines += cleared
        self.level = level_for(self.lines)
        self._spawn(self.next_type)

    def _spawn(self, piece_type: PieceType) -> None:
        """Bring piece_type in at its spawn position and draw a new next piece.

        Restarts the gravity interval. If the spawn cells are occupied the game is over
        (block out) and the active piece is left as it was.
        """
        self._gravity_time = 0
        piece = ActivePiece.spawn(piece_type)
        if not self._fits(piece):
            self.is_over = True  # block out
            return
        self.active = piece
        self.next_type = self._randomizer.next()
