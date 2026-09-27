"""Keyboard input rules without pygame: the splash and help screens, auto-repeat,
pause, frame time, name entry, restart, sound settings and each frame's sound events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from enum import Enum
from typing import Protocol

from tetris.highscores import Entry, HighScores, append_to_name, final_name
from tetris_ui.settings import Settings

SHIFT_DELAY_MS = 170
SHIFT_INTERVAL_MS = 50
SOFT_DROP_INTERVAL_MS = 50
MAX_FRAME_MS = 100


class Key(Enum):
    """Game actions produced by the keyboard; app.KEY_MAP maps pygame keys to them."""

    LEFT = "left"
    RIGHT = "right"
    DOWN = "down"
    HARD_DROP = "hard_drop"
    HOLD = "hold"
    ROTATE_CW = "rotate_cw"
    ROTATE_CCW = "rotate_ccw"
    PAUSE = "pause"
    RESTART = "restart"
    BACKSPACE = "backspace"
    TOGGLE_MUSIC = "toggle_music"
    TOGGLE_SOUND = "toggle_sound"
    VOLUME_DOWN = "volume_down"
    VOLUME_UP = "volume_up"
    SFX_DOWN = "sfx_down"
    SFX_UP = "sfx_up"
    HELP = "help"


# Keys that change the sound settings; they work everywhere except name entry.
SETTINGS_KEYS = (
    Key.TOGGLE_MUSIC,
    Key.TOGGLE_SOUND,
    Key.VOLUME_DOWN,
    Key.VOLUME_UP,
    Key.SFX_DOWN,
    Key.SFX_UP,
)


class Sound(Enum):
    """Sound effects; the values name the synthesized effects."""

    MOVE = "move"
    ROTATE = "rotate"
    LOCK = "lock"
    CLEAR = "clear"
    TETRIS = "tetris"
    LEVEL_UP = "level_up"
    GAME_OVER = "game_over"
    HOLD = "hold"


class Phase(Enum):
    """What the screen is for: the start screen, a game in progress, or after game over."""

    SPLASH = "splash"  # the start screen with the key list, Enter starts the game
    PLAYING = "playing"
    NAME_ENTRY = "name_entry"  # the result made the high score table
    TABLE = "table"  # showing the table, Enter starts a new game


class GameLike(Protocol):
    """The part of tetris.game.Game the controller uses; tests pass a recording fake."""

    is_over: bool
    score: int
    lines: int
    level: int
    pieces_locked: int

    def move_left(self) -> object:
        """Shift the active piece left; truthy if it moved."""

    def move_right(self) -> object:
        """Shift the active piece right; truthy if it moved."""

    def rotate_cw(self) -> object:
        """Rotate the active piece clockwise; truthy if it turned."""

    def rotate_ccw(self) -> object:
        """Rotate the active piece counterclockwise; truthy if it turned."""

    def step_down(self) -> object:
        """Soft drop by one row; a lying piece is left to the lock delay."""

    def hard_drop(self) -> object:
        """Drop the active piece to the bottom and lock it."""

    def hold(self) -> object:
        """Put the active piece in the hold slot; truthy if it was allowed."""

    def tick(self, dt_ms: int) -> None:
        """Let dt_ms milliseconds of gravity pass."""

    def new_game(self) -> None:
        """Start a new game."""


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
        """Whether the key is being held down."""
        return self._held

    def press(self) -> None:
        """Start timing the repeats from the moment the key went down."""
        self._held = True
        self._elapsed = 0
        self._next = self._delay

    def release(self) -> None:
        """Stop repeating until the key is pressed again."""
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
    """Turns key presses and frame time into commands on the game.

    `scores` is the high score table, and `on_save` is called with it after a new
    record is entered. `settings` are the sound settings, and `on_settings_change` is
    called with the new settings after every change. With `splash=True` the controller
    starts on the splash screen instead of in a running game.
    """

    def __init__(
        self,
        game: GameLike,
        scores: HighScores | None = None,
        on_save: Callable[[HighScores], object] | None = None,
        settings: Settings | None = None,
        on_settings_change: Callable[[Settings], object] | None = None,
        splash: bool = False,
    ) -> None:
        self.game = game
        self.scores = scores if scores is not None else HighScores()
        self._on_save = on_save
        self.settings = settings if settings is not None else Settings()
        self._on_settings_change = on_settings_change
        self.paused = False
        self.help_open = False  # the key list opened with F1; the game stays paused under it
        self.name = ""  # the name being typed in NAME_ENTRY
        self.highlight: int | None = None  # table place of this game's result
        self._phase = Phase.SPLASH if splash else Phase.PLAYING
        # Grows whenever the music must start over (new game, music switched on).
        self.music_generation = 0
        self._sounds: dict[Sound, None] = {}  # this frame's sounds, ordered, no repeats
        self._shift = KeyRepeater(SHIFT_DELAY_MS, SHIFT_INTERVAL_MS)
        self._shift_key: Key | None = None  # the horizontal key that repeats
        self._drop = KeyRepeater(SOFT_DROP_INTERVAL_MS, SOFT_DROP_INTERVAL_MS)

    @property
    def phase(self) -> Phase:
        """The current phase; the switch away from PLAYING happens here once the game is over."""
        self._check_game_over()
        return self._phase

    @property
    def playing(self) -> bool:
        """Whether the game is running: a game is in progress and it is not paused."""
        return self.phase is Phase.PLAYING and not self.paused

    @property
    def music_on(self) -> bool:
        """Whether the music is switched on."""
        return self.settings.music_on

    @property
    def sound_on(self) -> bool:
        """Whether the sound effects are switched on."""
        return self.settings.sound_on

    @property
    def music_volume(self) -> int:
        """Music volume in percent, 0-100."""
        return self.settings.music_volume

    @property
    def music_state(self) -> str:
        """What the music should do now: "playing", "paused" or "stopped"."""
        if not self.music_on or self.phase is not Phase.PLAYING:
            return "stopped"
        return "paused" if self.paused else "playing"

    def drain_sounds(self) -> list[Sound]:
        """The sound events since the last call, each at most once."""
        sounds = list(self._sounds)
        self._sounds.clear()
        return sounds

    def key_down(self, key: Key) -> None:
        """Handle a key press according to the current phase.

        Sound settings keys work everywhere except during name entry. The splash waits for
        Enter; the help screen closes on F1, Esc, P or Enter; during play the key moves,
        rotates or drops the piece, pauses or opens the help screen.
        """
        phase = self.phase
        if key in SETTINGS_KEYS and phase is not Phase.NAME_ENTRY:
            self._change_settings(key)
            return
        if phase is Phase.SPLASH:
            if key is Key.RESTART:
                self._phase = Phase.PLAYING
            return
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
                self.music_generation += 1
            return
        if self.help_open:
            if key in (Key.HELP, Key.PAUSE, Key.RESTART):
                self.help_open = False
                self.paused = False
                self._release_all()
            return
        if key is Key.HELP:
            self.help_open = True
            self.paused = True
            self._release_all()
            return
        if key is Key.PAUSE:
            self.paused = not self.paused
            self._release_all()
            return
        if not self.playing:
            return
        before = self._snapshot()
        if key in (Key.LEFT, Key.RIGHT):
            self._shift_key = key
            self._shift.press()
            self._shift_once()
        elif key is Key.DOWN:
            self._drop.press()
            self.game.step_down()
        elif key is Key.HARD_DROP:
            self.game.hard_drop()
        elif key is Key.HOLD:
            self._sound_if(self.game.hold(), Sound.HOLD)
        elif key is Key.ROTATE_CW:
            self._sound_if(self.game.rotate_cw(), Sound.ROTATE)
        elif key is Key.ROTATE_CCW:
            self._sound_if(self.game.rotate_ccw(), Sound.ROTATE)
        self._record_changes(before)
        self._check_game_over()

    def text_input(self, text: str) -> None:
        """Typed characters; they only matter while entering a record name."""
        if self.phase is Phase.NAME_ENTRY:
            self.name = append_to_name(self.name, text)

    def key_up(self, key: Key) -> None:
        """Handle a key release: stop the auto-repeat of that key."""
        if key is self._shift_key:
            self._shift.release()
            self._shift_key = None
        elif key is Key.DOWN:
            self._drop.release()

    def update(self, frame_ms: int) -> None:
        """Apply held-key repeats, then pass the (capped) frame time to the game."""
        if not self.playing:
            return
        before = self._snapshot()
        for _ in range(self._shift.update(frame_ms)):
            self._shift_once()
        for _ in range(self._drop.update(frame_ms)):
            if self.game.is_over:
                break
            self.game.step_down()
        if not self.game.is_over:
            self.game.tick(min(frame_ms, MAX_FRAME_MS))
        self._record_changes(before)
        self._check_game_over()

    def _shift_once(self) -> None:
        """Shift the piece once toward the held direction, recording a move sound."""
        if self._shift_key is Key.LEFT:
            self._sound_if(self.game.move_left(), Sound.MOVE)
        elif self._shift_key is Key.RIGHT:
            self._sound_if(self.game.move_right(), Sound.MOVE)

    def _change_settings(self, key: Key) -> None:
        """Apply a sound settings key and report the new settings if they changed."""
        old = self.settings
        if key is Key.TOGGLE_SOUND:
            new = replace(old, sound_on=not old.sound_on)
        elif key is Key.TOGGLE_MUSIC:
            new = replace(old, music_on=not old.music_on)
        elif key is Key.VOLUME_UP:
            new = old.with_volume_step(1)
        elif key is Key.SFX_UP:
            new = old.with_sfx_volume_step(1)
        elif key is Key.SFX_DOWN:
            new = old.with_sfx_volume_step(-1)
        else:
            new = old.with_volume_step(-1)
        if new == old:
            return
        self.settings = new
        if new.music_on and not old.music_on:
            self.music_generation += 1  # switching music on starts it over
        if self._on_settings_change is not None:
            self._on_settings_change(new)

    def _snapshot(self) -> tuple[int, int, int, bool]:
        """The game counters that sound events are derived from."""
        game = self.game
        return game.pieces_locked, game.lines, game.level, game.is_over

    def _record_changes(self, before: tuple[int, int, int, bool]) -> None:
        """Turn what changed in the game since `before` into sound events."""
        locked, lines, level, was_over = before
        game = self.game
        if game.pieces_locked > locked:
            cleared = game.lines - lines
            if cleared >= 4:
                self._sounds[Sound.TETRIS] = None
            elif cleared > 0:
                self._sounds[Sound.CLEAR] = None
            else:
                self._sounds[Sound.LOCK] = None
        if game.level > level:
            self._sounds[Sound.LEVEL_UP] = None
        if game.is_over and not was_over:
            self._sounds[Sound.GAME_OVER] = None

    def _sound_if(self, done: object, sound: Sound) -> None:
        """Record `sound` for this frame if `done` is truthy."""
        if done:
            self._sounds[sound] = None

    def _check_game_over(self) -> None:
        """Leave PLAYING once the game is over: ask for a name or show the table."""
        if self._phase is not Phase.PLAYING or not self.game.is_over:
            return
        self.paused = False
        self.help_open = False
        self._release_all()
        self.name = ""
        if self.scores.qualifies(self.game.score):
            self._phase = Phase.NAME_ENTRY
        else:
            self._phase = Phase.TABLE

    def _confirm_name(self) -> None:
        """Save this game's result under the typed name and show the table."""
        game = self.game
        entry = Entry(final_name(self.name), game.score, game.lines, game.level)
        self.highlight = self.scores.add(entry)
        if self._on_save is not None:
            self._on_save(self.scores)
        self._phase = Phase.TABLE

    def _release_all(self) -> None:
        """Forget held keys, so nothing repeats until they are pressed again."""
        self._shift.release()
        self._shift_key = None
        self._drop.release()
