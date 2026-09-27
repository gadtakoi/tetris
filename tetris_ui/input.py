"""Keyboard input rules without pygame: auto-repeat, pause, frame time, name entry and restart."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Protocol

from tetris.highscores import Entry, HighScores, append_to_name, final_name

SHIFT_DELAY_MS = 170
SHIFT_INTERVAL_MS = 50
SOFT_DROP_INTERVAL_MS = 50
MAX_FRAME_MS = 100


class Key(Enum):
    LEFT = "left"
    RIGHT = "right"
    DOWN = "down"
    HARD_DROP = "hard_drop"
    ROTATE_CW = "rotate_cw"
    ROTATE_CCW = "rotate_ccw"
    PAUSE = "pause"
    RESTART = "restart"
    BACKSPACE = "backspace"


class Phase(Enum):
    PLAYING = "playing"
    NAME_ENTRY = "name_entry"  # the result made the high score table
    TABLE = "table"  # showing the table, Enter starts a new game


class GameLike(Protocol):
    is_over: bool
    score: int
    lines: int
    level: int

    def move_left(self) -> object: ...
    def move_right(self) -> object: ...
    def rotate_cw(self) -> object: ...
    def rotate_ccw(self) -> object: ...
    def step_down(self) -> object: ...
    def hard_drop(self) -> object: ...
    def tick(self, dt_ms: int) -> None: ...
    def new_game(self) -> None: ...


class KeyRepeater:
    """Counts repeats of a held key: the first after delay_ms, then every interval_ms."""

    def __init__(self, delay_ms: int, interval_ms: int) -> None:
        self._delay = delay_ms
        self._interval = interval_ms
        self._held = False
        self._elapsed = 0
        self._next = 0

    @property
    def held(self) -> bool:
        return self._held

    def press(self) -> None:
        self._held = True
        self._elapsed = 0
        self._next = self._delay

    def release(self) -> None:
        self._held = False

    def update(self, dt_ms: int) -> int:
        """Advance the hold time and return how many repeats fell due."""
        if not self._held:
            return 0
        self._elapsed += dt_ms
        repeats = 0
        while self._elapsed >= self._next:
            repeats += 1
            self._next += self._interval
        return repeats


class Controller:
    """Turns key presses and frame time into commands on the game."""

    def __init__(
        self,
        game: GameLike,
        scores: HighScores | None = None,
        on_save: Callable[[HighScores], object] | None = None,
    ) -> None:
        self.game = game
        self.scores = scores if scores is not None else HighScores()
        self._on_save = on_save
        self.paused = False
        self.name = ""  # the name being typed in NAME_ENTRY
        self.highlight: int | None = None  # table place of this game's result
        self._phase = Phase.PLAYING
        self._shift = KeyRepeater(SHIFT_DELAY_MS, SHIFT_INTERVAL_MS)
        self._shift_key: Key | None = None  # the horizontal key that repeats
        self._drop = KeyRepeater(SOFT_DROP_INTERVAL_MS, SOFT_DROP_INTERVAL_MS)

    @property
    def phase(self) -> Phase:
        self._check_game_over()
        return self._phase

    @property
    def playing(self) -> bool:
        return self.phase is Phase.PLAYING and not self.paused

    def key_down(self, key: Key) -> None:
        phase = self.phase
        if phase is Phase.NAME_ENTRY:
            if key is Key.RESTART:
                self._confirm_name()
            elif key is Key.BACKSPACE:
                self.name = self.name[:-1]
            return
        if phase is Phase.TABLE:
            if key is Key.RESTART:
                self.game.new_game()
                self.highlight = None
                self._phase = Phase.PLAYING
            return
        if key is Key.PAUSE:
            self.paused = not self.paused
            self._release_all()
            return
        if not self.playing:
            return
        if key in (Key.LEFT, Key.RIGHT):
            self._shift_key = key
            self._shift.press()
            self._shift_once()
        elif key is Key.DOWN:
            self._drop.press()
            self.game.step_down()
        elif key is Key.HARD_DROP:
            self.game.hard_drop()
        elif key is Key.ROTATE_CW:
            self.game.rotate_cw()
        elif key is Key.ROTATE_CCW:
            self.game.rotate_ccw()
        self._check_game_over()

    def text_input(self, text: str) -> None:
        """Typed characters; they only matter while entering a record name."""
        if self.phase is Phase.NAME_ENTRY:
            self.name = append_to_name(self.name, text)

    def key_up(self, key: Key) -> None:
        if key is self._shift_key:
            self._shift.release()
            self._shift_key = None
        elif key is Key.DOWN:
            self._drop.release()

    def update(self, frame_ms: int) -> None:
        """Apply held-key repeats, then pass the (capped) frame time to the game."""
        if not self.playing:
            return
        for _ in range(self._shift.update(frame_ms)):
            self._shift_once()
        for _ in range(self._drop.update(frame_ms)):
            if self.game.is_over:
                return
            self.game.step_down()
        if not self.game.is_over:
            self.game.tick(min(frame_ms, MAX_FRAME_MS))
        self._check_game_over()

    def _shift_once(self) -> None:
        if self._shift_key is Key.LEFT:
            self.game.move_left()
        elif self._shift_key is Key.RIGHT:
            self.game.move_right()

    def _check_game_over(self) -> None:
        """Leave PLAYING once the game is over: ask for a name or show the table."""
        if self._phase is not Phase.PLAYING or not self.game.is_over:
            return
        self.paused = False
        self._release_all()
        self.name = ""
        if self.scores.qualifies(self.game.score):
            self._phase = Phase.NAME_ENTRY
        else:
            self._phase = Phase.TABLE

    def _confirm_name(self) -> None:
        game = self.game
        entry = Entry(final_name(self.name), game.score, game.lines, game.level)
        self.highlight = self.scores.add(entry)
        if self._on_save is not None:
            self._on_save(self.scores)
        self._phase = Phase.TABLE

    def _release_all(self) -> None:
        self._shift.release()
        self._shift_key = None
        self._drop.release()
