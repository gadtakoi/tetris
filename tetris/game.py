"""Game state and piece control: moves, rotation, drops, gravity, locking, scoring and game over."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from enum import Enum

from tetris.board import Board, Cell
from tetris.gravity import FRAMES_PER_SECOND, frames_per_row
from tetris.pieces import ROTATION_COUNT, PieceType, kick_offsets, shape_cells, spawn_position
from tetris.randomizer import Randomizer
from tetris.scoring import level_for, points_for


# Gravity time is kept in integer units of 1/60 ms, so frame-based intervals stay exact.
_UNITS_PER_MS = FRAMES_PER_SECOND
_MS_PER_SECOND = 1000

LOCK_DELAY_MS = 500  # how long a piece may lie on the stack before it locks
MAX_LOCK_RESETS = 15  # moves or rotations that may restart that time, per piece
_LOCK_DELAY_UNITS = LOCK_DELAY_MS * _UNITS_PER_MS


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
        """Start over: empty board, counters at zero, a new bag, fresh active and next
        pieces, an empty hold slot."""
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
        self.held_type: PieceType | None = None  # the hold slot
        self.can_hold = True  # hold may be used once per piece
        self._reset_lock_delay()

    def move_left(self) -> bool:
        """Shift the active piece one column left; return whether it moved."""
        return self._move(replace(self.active, col=self.active.col - 1))

    def move_right(self) -> bool:
        """Shift the active piece one column right; return whether it moved."""
        return self._move(replace(self.active, col=self.active.col + 1))

    def rotate_cw(self) -> bool:
        """Rotate the active piece clockwise with SRS kicks; return whether it turned."""
        return self._rotate(1)

    def rotate_ccw(self) -> bool:
        """Rotate the active piece counterclockwise with SRS kicks; return whether it turned."""
        return self._rotate(ROTATION_COUNT - 1)

    def step_down(self) -> StepResult:
        """The player's soft drop: move the active piece one row down.

        A piece that is lying cannot step down and is not locked by this command:
        REJECTED is returned and the lock delay decides when it locks. A successful
        move restarts the gravity interval, so gravity does not add a second step
        right after the player's one.
        """
        if not self._advance():
            return StepResult.REJECTED
        self._gravity_time = 0  # a player's drop restarts the gravity interval
        return StepResult.MOVED

    def hard_drop(self) -> StepResult:
        """Drop the active piece straight to the lowest valid row and lock it."""
        if self.is_over:
            return StepResult.REJECTED
        self.active = self._dropped()
        self._lock()
        return StepResult.LOCKED

    def hold(self) -> bool:
        """Put the active piece in the hold slot; return whether it was allowed.

        An empty slot takes the active piece and the next piece comes in, as after a
        lock; a full slot swaps with the active piece, and the next piece stays. The
        incoming piece starts at its spawn position in orientation 0. Hold works once
        per piece: it is allowed again after the active piece locks.
        """
        if self.is_over or not self.can_hold:
            return False
        current = self.active.type
        if self.held_type is None:
            self.held_type = current
            self._spawn(self.next_type)
        else:
            self.held_type, incoming = current, self.held_type
            self._bring_in(incoming)
        self.can_hold = False
        return True

    def ghost_cells(self) -> tuple[Cell, ...]:
        """Cells where the active piece would lock if dropped straight down."""
        if self.is_over:
            return ()
        return self._dropped().cells()

    def tick(self, dt_ms: int) -> None:
        """Advance time by dt_ms milliseconds: gravity steps and the lock delay.

        Time is split into spans up to the next event (a gravity step or the end of
        the lock delay), so the result does not depend on how the time is chunked.
        The time left over after a lock is dropped.
        """
        if dt_ms < 0:
            raise ValueError(f"dt_ms must not be negative, got {dt_ms}")
        remaining = dt_ms * _UNITS_PER_MS
        while remaining > 0 and not self.is_over:
            interval = self._gravity_interval()
            span = min(remaining, interval - self._gravity_time)
            lying = self._is_lying()
            if lying:
                span = min(span, _LOCK_DELAY_UNITS - self._lock_time)
            remaining -= span
            self._gravity_time += span
            if lying:
                self._lock_time += span
                if self._lock_time >= _LOCK_DELAY_UNITS:
                    self._lock()
                    break
            if self._gravity_time >= interval:
                self._gravity_time = 0
                self._advance()

    def _gravity_interval(self) -> int:
        """Gravity interval of the current level, in 1/60 ms."""
        return frames_per_row(self.level) * _MS_PER_SECOND

    def _advance(self) -> bool:
        """Move the active piece down one row if it can; a lying piece stays put."""
        if not self._try(replace(self.active, row=self.active.row + 1)):
            return False
        self._note_descent()
        return True

    def _is_lying(self) -> bool:
        """Whether the active piece cannot move down even one row."""
        return not self._fits(replace(self.active, row=self.active.row + 1))

    def _move(self, candidate: ActivePiece) -> bool:
        """Shift or turn the active piece to the candidate, applying the lock delay rules."""
        was_lying = not self.is_over and self._is_lying()
        if not self._try(candidate):
            return False
        if was_lying and self._resets_left > 0:
            self._lock_time = 0  # moving a lying piece buys it a fresh lock delay
            self._resets_left -= 1
        self._note_descent()  # an SRS kick may move the piece down
        return True

    def _note_descent(self) -> None:
        """Give back the full lock delay once the piece gets lower than ever before."""
        if self.active.row > self._lowest_row:
            self._lowest_row = self.active.row
            self._resets_left = MAX_LOCK_RESETS
            self._lock_time = 0

    def _reset_lock_delay(self) -> None:
        """Lock delay state of a newly arrived piece: no time lying, all resets left."""
        self._lock_time = 0  # time spent lying, in 1/60 ms
        self._resets_left = MAX_LOCK_RESETS
        self._lowest_row = self.active.row

    def _dropped(self) -> ActivePiece:
        """The active piece moved straight down as far as it fits."""
        piece = self.active
        while self._fits(below := replace(piece, row=piece.row + 1)):
            piece = below
        return piece

    def _rotate(self, delta: int) -> bool:
        """Turn the active piece by `delta` quarter turns clockwise using SRS.

        Tries the rotation in place, then each SRS kick in order, and keeps the
        first position that fits; if none fits, nothing changes.
        """
        active = self.active
        rotation = (active.rotation + delta) % ROTATION_COUNT
        for dx, dy in kick_offsets(active.type, active.rotation, rotation):
            # SRS offsets point up, board rows grow downward.
            candidate = replace(active, rotation=rotation, col=active.col + dx, row=active.row - dy)
            if self._move(candidate):
                return True
        return False

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
        self.can_hold = True
        self._spawn(self.next_type)

    def _spawn(self, piece_type: PieceType) -> None:
        """Bring piece_type in at its spawn position and draw a new next piece."""
        if self._bring_in(piece_type):
            self.next_type = self._randomizer.next()

    def _bring_in(self, piece_type: PieceType) -> bool:
        """Make piece_type the active piece at its spawn position; False on block out.

        Restarts the gravity interval and the lock delay. If the spawn cells are
        occupied the game is over (block out) and the active piece is left as it was.
        """
        self._gravity_time = 0
        piece = ActivePiece.spawn(piece_type)
        if not self._fits(piece):
            self.is_over = True  # block out
            return False
        self.active = piece
        self._reset_lock_delay()
        return True
