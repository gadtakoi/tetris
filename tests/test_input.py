import pytest

from tests.helpers import ScriptedRng
from tetris.game import Game
from tetris.pieces import PieceType
from tetris.highscores import Entry, HighScores
from tetris_ui.input import Controller, Key, KeyRepeater, Phase, Sound
from tetris_ui.settings import Settings
from tetris_ui.layout import (
    HIGHLIGHT,
    TEXT,
    cell_rect,
    key_screen,
    key_screen_texts,
    overlay_lines,
    overlay_texts,
    screen_texts,
)


class FakeGame:
    """Records the commands the controller sends."""

    def __init__(self) -> None:
        self.is_over = False
        self.score = self.lines = self.level = self.pieces_locked = 0
        self.held_type = None
        self.can_hold = True
        self.calls: list[str] = []
        self.ticks: list[int] = []

    def move_left(self):
        self.calls.append("left")

    def move_right(self):
        self.calls.append("right")

    def rotate_cw(self):
        self.calls.append("cw")

    def rotate_ccw(self):
        self.calls.append("ccw")

    def step_down(self):
        self.calls.append("down")

    def hard_drop(self):
        self.calls.append("hard_drop")

    def hold(self):
        self.calls.append("hold")

    def new_game(self):
        self.calls.append("new_game")
        self.is_over = False

    def tick(self, dt_ms):
        self.ticks.append(dt_ms)


def frames(controller: Controller, total_ms: int, frame_ms: int = 16) -> None:
    while total_ms > 0:
        step = min(frame_ms, total_ms)
        controller.update(step)
        total_ms -= step


@pytest.fixture
def game() -> FakeGame:
    return FakeGame()


@pytest.fixture
def controller(game) -> Controller:
    return Controller(game)


# --- KeyRepeater -----------------------------------------------------------


def test_shift_repeater_waits_for_delay():
    repeater = KeyRepeater(170, 50)
    repeater.press()
    assert repeater.update(169) == 0


@pytest.mark.parametrize("frame_ms", [16, 270])
def test_shift_repeater_repeats_every_interval(frame_ms):
    repeater = KeyRepeater(170, 50)
    repeater.press()
    repeats, elapsed = 0, 0
    while elapsed < 270:
        step = min(frame_ms, 270 - elapsed)
        repeats += repeater.update(step)
        elapsed += step
    assert repeats == 3  # at 170, 220 and 270 ms


def test_soft_drop_repeater():
    repeater = KeyRepeater(50, 50)
    repeater.press()
    assert repeater.update(120) == 2  # at 50 and 100 ms


def test_released_repeater_stays_quiet():
    repeater = KeyRepeater(170, 50)
    repeater.press()
    repeater.release()
    assert repeater.update(1000) == 0


# --- Keys and auto-repeat --------------------------------------------------


def test_left_key_moves_once(controller, game):
    controller.key_down(Key.LEFT)
    assert game.calls == ["left"]


def test_two_rotation_presses(controller, game):
    controller.key_down(Key.ROTATE_CW)
    controller.key_up(Key.ROTATE_CW)
    controller.key_down(Key.ROTATE_CW)
    assert game.calls == ["cw", "cw"]


def test_ccw_rotation(controller, game):
    controller.key_down(Key.ROTATE_CCW)
    assert game.calls == ["ccw"]


def test_short_press(controller, game):
    controller.key_down(Key.LEFT)
    frames(controller, 169)
    controller.key_up(Key.LEFT)
    frames(controller, 500)
    assert game.calls == ["left"]


def test_hold_repeats_shift(controller, game):
    controller.key_down(Key.LEFT)
    frames(controller, 270, frame_ms=10)
    assert game.calls == ["left"] * 4


def test_last_pressed_direction_wins(controller, game):
    controller.key_down(Key.LEFT)
    frames(controller, 100, frame_ms=10)
    controller.key_down(Key.RIGHT)
    frames(controller, 170, frame_ms=10)
    assert game.calls == ["left", "right", "right"]


def test_releasing_last_direction_stops_repeat(controller, game):
    controller.key_down(Key.LEFT)
    controller.key_down(Key.RIGHT)
    controller.key_up(Key.RIGHT)
    frames(controller, 500)
    assert game.calls == ["left", "right"]


def test_long_frame_fires_several_repeats(controller, game):
    controller.key_down(Key.RIGHT)
    controller.update(270)
    assert game.calls == ["right"] * 4


def test_hold_soft_drop(controller, game):
    controller.key_down(Key.DOWN)
    controller.update(120)
    assert game.calls == ["down"] * 3


def test_space_hard_drops_once(controller, game):
    controller.key_down(Key.HARD_DROP)
    assert game.calls == ["hard_drop"]


def test_holding_space_does_not_repeat(controller, game):
    controller.key_down(Key.HARD_DROP)
    frames(controller, 1000)
    controller.key_up(Key.HARD_DROP)
    assert game.calls == ["hard_drop"]


def test_space_on_pause_does_nothing(controller, game):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.HARD_DROP)
    assert game.calls == []


def test_space_after_game_over_does_nothing(controller, game):
    game.is_over = True
    controller.key_down(Key.HARD_DROP)
    assert game.calls == []


def test_rotation_does_not_repeat(controller, game):
    controller.key_down(Key.ROTATE_CW)
    frames(controller, 1000)
    assert game.calls == ["cw"]


# --- Time, pause and restart -----------------------------------------------


def test_frame_time_is_passed_to_game(controller, game):
    controller.update(16)
    assert game.ticks == [16]


def test_long_frame_is_capped(controller, game):
    controller.update(2000)
    assert game.ticks == [100]


def test_pause_stops_the_game(controller, game):
    controller.key_down(Key.PAUSE)
    assert controller.paused
    frames(controller, 5000)
    controller.key_down(Key.LEFT)
    assert game.calls == []
    assert game.ticks == []


def test_unpause(controller, game):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.PAUSE)  # Esc maps to the same key
    assert not controller.paused
    controller.update(16)
    assert game.ticks == [16]


def test_held_key_does_not_repeat_after_pause(controller, game):
    controller.key_down(Key.LEFT)
    controller.key_down(Key.PAUSE)
    frames(controller, 1000)
    controller.key_down(Key.PAUSE)
    frames(controller, 500)
    assert game.calls == ["left"]


def test_no_pause_after_game_over(controller, game):
    game.is_over = True
    controller.key_down(Key.PAUSE)
    assert not controller.paused


def test_enter_during_play_does_nothing(controller, game):
    controller.key_down(Key.RESTART)
    assert game.calls == []


def test_game_over_ignores_keys_and_time(controller, game):
    game.is_over = True
    for key in (Key.LEFT, Key.RIGHT, Key.DOWN, Key.HARD_DROP, Key.ROTATE_CW, Key.ROTATE_CCW):
        controller.key_down(key)
    controller.update(16)
    assert game.calls == []
    assert game.ticks == []


def finished_game() -> Game:
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    return game


def test_enter_restarts_when_result_misses_the_table():
    game = finished_game()
    assert game.score == 0
    controller = Controller(game)
    assert controller.phase is Phase.TABLE
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.PLAYING
    assert not game.is_over
    assert (game.score, game.lines, game.level) == (0, 0, 0)
    assert all(cell is None for row in game.board.visible_rows() for cell in row)


def record_game(score: int = 340) -> Game:
    game = finished_game()
    game.score, game.lines, game.level = score, 3, 0
    return game


def test_name_entry_then_restart():
    saved = []
    game = record_game()
    controller = Controller(game, HighScores(), on_save=saved.append)
    assert controller.phase is Phase.NAME_ENTRY
    controller.text_input("Ann")
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.TABLE
    assert game.is_over  # the confirming Enter does not restart
    assert controller.scores.entries == (Entry("Ann", 340, 3, 0),)
    assert controller.highlight == 1
    assert saved == [controller.scores]
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.PLAYING
    assert not game.is_over
    assert controller.highlight is None


def test_backspace_in_name_entry():
    controller = Controller(record_game())
    controller.text_input("Annx")
    controller.key_down(Key.BACKSPACE)
    controller.key_down(Key.RESTART)
    assert controller.scores.entries[0].name == "Ann"


def test_control_letters_are_typed_in_name_entry():
    game = record_game()
    controller = Controller(game)
    for key, text in ((Key.ROTATE_CCW, "Z"), (Key.ROTATE_CW, "X"), (Key.PAUSE, "P")):
        controller.key_down(key)
        controller.text_input(text)
    assert controller.name == "ZXP"
    assert not controller.paused
    assert controller.phase is Phase.NAME_ENTRY


def test_text_is_ignored_outside_name_entry(controller):
    controller.text_input("abc")
    assert controller.name == ""


def test_empty_name_is_saved_as_player():
    controller = Controller(record_game())
    controller.key_down(Key.RESTART)
    assert controller.scores.entries[0].name == "PLAYER"


def test_game_over_during_play_switches_phase():
    game = Game(rng=ScriptedRng([PieceType.O]))
    controller = Controller(game)
    while controller.phase is Phase.PLAYING:
        controller.key_down(Key.HARD_DROP)
    assert game.is_over
    assert controller.phase is Phase.TABLE  # hard drops score nothing


def test_table_phase_ignores_control_keys():
    game = finished_game()
    controller = Controller(game)
    for key in (Key.PAUSE, Key.LEFT, Key.BACKSPACE):
        controller.key_down(key)
    assert controller.phase is Phase.TABLE
    assert not controller.paused


def test_enter_during_real_play_changes_nothing():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    active, next_type = game.active, game.next_type
    Controller(game).key_down(Key.RESTART)
    assert (game.active, game.next_type, game.is_over) == (active, next_type, False)


# --- Layout ----------------------------------------------------------------


def test_cell_rect():
    assert cell_rect(0, 2) == (20, 20, 30, 30)
    assert cell_rect(0, 21) == (20, 590, 30, 30)
    assert cell_rect(9, 21) == (290, 590, 30, 30)


def test_hidden_cells_have_no_rect():
    with pytest.raises(ValueError):
        cell_rect(0, 1)


def test_texts_during_play():
    controller = Controller(Game(seed=1))
    controller.game.score, controller.game.lines, controller.game.level = 1200, 13, 1
    assert screen_texts(controller) == [
        "NEXT", "HOLD", "SCORE", "1200", "LINES", "13", "LEVEL", "1",
        "MUSIC ON", "MUSIC 50%", "SOUND ON", "SOUND 100%",
    ]


def test_sound_indicators():
    controller = Controller(Game(seed=1))
    controller.key_down(Key.TOGGLE_MUSIC)
    texts = screen_texts(controller)
    assert "MUSIC OFF" in texts and "SOUND ON" in texts


def test_indicators_sit_below_the_counters():
    from tetris_ui.layout import panel_texts
    positions = dict(panel_texts(Controller(Game(seed=1))))
    for text in ("MUSIC ON", "MUSIC 50%", "SOUND ON", "SOUND 100%"):
        assert positions[text][1] >= 460


def test_volume_on_the_panel():
    controller = Controller(Game(seed=1))
    controller.key_down(Key.VOLUME_UP)
    controller.key_down(Key.VOLUME_UP)
    assert "MUSIC 70%" in screen_texts(controller)


def test_texts_on_pause():
    controller = Controller(Game(seed=1))
    controller.key_down(Key.PAUSE)
    assert screen_texts(controller)[-1] == "PAUSE"


def test_texts_game_over_without_record():
    table = HighScores()
    table.add(Entry("ANNA", 1200, 13, 1))
    controller = Controller(finished_game(), table)
    texts = screen_texts(controller)
    assert texts[texts.index("SCORE") + 1] == "0"
    assert overlay_texts(controller) == ["GAME OVER", "HIGH SCORES", "1. ANNA 1200", "Press Enter"]


def test_texts_name_entry():
    controller = Controller(record_game(340))
    controller.text_input("Ann")
    assert overlay_texts(controller) == ["GAME OVER", "NEW RECORD", "Name: Ann_"]
    assert "340" in screen_texts(controller)


def test_new_entry_is_highlighted():
    table = HighScores()
    table.add(Entry("ANNA", 1200, 13, 1))
    controller = Controller(record_game(340), table)
    controller.text_input("Ann")
    controller.key_down(Key.RESTART)
    lines = dict(overlay_lines(controller))
    assert lines["2. Ann 340"] == HIGHLIGHT
    assert lines["1. ANNA 1200"] == TEXT


def test_empty_table_text():
    controller = Controller(finished_game())
    assert overlay_texts(controller) == ["GAME OVER", "HIGH SCORES", "No records yet", "Press Enter"]


def test_texts_after_restart():
    controller = Controller(finished_game())
    controller.key_down(Key.RESTART)
    texts = screen_texts(controller)
    for gone in ("GAME OVER", "HIGH SCORES", "Press Enter"):
        assert gone not in texts


# --- Sound events ----------------------------------------------------------


def real_controller(*pieces: PieceType) -> tuple[Game, Controller]:
    game = Game(rng=ScriptedRng(pieces))
    return game, Controller(game)


def test_blocked_move_makes_no_sound():
    game, controller = real_controller(PieceType.O, PieceType.O)
    while game.move_left():
        pass
    controller.drain_sounds()
    controller.key_down(Key.LEFT)
    assert controller.drain_sounds() == []


def test_successful_move_and_rotation_sound():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.LEFT)
    controller.key_down(Key.ROTATE_CW)
    assert controller.drain_sounds() == [Sound.MOVE, Sound.ROTATE]


def test_repeated_moves_sound_once_per_frame():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.LEFT)
    controller.drain_sounds()
    controller.update(270)  # three auto-repeats in one frame
    assert controller.drain_sounds().count(Sound.MOVE) == 1


def test_gravity_lock_sound():
    game, controller = real_controller(PieceType.O, PieceType.T)
    for _ in range(18):
        game.step_down()
    controller.update(16)
    assert controller.drain_sounds() == []  # not due yet
    for _ in range(60):
        controller.update(16)
        if game.pieces_locked:
            break
    assert game.pieces_locked == 1
    assert controller.drain_sounds() == [Sound.LOCK]


def test_soft_drop_step_is_silent():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.DOWN)
    assert controller.drain_sounds() == []


def test_tetris_with_level_up():
    game, controller = real_controller(PieceType.I, PieceType.T)
    game.lines = 9
    assert game.rotate_cw()
    for _ in range(4):
        assert game.move_right()
    game.board.place([(c, r) for r in range(18, 22) for c in range(9)], PieceType.J)
    controller.key_down(Key.HARD_DROP)
    assert controller.drain_sounds() == [Sound.TETRIS, Sound.LEVEL_UP]


def test_single_line_clear_sound():
    game, controller = real_controller(PieceType.O, PieceType.T)
    game.board.place([(c, 21) for c in range(8)], PieceType.J)
    for _ in range(4):
        assert game.move_right()
    controller.key_down(Key.HARD_DROP)
    assert controller.drain_sounds() == [Sound.CLEAR]


def test_game_over_sound():
    game, controller = real_controller(PieceType.O)
    sounds = []
    while not game.is_over:
        controller.key_down(Key.HARD_DROP)
        sounds = controller.drain_sounds()
    assert sounds == [Sound.LOCK, Sound.GAME_OVER]


def test_sounds_are_recorded_even_when_effects_are_off():
    # The audio layer decides whether to play; the controller only reports.
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.TOGGLE_SOUND)
    controller.key_down(Key.LEFT)
    assert not controller.sound_on
    assert controller.drain_sounds() == [Sound.MOVE]


# --- Music state and toggles -----------------------------------------------


def test_music_state_follows_the_game():
    game, controller = real_controller(PieceType.O)
    assert controller.music_state == "playing"
    controller.key_down(Key.PAUSE)
    assert controller.music_state == "paused"
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.TOGGLE_MUSIC)
    assert controller.music_state == "stopped"
    controller.key_down(Key.TOGGLE_MUSIC)
    while not game.is_over:
        controller.key_down(Key.HARD_DROP)
    assert controller.music_state == "stopped"


def test_music_generation_grows_on_new_game_and_music_on():
    _, controller = real_controller(PieceType.O)
    start = controller.music_generation
    controller.key_down(Key.TOGGLE_MUSIC)  # off
    assert controller.music_generation == start
    controller.key_down(Key.TOGGLE_MUSIC)  # on
    assert controller.music_generation == start + 1
    while controller.phase is Phase.PLAYING:
        controller.key_down(Key.HARD_DROP)
    controller.key_down(Key.RESTART)
    assert controller.music_generation == start + 2


def test_toggle_sound_sends_no_command(controller, game):
    controller.key_down(Key.TOGGLE_SOUND)
    assert not controller.sound_on
    assert game.calls == []


def test_toggle_music_keeps_pause(controller):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.TOGGLE_MUSIC)
    assert not controller.music_on
    assert controller.paused


def test_music_on_during_pause_waits_for_unpause(controller):
    controller.key_down(Key.TOGGLE_MUSIC)
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.TOGGLE_MUSIC)
    assert controller.music_state == "paused"
    controller.key_down(Key.PAUSE)
    assert controller.music_state == "playing"


def test_m_is_typed_during_name_entry():
    controller = Controller(record_game())
    controller.key_down(Key.TOGGLE_MUSIC)
    controller.text_input("M")
    assert controller.name == "M"
    assert controller.music_on


def test_toggles_work_on_the_table_screen():
    controller = Controller(finished_game())
    controller.key_down(Key.TOGGLE_SOUND)
    assert not controller.sound_on


# --- Sound settings and volume keys ----------------------------------------


def test_volume_up():
    controller = Controller(FakeGame())
    controller.key_down(Key.VOLUME_UP)
    assert controller.music_volume == 60


def test_volume_stops_at_100():
    controller = Controller(FakeGame(), settings=Settings(music_volume=100))
    controller.key_down(Key.VOLUME_UP)
    assert controller.music_volume == 100


def test_volume_stops_at_0():
    controller = Controller(FakeGame(), settings=Settings(music_volume=0))
    controller.key_down(Key.VOLUME_DOWN)
    assert controller.music_volume == 0


def test_volume_on_pause(controller, game):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.VOLUME_DOWN)
    assert controller.music_volume == 40
    assert controller.paused
    assert game.calls == []


def test_minus_is_typed_during_name_entry():
    controller = Controller(record_game())
    controller.key_down(Key.VOLUME_DOWN)
    controller.text_input("-")
    assert controller.name == "-"
    assert controller.music_volume == 50


def test_volume_on_the_table_screen():
    controller = Controller(finished_game())
    controller.key_down(Key.VOLUME_UP)
    assert controller.music_volume == 60


def test_every_settings_change_is_reported():
    reported = []
    controller = Controller(FakeGame(), on_settings_change=reported.append)
    controller.key_down(Key.TOGGLE_MUSIC)
    controller.key_down(Key.TOGGLE_SOUND)
    controller.key_down(Key.VOLUME_UP)
    assert reported == [
        Settings(music_on=False, sound_on=True, music_volume=50),
        Settings(music_on=False, sound_on=False, music_volume=50),
        Settings(music_on=False, sound_on=False, music_volume=60),
    ]
    assert controller.settings == reported[-1]


def test_no_report_when_volume_is_at_its_limit():
    reported = []
    controller = Controller(
        FakeGame(), settings=Settings(music_volume=100), on_settings_change=reported.append
    )
    controller.key_down(Key.VOLUME_UP)
    assert reported == []


def test_saved_music_off_means_no_music():
    controller = Controller(FakeGame(), settings=Settings(music_on=False))
    assert not controller.music_on
    assert controller.music_state == "stopped"


def test_volume_change_does_not_restart_music():
    controller = Controller(FakeGame())
    generation = controller.music_generation
    controller.key_down(Key.VOLUME_UP)
    assert controller.music_generation == generation


# --- Splash screen ---------------------------------------------------------

T_SPAWN = {(4, 2), (3, 3), (4, 3), (5, 3)}
T_ONE_ROW_DOWN = {(4, 3), (3, 4), (4, 4), (5, 4)}


def splash_controller(*pieces: PieceType) -> tuple[Game, Controller]:
    game = Game(rng=ScriptedRng(pieces or (PieceType.T,)))
    return game, Controller(game, splash=True)


def test_no_time_passes_on_the_splash():
    game, controller = splash_controller(PieceType.T, PieceType.T)
    assert controller.phase is Phase.SPLASH
    frames(controller, 5000)
    assert set(game.active.cells()) == T_SPAWN


def test_splash_sends_no_ticks():
    game = FakeGame()
    controller = Controller(game, splash=True)
    frames(controller, 5000)
    assert game.ticks == []


def test_enter_starts_the_game():
    game, controller = splash_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.PLAYING
    frames(controller, 800)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_keys_on_the_splash():
    game = FakeGame()
    controller = Controller(game, splash=True)
    controller.key_down(Key.LEFT)
    controller.key_down(Key.HARD_DROP)
    controller.key_down(Key.HELP)
    controller.key_down(Key.TOGGLE_MUSIC)
    assert game.calls == []
    assert controller.phase is Phase.SPLASH
    assert not controller.help_open
    assert not controller.music_on


def test_volume_works_on_the_splash():
    controller = Controller(FakeGame(), splash=True)
    controller.key_down(Key.VOLUME_UP)
    assert controller.music_volume == 60


def test_no_music_on_the_splash():
    _, controller = splash_controller()
    assert controller.music_state == "stopped"
    controller.key_down(Key.RESTART)
    assert controller.music_state == "playing"


def test_splash_is_not_shown_again():
    game, controller = splash_controller(PieceType.O)
    controller.key_down(Key.RESTART)
    while controller.phase is Phase.PLAYING:
        controller.key_down(Key.HARD_DROP)
    assert controller.phase is Phase.TABLE
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.PLAYING


# --- Help screen (F1) ------------------------------------------------------


def test_f1_opens_the_help_screen(controller, game):
    controller.key_down(Key.HELP)
    assert controller.help_open
    frames(controller, 5000)
    controller.key_down(Key.LEFT)
    assert game.ticks == []
    assert game.calls == []
    assert controller.music_state == "paused"


@pytest.mark.parametrize("closing_key", [Key.HELP, Key.PAUSE, Key.RESTART])
def test_help_screen_closes_and_the_game_goes_on(closing_key):
    game, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.HELP)
    controller.key_down(closing_key)
    assert not controller.help_open
    assert not controller.paused
    frames(controller, 800)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_f1_on_pause():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.HELP)
    assert controller.help_open
    controller.key_down(Key.RESTART)
    assert not controller.help_open
    assert not controller.paused
    assert controller.phase is Phase.PLAYING


def test_f1_is_ignored_after_game_over():
    controller = Controller(finished_game())
    controller.key_down(Key.HELP)
    assert controller.phase is Phase.TABLE
    assert not controller.help_open


def test_f1_is_ignored_during_name_entry():
    controller = Controller(record_game())
    controller.key_down(Key.HELP)
    assert controller.phase is Phase.NAME_ENTRY
    assert not controller.help_open


def test_held_key_does_not_repeat_after_help(controller, game):
    controller.key_down(Key.LEFT)
    controller.key_down(Key.HELP)
    frames(controller, 1000)
    controller.key_down(Key.HELP)
    frames(controller, 500)
    assert game.calls == ["left"]


def test_sound_keys_work_on_the_help_screen(controller):
    controller.key_down(Key.HELP)
    controller.key_down(Key.TOGGLE_MUSIC)
    controller.key_down(Key.VOLUME_UP)
    assert controller.help_open
    assert not controller.music_on
    assert controller.music_volume == 60


def test_other_keys_are_ignored_on_the_help_screen(controller, game):
    controller.key_down(Key.HELP)
    for key in (Key.LEFT, Key.DOWN, Key.HARD_DROP, Key.ROTATE_CW, Key.BACKSPACE):
        controller.key_down(key)
    assert controller.help_open
    assert game.calls == []


# --- Key screen texts ------------------------------------------------------

SPEC_HOTKEYS = [
    ("Left / Right", "Move"),
    ("Down", "Soft drop"),
    ("Space", "Hard drop"),
    ("Up / X", "Rotate right"),
    ("Z / Ctrl", "Rotate left"),
    ("P / Esc", "Pause"),
    ("F1", "Help"),
    ("M", "Music on/off"),
    ("- / +", "Music volume"),
    ("N", "Sound on/off"),
    ("Enter", "Start / restart"),
]


def test_splash_texts():
    _, controller = splash_controller()
    assert key_screen(controller) == "splash"
    texts = screen_texts(controller)
    assert texts[0] == "SEVA Tetris"
    assert texts[-1] == "Press Enter to start"
    pairs = list(zip(texts[1:-1:2], texts[2:-1:2]))
    assert pairs == SPEC_HOTKEYS
    assert "SCORE" not in texts and "NEXT" not in texts
    assert all(text.isascii() for text in texts)


def test_key_table_layout():
    _, controller = splash_controller()
    entries = key_screen_texts(controller)
    keys = [pos for _, pos, role in entries if role == "key"]
    actions = [pos for _, pos, role in entries if role == "action"]
    assert keys == [(70, 150 + 36 * row) for row in range(11)]
    assert actions == [(270, 150 + 36 * row) for row in range(11)]


def test_help_screen_texts():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.HELP)
    texts = screen_texts(controller)
    assert key_screen(controller) == "help"
    assert texts[0] == "SEVA Tetris"
    assert texts[-1] == "Press F1 or Enter to return"
    assert list(zip(texts[1:-1:2], texts[2:-1:2])) == SPEC_HOTKEYS


def test_field_and_panel_return_after_help():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.HELP)
    controller.key_down(Key.HELP)
    texts = screen_texts(controller)
    assert key_screen(controller) is None
    assert "SCORE" in texts and "NEXT" in texts
    assert "SEVA Tetris" not in texts


# --- Hold key --------------------------------------------------------------


def test_c_then_shift_holds_twice(controller, game):
    controller.key_down(Key.HOLD)  # C
    controller.key_down(Key.HOLD)  # Shift
    assert game.calls == ["hold", "hold"]


def test_hold_is_not_repeated_while_held(controller, game):
    controller.key_down(Key.HOLD)
    frames(controller, 1000)
    assert game.calls == ["hold"]


def test_hold_makes_a_sound():
    _, controller = real_controller(PieceType.T, PieceType.S, PieceType.Z)
    controller.key_down(Key.HOLD)
    assert controller.drain_sounds() == [Sound.HOLD]


def test_rejected_hold_is_silent():
    _, controller = real_controller(PieceType.T, PieceType.S, PieceType.Z)
    controller.key_down(Key.HOLD)
    controller.drain_sounds()
    controller.key_down(Key.HOLD)
    assert controller.drain_sounds() == []


def test_hold_is_ignored_on_pause(controller, game):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.HOLD)
    assert game.calls == []


# --- Effects volume keys ---------------------------------------------------


def test_nine_makes_effects_quieter():
    controller = Controller(FakeGame())
    controller.key_down(Key.SFX_DOWN)
    assert controller.settings.sfx_volume == 90


def test_effects_volume_stops_at_100():
    controller = Controller(FakeGame())
    controller.key_down(Key.SFX_UP)
    assert controller.settings.sfx_volume == 100


def test_effects_volume_stops_at_0():
    controller = Controller(FakeGame(), settings=Settings(sfx_volume=0))
    controller.key_down(Key.SFX_DOWN)
    assert controller.settings.sfx_volume == 0


def test_digits_are_typed_during_name_entry():
    controller = Controller(record_game())
    controller.key_down(Key.SFX_DOWN)
    controller.text_input("9")
    assert controller.name == "9"
    assert controller.settings.sfx_volume == 100


def test_effects_volume_keys_send_no_command_and_keep_pause(controller, game):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.SFX_DOWN)
    assert controller.paused
    assert game.calls == []


def test_effects_volume_on_the_panel():
    controller = Controller(Game(seed=1))
    for _ in range(3):
        controller.key_down(Key.SFX_DOWN)
    assert "SOUND 70%" in screen_texts(controller)


def test_effects_volume_change_is_reported():
    reported = []
    controller = Controller(FakeGame(), on_settings_change=reported.append)
    controller.key_down(Key.SFX_DOWN)
    assert reported == [Settings(sfx_volume=90)]
