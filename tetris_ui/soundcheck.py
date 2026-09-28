"""The sound check without pygame: every sound of the game, alone and in the combinations
heard during play, listened to one by one so that the unpleasant ones can be marked.

Each item is a schedule of cues: (milliseconds after the item starts, what to play). A cue
is the name of one of synth.EFFECTS or MUSIC, the background melody; audio plays them with
the same pygame sounds as the game. Titles and descriptions are English keys of texts.RU,
like every other fixed text.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from tetris_ui import menus

MUSIC = "music"  # the cue of the background melody; every other cue names a synth effect
AUTOREPEAT_MOVES = 7  # a three-cell piece held from one wall to the other
REPORT_VERSION = 1

Cue = tuple[int, str]  # (ms after the item starts, effect name or MUSIC)


@dataclass(frozen=True)
class CheckItem:
    """One item of the sound check: its id in the report, what the screen shows and what
    it plays."""

    id: str
    title: str
    description: str
    cues: tuple[Cue, ...]


def _together(*cues: str) -> tuple[Cue, ...]:
    """Cues that all start at the moment the item starts."""
    return tuple((0, cue) for cue in cues)


def _held_shift(effect: str, moves: int) -> tuple[Cue, ...]:
    """`moves` cues of `effect` timed like a held shift key at the Normal autorepeat speed:
    the first at once, the second after the delay, the rest one interval apart."""
    delay, interval = menus.AUTOREPEAT["normal"]
    return _together(effect) + tuple((delay + k * interval, effect) for k in range(moves - 1))


ITEMS: tuple[CheckItem, ...] = (
    CheckItem("move", "Move", "Piece moved left or right", _together("move")),
    CheckItem("rotate", "Rotate", "Piece turned", _together("rotate")),
    CheckItem("hold", "Hold piece", "Piece put on hold", _together("hold")),
    CheckItem("lock", "Lock", "Piece locked, no lines cleared", _together("lock")),
    CheckItem("clear", "Line clear", "One to three lines cleared", _together("clear")),
    CheckItem("tetris", "Tetris", "Four lines cleared at once", _together("tetris")),
    CheckItem("level_up", "Level up", "Level went up", _together("level_up")),
    CheckItem("game_over", "Game over", "Game ended", _together("game_over")),
    CheckItem("move_repeat", "Move with autorepeat", "Key held: 7 moves wall to wall",
              _held_shift("move", AUTOREPEAT_MOVES)),
    CheckItem("clear_level_up", "Clear + level up", "Lines cleared, level went up",
              _together("clear", "level_up")),
    CheckItem("tetris_level_up", "Tetris + level up", "Tetris, level went up",
              _together("tetris", "level_up")),
    CheckItem("lock_game_over", "Lock + game over", "Last piece locked, game over",
              _together("lock", "game_over")),
    CheckItem("music", "Music", "Background melody in a loop", _together(MUSIC)),
)


class CheckKey(Enum):
    """Keys of the sound check; app.SOUND_CHECK_KEYS maps pygame keys to them."""

    UP = "up"  # the previous item
    DOWN = "down"  # the next item
    PLAY = "play"  # the selected item once more (Space, Enter)
    MARK = "mark"  # mark or unmark the selected item as unpleasant (X)
    EXIT = "exit"  # end the check (Esc)


@dataclass(frozen=True)
class Playback:
    """What the sound does in one frame: stop everything first if `stop`, then start `cues`."""

    stop: bool = False
    cues: tuple[str, ...] = ()


class SoundCheck:
    """The sound check: the selected item, the marks and when each sound starts.

    Selecting an item starts it over: the next update() stops everything that sounds and
    starts the item's first cues. The check starts with the first item selected. Without
    a sound device (`can_play` False) nothing counts as played. `on_report` gets the
    report text when the check starts and after every change to it: an item heard for
    the first time, a mark set or removed.
    """

    def __init__(
        self, can_play: bool = True, on_report: Callable[[str], object] | None = None
    ) -> None:
        self._can_play = can_play
        self._on_report = on_report
        self.index = 0  # the selected item of ITEMS
        self.marked = [False] * len(ITEMS)  # marked as unpleasant
        self.played = [False] * len(ITEMS)  # heard at least once in this check
        self.exit_requested = False  # Esc was pressed
        self._clock = 0  # ms since the selected item started
        self._pending: list[Cue] = []  # cues of the selected item that have not started
        self._restarted = False  # the item started over since the last update()
        self._start(0, report=False)
        self._report()  # a new report replaces the one of the last check

    @property
    def item(self) -> CheckItem:
        """The selected item."""
        return ITEMS[self.index]

    def key_down(self, key: CheckKey) -> None:
        """Handle a key press: choose, replay or mark an item, or end the check.

        Up on the first item and Down on the last do nothing, so the sound goes on.
        """
        if key is CheckKey.DOWN and self.index < len(ITEMS) - 1:
            self._start(self.index + 1)
        elif key is CheckKey.UP and self.index > 0:
            self._start(self.index - 1)
        elif key is CheckKey.PLAY:
            self._start(self.index)
        elif key is CheckKey.MARK:
            self.marked[self.index] = not self.marked[self.index]
            self._report()
        elif key is CheckKey.EXIT:
            self.exit_requested = True

    def update(self, dt_ms: int) -> Playback:
        """Let dt_ms pass on the selected item's clock and say what to play in this frame.

        The frame in which the item started is its moment 0, however long that frame
        was. Cues whose time has come start now, each effect at most once per frame as in
        the game: another cue of the same effect due in the same frame is dropped.
        """
        stop = self._restarted
        if self._restarted:
            self._restarted = False
        else:
            self._clock += dt_ms
        cues: list[str] = []
        while self._pending and self._pending[0][0] <= self._clock:
            _, cue = self._pending.pop(0)
            if cue not in cues:
                cues.append(cue)
        return Playback(stop, tuple(cues))

    def report_json(self) -> str:
        """The report kept in sound-check.json: every item, whether it was heard and
        whether it is marked as unpleasant."""
        items = [
            {"number": number, "id": item.id, "played": played, "unpleasant": marked}
            for number, (item, played, marked)
            in enumerate(zip(ITEMS, self.played, self.marked), start=1)
        ]
        return json.dumps({"version": REPORT_VERSION, "items": items}, indent=2)

    def _start(self, index: int, report: bool = True) -> None:
        """Select an item and play it from the beginning, dropping what is still due.

        An item heard for the first time changes the report.
        """
        self.index = index
        self._clock = 0
        self._pending = sorted(ITEMS[index].cues, key=lambda cue: cue[0])
        self._restarted = True
        if self._can_play and not self.played[index]:
            self.played[index] = True
            if report:
                self._report()

    def _report(self) -> None:
        """Hand the current report to on_report."""
        if self._on_report is not None:
            self._on_report(self.report_json())
