"""Keyboard input rules without pygame: the main menu and its screens, the help screen,
the guide, auto-repeat, the pause menu, frame time, name entry, restart, settings and each
frame's sound events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from enum import Enum
from typing import Protocol

from tetris.highscores import Entry, HighScores, append_to_name, final_name
from tetris_ui import guide, menus
from tetris_ui.settings import Settings

SOFT_DROP_INTERVAL_MS = 50
MAX_FRAME_MS = 100


class Key(Enum):
    """Game actions produced by the keyboard; app.KEY_MAP maps pygame keys to them."""

    LEFT = "left"
    RIGHT = "right"
    UP = "up"  # rotates clockwise during play, moves the selection in menus
    DOWN = "down"
    HARD_DROP = "hard_drop"
    HOLD = "hold"
    ROTATE_CW = "rotate_cw"
    ROTATE_CCW = "rotate_ccw"
    PAUSE = "pause"
    ESCAPE = "escape"  # pauses during play, goes back in menus
    RESTART = "restart"  # Enter
    BACKSPACE = "backspace"
    TOGGLE_MUSIC = "toggle_music"
    TOGGLE_SOUND = "toggle_sound"
    VOLUME_DOWN = "volume_down"
    VOLUME_UP = "volume_up"
    SFX_DOWN = "sfx_down"
    SFX_UP = "sfx_up"
    HELP = "help"
    GUIDE = "guide"  # F2


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
    """What the screen is for: the main menu or one of its screens, a game in progress,
    or after game over."""

    MENU = "menu"  # the main menu shown at launch
    SCORES = "scores"  # the high score table opened from the menu
    SETTINGS = "settings"  # the settings screen
    CONTROLS = "controls"  # the key list opened from the menu
    PLAYING = "playing"
    NAME_ENTRY = "name_entry"  # the result made the high score table
    TABLE = "table"  # showing the table, Enter starts a new game, Esc opens the menu


# The main menu and the screens opened from it; the game stands still on all of them.
MENU_PHASES = (Phase.MENU, Phase.SCORES, Phase.SETTINGS, Phase.CONTROLS)


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

    def new_game(self, start_level: int = 0) -> None:
        """Start a new game at start_level."""


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
    record is entered. `settings` are the player's settings, and `on_settings_change` is
    called with the new settings after every change. With `start_in_menu=True` the
    controller starts in the main menu instead of in a running game.
    """

    def __init__(
        self,
        game: GameLike,
        scores: HighScores | None = None,
        on_save: Callable[[HighScores], object] | None = None,
        settings: Settings | None = None,
        on_settings_change: Callable[[Settings], object] | None = None,
        start_in_menu: bool = False,
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
        self.menu_index = 0  # selected item of menus.MAIN_ITEMS
        self.pause_index = 0  # selected item of menus.PAUSE_ITEMS
        self.settings_index = 0  # selected settings row; the last one is Back
        self.quit_requested = False  # Quit was chosen in the main menu
        self.guide_open = False  # the guide (F2) covers whatever screen is under it
        self.guide_page = 0  # 0-based page of the guide
        self._phase = Phase.MENU if start_in_menu else Phase.PLAYING
        # Grows whenever the music must start over (new game, music switched on).
        self.music_generation = 0
        self._sounds: dict[Sound, None] = {}  # this frame's sounds, ordered, no repeats
        self._shift = self._make_shift_repeater()
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

        Sound settings keys work everywhere except during name entry. The open guide takes
        its keys before the screen under it does; F2 opens it in the menu, on the menu's
        screens and in a game. The menu and its screens are handled by _menu_key(); after
        game over Enter starts a new game and Esc opens the menu; the help screen closes
        on F1, Esc, P or Enter; the pause menu takes Up, Down and Enter; during play the
        key moves, rotates or drops the piece, pauses or opens the help screen.
        """
        phase = self.phase
        if key in SETTINGS_KEYS and phase is not Phase.NAME_ENTRY:
            self._change_settings(key)
            return
        if self.guide_open:
            self._guide_key(key)
            return
        if key is Key.GUIDE:
            if phase in MENU_PHASES or (phase is Phase.PLAYING and not self.help_open):
                self._open_guide()
            return  # ignored after game over and on the help screen
        if phase in MENU_PHASES:
            self._menu_key(phase, key)
            return
        if phase is Phase.NAME_ENTRY:
            if key is Key.RESTART:
                self._confirm_name()
            elif key is Key.BACKSPACE:
                self.name = self.name[:-1]
            return
        if phase is Phase.TABLE:
            if key is Key.RESTART:
                self._start_game()
            elif key is Key.ESCAPE:
                self._open_menu()
            return
        if self.help_open:
            if key in (Key.HELP, Key.PAUSE, Key.ESCAPE, Key.RESTART):
                self.help_open = False
                self.paused = False
                self._release_all()
            return
        if key is Key.HELP:
            self.help_open = True
            self.paused = True
            self._release_all()
            return
        if key in (Key.PAUSE, Key.ESCAPE):
            self.paused = not self.paused
            self.pause_index = 0
            self._release_all()
            return
        if self.paused:
            self._pause_key(key)
            return
        if key is Key.UP:
            key = Key.ROTATE_CW
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

    def _menu_key(self, phase: Phase, key: Key) -> None:
        """Handle a key in the main menu or on one of its screens."""
        if phase is Phase.MENU:
            if key in (Key.UP, Key.DOWN):
                step = -1 if key is Key.UP else 1
                self.menu_index = (self.menu_index + step) % len(menus.MAIN_ITEMS)
            elif key is Key.RESTART:
                self._choose(menus.MAIN_ITEMS[self.menu_index])
        elif phase is Phase.SETTINGS:
            self._settings_key(key)
        elif key in (Key.RESTART, Key.ESCAPE):  # the high scores and the key list
            self._open_menu()

    def _choose(self, item: str) -> None:
        """Do what the chosen main menu item stands for."""
        if item == menus.NEW_GAME:
            self._start_game()
        elif item == menus.HIGH_SCORES:
            self._phase = Phase.SCORES
        elif item == menus.SETTINGS:
            self.settings_index = 0
            self._phase = Phase.SETTINGS
        elif item == menus.CONTROLS:
            self._phase = Phase.CONTROLS
        elif item == menus.GUIDE:
            self._open_guide()
        elif item == menus.QUIT:
            self.quit_requested = True

    def _settings_key(self, key: Key) -> None:
        """Handle a key on the settings screen: choose a row, change it or go back."""
        on_back = self.settings_index == len(menus.SETTING_ROWS)
        if key in (Key.UP, Key.DOWN):
            step = -1 if key is Key.UP else 1
            self.settings_index = (self.settings_index + step) % menus.SETTINGS_ROW_COUNT
        elif key is Key.ESCAPE or (key is Key.RESTART and on_back):
            self._open_menu()
        elif key in (Key.LEFT, Key.RIGHT, Key.RESTART) and not on_back:
            row = menus.SETTING_ROWS[self.settings_index]
            steps = -1 if key is Key.LEFT else 1
            self._apply_settings(menus.step_setting(self.settings, row, steps))

    def _pause_key(self, key: Key) -> None:
        """Handle a key in the pause menu: choose Continue or Main menu."""
        if key in (Key.UP, Key.DOWN):
            step = -1 if key is Key.UP else 1
            self.pause_index = (self.pause_index + step) % len(menus.PAUSE_ITEMS)
        elif key is Key.RESTART:
            if menus.PAUSE_ITEMS[self.pause_index] == menus.CONTINUE:
                self.paused = False
            else:
                self._open_menu()  # the unfinished game is dropped, nothing is recorded

    def _open_guide(self) -> None:
        """Show the guide from its first page; a game under it is paused."""
        self.guide_open = True
        self.guide_page = 0
        if self._phase is Phase.PLAYING:
            self.paused = True
            self.pause_index = 0
            self._release_all()

    def _guide_key(self, key: Key) -> None:
        """Handle a key while the guide is open: turn a page or close the guide."""
        if key is Key.LEFT:
            self.guide_page = max(0, self.guide_page - 1)
        elif key is Key.RIGHT:
            self.guide_page = min(guide.PAGE_COUNT - 1, self.guide_page + 1)
        elif key in (Key.ESCAPE, Key.RESTART, Key.GUIDE):
            self._close_guide()

    def _close_guide(self) -> None:
        """Close the guide and show the screen under it; the main menu opens afresh with
        New game selected, and a game stays paused."""
        self.guide_open = False
        if self._phase is Phase.MENU:
            self._open_menu()

    def _start_game(self) -> None:
        """Start a new game at the chosen start level; the music starts over."""
        self.game.new_game(self.settings.start_level)
        self.highlight = None
        self.paused = False
        self.help_open = False
        self.guide_open = False
        self._release_all()
        self._phase = Phase.PLAYING
        self.music_generation += 1

    def _open_menu(self) -> None:
        """Show the main menu with New game selected."""
        self.menu_index = 0
        self.highlight = None
        self.paused = False
        self.help_open = False
        self.guide_open = False
        self._release_all()
        self._phase = Phase.MENU

    def _make_shift_repeater(self) -> KeyRepeater:
        """A repeater for Left and Right with the delay and interval of the chosen speed."""
        return KeyRepeater(*menus.AUTOREPEAT[self.settings.autorepeat])

    def _change_settings(self, key: Key) -> None:
        """Apply a sound settings key."""
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
        self._apply_settings(new)

    def _apply_settings(self, new: Settings) -> None:
        """Switch to new settings and report them, if they differ from the current ones."""
        old = self.settings
        if new == old:
            return
        self.settings = new
        if new.music_on and not old.music_on:
            self.music_generation += 1  # switching music on starts it over
        if new.autorepeat != old.autorepeat:
            self._shift = self._make_shift_repeater()
            self._shift_key = None
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
