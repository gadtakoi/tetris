import pytest

from tests.helpers import ScriptedRng
from tetris.game import Game
from tetris.pieces import PieceType
from tetris.highscores import Entry, HighScores
from tetris_ui import GAME_TITLE, guide, menus
from tetris_ui.input import Controller, Key, KeyRepeater, Phase, Sound
from tetris_ui.settings import Settings
from tetris_ui.texts import RU
from tetris_ui.layout import (
    HIGHLIGHT,
    TEXT,
    TITLE,
    all_screen_texts,
    cell_rect,
    full_screen,
    full_screen_texts,
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

    def new_game(self, start_level=0):
        self.calls.append(f"new_game {start_level}")
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


@pytest.mark.parametrize("key", [Key.PAUSE, Key.ESCAPE])
def test_unpause(controller, game, key):
    controller.key_down(Key.PAUSE)
    controller.key_down(key)
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


def test_game_title():
    assert TITLE == GAME_TITLE == "Tetris Shmetris"


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
    assert overlay_lines(controller) == [
        ("PAUSE", TEXT), ("Continue", HIGHLIGHT), ("Main menu", TEXT),
    ]


def test_pause_selection_moves():
    controller = Controller(Game(seed=1))
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.DOWN)
    assert overlay_lines(controller)[1:] == [("Continue", TEXT), ("Main menu", HIGHLIGHT)]


def test_texts_game_over_without_record():
    table = HighScores()
    table.add(Entry("ANNA", 1200, 13, 1))
    controller = Controller(finished_game(), table)
    texts = screen_texts(controller)
    assert texts[texts.index("SCORE") + 1] == "0"
    assert overlay_texts(controller) == [
        "GAME OVER", "HIGH SCORES", "1. ANNA 1200", "Enter - new game", "Esc - main menu",
    ]


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
    assert overlay_texts(controller) == [
        "GAME OVER", "HIGH SCORES", "No records yet", "Enter - new game", "Esc - main menu",
    ]


def test_texts_after_restart():
    controller = Controller(finished_game())
    controller.key_down(Key.RESTART)
    texts = screen_texts(controller)
    for gone in ("GAME OVER", "HIGH SCORES", "Enter - new game", "Esc - main menu"):
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


# --- Main menu -------------------------------------------------------------

T_SPAWN = {(4, 2), (3, 3), (4, 3), (5, 3)}
T_ONE_ROW_DOWN = {(4, 3), (3, 4), (4, 4), (5, 4)}


def menu_controller(*pieces: PieceType, **kwargs) -> tuple[Game, Controller]:
    game = Game(rng=ScriptedRng(pieces or (PieceType.T,)))
    return game, Controller(game, start_in_menu=True, **kwargs)


def choose(controller: Controller, item: str) -> None:
    """Move the main menu selection down to item and press Enter."""
    while menus.MAIN_ITEMS[controller.menu_index] != item:
        controller.key_down(Key.DOWN)
    controller.key_down(Key.RESTART)


def highlighted(controller: Controller) -> list[str]:
    return [text for text, _, role, color in full_screen_texts(controller)
            if role == "item" and color == HIGHLIGHT]


def test_menu_at_launch():
    _, controller = menu_controller()
    assert controller.phase is Phase.MENU
    assert full_screen(controller) == "menu"
    texts = screen_texts(controller)
    assert texts == [
        "Tetris Shmetris", "New game", "High scores", "Settings", "Controls", "Guide", "Quit",
        "Up / Down - choose, Enter - select", "v1.0.0",
    ]
    assert highlighted(controller) == ["New game"]
    assert "SCORE" not in texts and "NEXT" not in texts


def test_menu_selection_moves_round():
    _, controller = menu_controller()
    controller.key_down(Key.DOWN)
    controller.key_down(Key.DOWN)
    assert highlighted(controller) == ["Settings"]
    for _ in range(3):
        controller.key_down(Key.UP)
    assert highlighted(controller) == ["Quit"]
    controller.key_down(Key.DOWN)
    assert highlighted(controller) == ["New game"]


def test_new_game_from_the_menu():
    game, controller = menu_controller(PieceType.T)
    frames(controller, 800)
    assert set(game.active.cells()) == T_SPAWN  # no time passes in the menu
    choose(controller, "New game")
    assert controller.phase is Phase.PLAYING
    frames(controller, 800)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_new_game_uses_the_start_level():
    game = FakeGame()
    controller = Controller(game, start_in_menu=True, settings=Settings(start_level=7))
    controller.key_down(Key.RESTART)
    assert game.calls == ["new_game 7"]


def test_no_time_and_no_music_in_the_menu():
    game = FakeGame()
    controller = Controller(game, start_in_menu=True)
    frames(controller, 5000)
    assert game.ticks == []
    assert controller.music_state == "stopped"


def test_music_starts_with_the_game():
    _, controller = menu_controller()
    generation = controller.music_generation
    controller.key_down(Key.RESTART)
    assert controller.music_state == "playing"
    assert controller.music_generation == generation + 1


@pytest.mark.parametrize("phase_item", [None, "High scores", "Settings", "Controls"])
def test_sound_keys_in_the_menu_and_its_screens(phase_item):
    _, controller = menu_controller()
    if phase_item:
        choose(controller, phase_item)
    phase = controller.phase
    controller.key_down(Key.TOGGLE_MUSIC)
    controller.key_down(Key.VOLUME_UP)
    controller.key_down(Key.SFX_DOWN)
    assert controller.phase is phase
    assert not controller.music_on
    assert (controller.music_volume, controller.settings.sfx_volume) == (60, 90)


def test_game_keys_are_ignored_in_the_menu():
    game = FakeGame()
    controller = Controller(game, start_in_menu=True)
    for key in (Key.LEFT, Key.RIGHT, Key.HARD_DROP, Key.HOLD, Key.ROTATE_CW, Key.PAUSE,
                Key.HELP, Key.BACKSPACE, Key.ESCAPE):
        controller.key_down(key)
    assert game.calls == []
    assert controller.phase is Phase.MENU
    assert not controller.paused and not controller.help_open
    assert highlighted(controller) == ["New game"]


def test_high_scores_from_the_menu():
    table = HighScores()
    table.add(Entry("ANNA", 1200, 13, 1))
    _, controller = menu_controller(scores=table)
    choose(controller, "High scores")
    assert controller.phase is Phase.SCORES
    assert screen_texts(controller) == ["HIGH SCORES", "1. ANNA 1200", "Press Enter or Esc to return"]


def test_empty_high_scores_from_the_menu():
    _, controller = menu_controller()
    choose(controller, "High scores")
    assert screen_texts(controller)[:2] == ["HIGH SCORES", "No records yet"]


@pytest.mark.parametrize("key", [Key.ESCAPE, Key.RESTART])
def test_back_from_high_scores(key):
    _, controller = menu_controller()
    choose(controller, "High scores")
    controller.key_down(key)
    assert controller.phase is Phase.MENU
    assert highlighted(controller) == ["New game"]


def test_controls_from_the_menu():
    _, controller = menu_controller()
    choose(controller, "Controls")
    assert full_screen(controller) == "controls"
    texts = screen_texts(controller)
    assert texts[0] == "Tetris Shmetris"
    assert texts[-1] == "Press Enter or Esc to return"
    assert list(zip(texts[1:-1:2], texts[2:-1:2])) == SPEC_HOTKEYS
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.MENU


def test_escape_leaves_controls():
    _, controller = menu_controller()
    choose(controller, "Controls")
    controller.key_down(Key.ESCAPE)
    assert controller.phase is Phase.MENU


def test_quit_from_the_menu():
    _, controller = menu_controller()
    assert not controller.quit_requested
    choose(controller, "Quit")
    assert controller.quit_requested


# --- Settings screen -------------------------------------------------------


def settings_controller(**settings) -> tuple[FakeGame, Controller, list[Settings]]:
    game, reported = FakeGame(), []
    controller = Controller(game, start_in_menu=True, settings=Settings(**settings),
                            on_settings_change=reported.append)
    choose(controller, "Settings")
    return game, controller, reported


def select_row(controller: Controller, row: str) -> None:
    while controller.settings_index != menus.SETTING_ROWS.index(row):
        controller.key_down(Key.DOWN)


def test_settings_screen_defaults():
    _, controller, _ = settings_controller()
    assert controller.phase is Phase.SETTINGS
    assert screen_texts(controller) == [
        "Settings",
        "Language: English",
        "Music: On",
        "Music volume: 50%",
        "Sound: On",
        "Sound volume: 100%",
        "Start level: 0",
        "Ghost: On",
        "Autorepeat: Normal",
        "Back",
        "Left / Right - change, Esc - back",
    ]
    assert highlighted(controller) == ["Language: English"]


def test_settings_selection_moves_round():
    _, controller, _ = settings_controller()
    controller.key_down(Key.UP)
    assert highlighted(controller) == ["Back"]
    controller.key_down(Key.DOWN)
    assert highlighted(controller) == ["Language: English"]


def test_start_level_change_applies_to_the_next_game():
    game, controller, reported = settings_controller()
    select_row(controller, "start_level")
    controller.key_down(Key.RIGHT)
    controller.key_down(Key.RIGHT)
    assert "Start level: 2" in screen_texts(controller)
    assert reported[-1] == Settings(start_level=2)
    controller.key_down(Key.ESCAPE)
    controller.key_down(Key.RESTART)
    assert game.calls == ["new_game 2"]


def test_left_goes_back_a_value():
    _, controller, _ = settings_controller(start_level=3)
    select_row(controller, "start_level")
    controller.key_down(Key.LEFT)
    assert controller.settings.start_level == 2


def test_setting_stops_at_its_limit():
    _, controller, reported = settings_controller(music_volume=100)
    select_row(controller, "music_volume")
    controller.key_down(Key.RIGHT)
    assert "Music volume: 100%" in screen_texts(controller)
    assert reported == []


def test_setting_goes_round():
    _, controller, _ = settings_controller(autorepeat="fast")
    select_row(controller, "autorepeat")
    controller.key_down(Key.RIGHT)
    assert "Autorepeat: Slow" in screen_texts(controller)


def test_enter_on_music_works_like_m():
    _, controller, _ = settings_controller()
    select_row(controller, "music_on")
    generation = controller.music_generation
    controller.key_down(Key.RESTART)
    assert "Music: Off" in screen_texts(controller)
    assert not controller.music_on
    controller.key_down(Key.RESTART)
    assert controller.music_generation == generation + 1  # switched on: starts over
    controller.key_down(Key.RESTART)
    controller.key_down(Key.ESCAPE)
    controller.key_down(Key.RESTART)
    assert "MUSIC OFF" in screen_texts(controller)


def test_sound_keys_show_on_the_settings_screen():
    _, controller, _ = settings_controller()
    controller.key_down(Key.SFX_DOWN)
    assert "Sound volume: 90%" in screen_texts(controller)


@pytest.mark.parametrize("key", [Key.ESCAPE, Key.RESTART])
def test_back_from_settings(key):
    _, controller, _ = settings_controller()
    if key is Key.RESTART:
        controller.key_down(Key.UP)  # to Back
    controller.key_down(key)
    assert controller.phase is Phase.MENU
    assert highlighted(controller) == ["New game"]


def test_left_right_on_back_do_nothing():
    _, controller, reported = settings_controller()
    controller.key_down(Key.UP)
    controller.key_down(Key.RIGHT)
    controller.key_down(Key.LEFT)
    assert controller.phase is Phase.SETTINGS
    assert reported == []


def test_settings_open_on_the_first_row():
    _, controller, _ = settings_controller()
    controller.key_down(Key.DOWN)
    controller.key_down(Key.ESCAPE)
    choose(controller, "Settings")
    assert controller.settings_index == 0


def test_ghost_setting():
    _, controller, _ = settings_controller()
    select_row(controller, "ghost")
    controller.key_down(Key.RIGHT)
    assert controller.settings.ghost is False
    assert "Ghost: Off" in screen_texts(controller)


def test_language_setting_is_stored():
    _, controller, reported = settings_controller()
    controller.key_down(Key.RIGHT)
    assert controller.settings.language == "ru"
    assert reported == [Settings(language="ru")]


# --- Pause menu ------------------------------------------------------------


def test_enter_on_pause_continues(controller, game):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.RESTART)
    assert not controller.paused
    controller.update(16)
    assert game.ticks == [16]


def test_main_menu_from_pause_records_nothing():
    saved = []
    game = Game(rng=ScriptedRng([PieceType.T]))
    controller = Controller(game, HighScores(), on_save=saved.append)
    game.score = 340
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.DOWN)
    controller.key_down(Key.RESTART)
    assert controller.phase is Phase.MENU
    assert not controller.paused
    assert controller.scores.entries == ()
    assert saved == []
    assert controller.music_state == "stopped"
    assert highlighted(controller) == ["New game"]


def test_pause_selection_goes_round_and_resets(controller):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.UP)
    assert controller.pause_index == 1
    controller.key_down(Key.DOWN)
    assert controller.pause_index == 0
    controller.key_down(Key.DOWN)
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.PAUSE)
    assert controller.pause_index == 0


def test_arrows_on_pause_do_not_move_the_piece(controller, game):
    controller.key_down(Key.PAUSE)
    for key in (Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT, Key.HARD_DROP):
        controller.key_down(key)
    assert game.calls == []


def test_up_rotates_and_escape_pauses_during_play(controller, game):
    controller.key_down(Key.UP)
    assert game.calls == ["cw"]
    controller.key_down(Key.ESCAPE)
    assert controller.paused


def test_new_game_after_a_game_left_from_pause():
    game, controller = real_controller(PieceType.T)
    game.score = 340
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.DOWN)
    controller.key_down(Key.RESTART)
    controller.key_down(Key.RESTART)  # New game
    assert controller.phase is Phase.PLAYING
    assert game.score == 0


# --- After game over -------------------------------------------------------


def test_escape_on_the_table_opens_the_menu():
    controller = Controller(finished_game())
    controller.key_down(Key.ESCAPE)
    assert controller.phase is Phase.MENU
    assert highlighted(controller) == ["New game"]


def test_enter_on_the_table_uses_the_start_level():
    game = FakeGame()
    controller = Controller(game, settings=Settings(start_level=4))
    game.is_over = True
    controller.key_down(Key.RESTART)
    assert game.calls == ["new_game 4"]


def test_escape_during_name_entry_does_nothing():
    controller = Controller(record_game())
    controller.key_down(Key.ESCAPE)
    assert controller.phase is Phase.NAME_ENTRY


# --- Auto-repeat speed -----------------------------------------------------


@pytest.mark.parametrize(("speed", "hold_ms", "moves"), [
    ("fast", 180, 4),  # 0, 120, 150, 180
    ("fast", 119, 1),
    ("slow", 289, 2),  # 0, 220
    ("slow", 360, 4),  # 0, 220, 290, 360
    ("normal", 270, 4),
])
def test_autorepeat_speed(speed, hold_ms, moves):
    game = FakeGame()
    controller = Controller(game, settings=Settings(autorepeat=speed))
    controller.key_down(Key.LEFT)
    frames(controller, hold_ms, frame_ms=1)
    assert game.calls == ["left"] * moves


def test_autorepeat_setting_applies_to_the_next_game():
    game, controller, _ = settings_controller()
    select_row(controller, "autorepeat")
    controller.key_down(Key.RIGHT)  # Fast
    controller.key_down(Key.ESCAPE)
    controller.key_down(Key.RESTART)
    controller.key_down(Key.LEFT)
    frames(controller, 180, frame_ms=1)
    assert game.calls == ["new_game 0"] + ["left"] * 4


# --- Help screen (F1) ------------------------------------------------------


def test_f1_opens_the_help_screen(controller, game):
    controller.key_down(Key.HELP)
    assert controller.help_open
    frames(controller, 5000)
    controller.key_down(Key.LEFT)
    assert game.ticks == []
    assert game.calls == []
    assert controller.music_state == "paused"


@pytest.mark.parametrize("closing_key", [Key.HELP, Key.PAUSE, Key.ESCAPE, Key.RESTART])
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


@pytest.mark.parametrize("item", [None, "High scores", "Settings", "Controls"])
def test_f1_is_ignored_in_the_menu(item):
    _, controller = menu_controller()
    if item:
        choose(controller, item)
    phase = controller.phase
    controller.key_down(Key.HELP)
    assert controller.phase is phase
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


# --- Key list texts --------------------------------------------------------

SPEC_HOTKEYS = [
    ("Left / Right", "Move"),
    ("Down", "Soft drop"),
    ("Space", "Hard drop"),
    ("Up / X", "Rotate right"),
    ("Z / Ctrl", "Rotate left"),
    ("C / Shift", "Hold"),
    ("P / Esc", "Pause"),
    ("F1", "Help"),
    ("F2", "Guide"),
    ("M", "Music on/off"),
    ("- / +", "Music volume"),
    ("N", "Sound on/off"),
    ("9 / 0", "Sound volume"),
    ("Enter", "Select / new game"),
]


def test_key_table_layout():
    _, controller = menu_controller()
    choose(controller, "Controls")
    entries = full_screen_texts(controller)
    keys = [pos for _, pos, role, _ in entries if role == "key"]
    actions = [pos for _, pos, role, _ in entries if role == "action"]
    assert keys == [(70, 120 + 32 * row) for row in range(14)]
    assert actions == [(270, 120 + 32 * row) for row in range(14)]
    assert all(text.isascii() for text, _, _, _ in entries)


def test_help_screen_texts():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.HELP)
    texts = screen_texts(controller)
    assert full_screen(controller) == "help"
    assert texts[0] == "Tetris Shmetris"
    assert texts[-1] == "Press F1 or Enter to return"
    assert list(zip(texts[1:-1:2], texts[2:-1:2])) == SPEC_HOTKEYS
    assert "SCORE" not in texts and "NEXT" not in texts


def test_field_and_panel_return_after_help():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.HELP)
    controller.key_down(Key.HELP)
    texts = screen_texts(controller)
    assert full_screen(controller) is None
    assert "SCORE" in texts and "NEXT" in texts
    assert "Tetris Shmetris" not in texts


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


# --- Russian interface -----------------------------------------------------


def ru(**settings) -> Settings:
    return Settings(language="ru", **settings)


def test_english_by_default():
    _, controller = menu_controller()
    texts = screen_texts(controller)
    assert "New game" in texts and "Settings" in texts


def test_switch_to_russian():
    _, controller, _ = settings_controller()
    controller.key_down(Key.RIGHT)
    texts = screen_texts(controller)
    assert "Язык: Русский" in texts
    assert texts[0] == "Настройки"
    controller.key_down(Key.ESCAPE)
    texts = screen_texts(controller)
    assert "Новая игра" in texts and "Настройки" in texts
    assert texts[0] == "Tetris Shmetris"


def test_switch_back_to_english():
    _, controller, _ = settings_controller(language="ru")
    controller.key_down(Key.LEFT)
    assert screen_texts(controller)[:2] == ["Settings", "Language: English"]


def test_names_and_numbers_are_not_translated():
    table = HighScores()
    table.add(Entry("Ann", 340, 3, 0))
    _, controller = menu_controller(scores=table, settings=ru())
    choose(controller, "High scores")
    assert screen_texts(controller) == ["РЕКОРДЫ", "1. Ann 340", "Enter или Esc - назад"]


def test_panel_in_russian():
    controller = Controller(Game(seed=1), settings=ru())
    assert screen_texts(controller) == [
        "ДАЛЕЕ", "ЗАПАС", "ОЧКИ", "0", "ЛИНИИ", "0", "УРОВЕНЬ", "0",
        "МУЗЫКА ВКЛ", "МУЗЫКА 50%", "ЗВУК ВКЛ", "ЗВУК 100%",
    ]


def test_switches_off_in_russian():
    controller = Controller(Game(seed=1), settings=ru(music_on=False, sound_on=False))
    texts = screen_texts(controller)
    assert "МУЗЫКА ВЫКЛ" in texts and "ЗВУК ВЫКЛ" in texts


def test_name_entry_in_russian():
    controller = Controller(record_game(340), settings=ru())
    controller.text_input("Иван")
    assert overlay_texts(controller) == ["ИГРА ОКОНЧЕНА", "НОВЫЙ РЕКОРД", "Имя: Иван_"]


def test_table_in_russian():
    controller = Controller(finished_game(), settings=ru())
    assert overlay_texts(controller) == [
        "ИГРА ОКОНЧЕНА", "РЕКОРДЫ", "Рекордов пока нет", "Enter - новая игра",
        "Esc - главное меню",
    ]


def test_pause_in_russian():
    controller = Controller(Game(seed=1), settings=ru())
    controller.key_down(Key.PAUSE)
    assert overlay_lines(controller) == [
        ("ПАУЗА", TEXT), ("Продолжить", HIGHLIGHT), ("Главное меню", TEXT),
    ]


def test_key_list_in_russian():
    _, controller = menu_controller(settings=ru())
    choose(controller, "Controls")
    texts = screen_texts(controller)
    pairs = list(zip(texts[1:-1:2], texts[2:-1:2]))
    for pair in [("Влево / Вправо", "Сдвиг"), ("Пробел", "Жёсткое падение"),
                 ("C / Shift", "Отложить"), ("F2", "Инструкция"),
                 ("9 / 0", "Громкость звука")]:
        assert pair in pairs
    assert texts[0] == "Tetris Shmetris"
    assert texts[-1] == "Enter или Esc - назад"


def test_help_screen_in_russian():
    controller = Controller(Game(seed=1), settings=ru())
    controller.key_down(Key.HELP)
    assert screen_texts(controller)[-1] == "F1 или Enter - назад"


def test_setting_lines_in_russian():
    _, controller, _ = settings_controller(language="ru")
    assert screen_texts(controller)[1:-1] == [
        "Язык: Русский",
        "Музыка: Вкл",
        "Громкость музыки: 50%",
        "Звук: Вкл",
        "Громкость звука: 100%",
        "Начальный уровень: 0",
        "Тень: Вкл",
        "Автоповтор: Обычно",
        "Назад",
    ]
    assert screen_texts(controller)[-1] == "Влево / Вправо - изменить, Esc - назад"


@pytest.mark.parametrize(("settings", "line"), [
    (ru(music_on=False), "Музыка: Выкл"),
    (ru(autorepeat="slow"), "Автоповтор: Медленно"),
    (ru(autorepeat="fast"), "Автоповтор: Быстро"),
    (ru(ghost=False), "Тень: Выкл"),
])
def test_setting_values_in_russian(settings, line):
    _, controller, _ = settings_controller(**{
        field: getattr(settings, field) for field in ("language", "music_on", "autorepeat", "ghost")
    })
    assert line in screen_texts(controller)


def test_menu_in_russian():
    _, controller = menu_controller(settings=ru())
    assert screen_texts(controller) == [
        "Tetris Shmetris", "Новая игра", "Рекорды", "Настройки", "Управление", "Инструкция",
        "Выход", "Вверх / Вниз - выбор, Enter - открыть", "v1.0.0",
    ]


def test_every_text_is_translated():
    table = HighScores()
    table.add(Entry("Ann", 340, 3, 0))
    for settings in (ru(), ru(music_on=False, sound_on=False, ghost=False, autorepeat="slow"),
                     ru(autorepeat="fast")):
        controller = Controller(Game(seed=1), table, settings=settings)
        left_english = set(all_screen_texts(controller)) & set(RU)
        assert not left_english


def test_english_texts_cover_every_screen():
    controller = Controller(Game(seed=1))
    texts = set(all_screen_texts(controller))
    for text in ("NEXT", "PAUSE", "GAME OVER", "NEW RECORD", "New game", "Settings",
                 "Language: English", "Move", "Press F1 or Enter to return"):
        assert text in texts


# --- Guide (F2): opening, paging and closing ---------------------------------


def test_f2_opens_the_guide_during_play():
    game, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.GUIDE)
    assert controller.guide_open and controller.guide_page == 0
    frames(controller, 5000)
    controller.key_down(Key.LEFT)
    assert set(game.active.cells()) == T_SPAWN  # neither moved nor fell
    assert controller.music_state == "paused"


def test_closing_the_guide_leaves_the_game_paused():
    game, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.ESCAPE)
    frames(controller, 800)
    assert not controller.guide_open
    assert controller.paused and controller.pause_index == 0
    assert overlay_lines(controller)[:2] == [("PAUSE", TEXT), ("Continue", HIGHLIGHT)]
    assert set(game.active.cells()) == T_SPAWN


def test_guide_on_pause_returns_to_continue(controller):
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.DOWN)  # Main menu selected
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RESTART)
    assert not controller.guide_open
    assert controller.phase is Phase.PLAYING
    assert controller.paused and controller.pause_index == 0


def test_guide_from_the_settings_screen_keeps_the_row():
    _, controller, reported = settings_controller()
    select_row(controller, "ghost")
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RIGHT)  # turns a page, does not change Ghost
    controller.key_down(Key.GUIDE)
    assert controller.phase is Phase.SETTINGS
    assert controller.settings_index == menus.SETTING_ROWS.index("ghost")
    assert controller.settings.ghost and reported == []


def test_f2_in_the_main_menu_returns_to_new_game():
    _, controller = menu_controller()
    controller.key_down(Key.DOWN)
    controller.key_down(Key.DOWN)  # Settings
    controller.key_down(Key.GUIDE)
    assert controller.guide_open
    controller.key_down(Key.ESCAPE)
    assert controller.phase is Phase.MENU and not controller.guide_open
    assert highlighted(controller) == ["New game"]


@pytest.mark.parametrize("item", ["High scores", "Controls"])
def test_guide_from_a_menu_screen_returns_to_it(item):
    _, controller = menu_controller()
    choose(controller, item)
    phase = controller.phase
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RESTART)  # closes the guide, does not leave the screen
    assert controller.phase is phase and not controller.guide_open


def test_f2_is_ignored_on_the_table():
    controller = Controller(finished_game())
    controller.key_down(Key.GUIDE)
    assert not controller.guide_open
    assert controller.phase is Phase.TABLE


def test_f2_is_ignored_during_name_entry():
    controller = Controller(record_game())
    controller.text_input("Ann")
    controller.key_down(Key.GUIDE)
    assert not controller.guide_open
    assert controller.phase is Phase.NAME_ENTRY and controller.name == "Ann"


def test_f2_is_ignored_on_the_help_screen(controller):
    controller.key_down(Key.HELP)
    controller.key_down(Key.GUIDE)
    assert controller.help_open and not controller.guide_open


def test_other_keys_are_ignored_in_the_guide():
    game, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.GUIDE)
    for key in (Key.HARD_DROP, Key.PAUSE, Key.HELP, Key.HOLD, Key.UP, Key.DOWN, Key.BACKSPACE):
        controller.key_down(key)
    assert controller.guide_open and controller.guide_page == 0
    assert not controller.help_open
    assert set(game.active.cells()) == T_SPAWN and game.held_type is None


def test_sound_keys_work_in_the_guide(controller):
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.TOGGLE_MUSIC)
    controller.key_down(Key.SFX_DOWN)
    assert controller.guide_open
    assert not controller.music_on and controller.settings.sfx_volume == 90


def test_guide_pages_turn():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RIGHT)
    controller.key_down(Key.RIGHT)
    assert controller.guide_page == 2
    controller.key_down(Key.LEFT)
    assert controller.guide_page == 1


def test_guide_pages_stop_at_the_ends():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.LEFT)
    assert controller.guide_page == 0
    for _ in range(10):
        controller.key_down(Key.RIGHT)
    assert controller.guide_page == 5


def test_guide_always_opens_on_the_first_page():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RIGHT)
    controller.key_down(Key.GUIDE)  # close
    controller.key_down(Key.GUIDE)  # open again
    assert controller.guide_page == 0


def test_guide_item_in_the_main_menu():
    game = FakeGame()
    controller = Controller(game, start_in_menu=True)
    choose(controller, "Guide")
    assert controller.guide_open and controller.guide_page == 0
    controller.key_down(Key.RESTART)  # closes the guide, starts nothing
    assert controller.phase is Phase.MENU and not controller.guide_open
    assert highlighted(controller) == ["New game"]
    assert game.calls == []


def test_no_music_under_the_guide_in_the_menu():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    assert controller.music_state == "stopped"


def test_held_key_does_not_repeat_after_the_guide(controller, game):
    controller.key_down(Key.LEFT)
    controller.key_down(Key.GUIDE)
    frames(controller, 1000)
    controller.key_down(Key.ESCAPE)  # closes the guide: the game is still paused
    controller.key_down(Key.PAUSE)  # continue
    frames(controller, 500)
    assert game.calls == ["left"]


# --- Guide (F2): texts -------------------------------------------------------


def guide_paragraphs(controller: Controller) -> list[str]:
    return [text for text, _, role, _ in full_screen_texts(controller) if role == "paragraph"]


def test_guide_first_page_texts():
    _, controller = real_controller(PieceType.T, PieceType.T)
    controller.key_down(Key.GUIDE)
    texts = screen_texts(controller)
    assert full_screen(controller) == "guide"
    assert texts[0] == "Menu and pause"
    assert texts[-2:] == ["Page 1 / 6", "Left / Right - page, Esc - close"]
    assert guide_paragraphs(controller) == list(guide.paragraphs(0, "en"))
    assert "SCORE" not in texts and "NEXT" not in texts
    controller.key_down(Key.ESCAPE)
    assert full_screen(controller) is None
    assert "SCORE" in screen_texts(controller)


def test_guide_titles_follow_the_page():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RIGHT)
    controller.key_down(Key.RIGHT)
    texts = screen_texts(controller)
    assert texts[0] == "How to play" and "Page 3 / 6" in texts
    controller.key_down(Key.LEFT)
    texts = screen_texts(controller)
    assert texts[0] == "Controls" and "Page 2 / 6" in texts


def test_every_guide_page_title():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    titles = []
    for _ in range(guide.PAGE_COUNT):
        titles.append(screen_texts(controller)[0])
        controller.key_down(Key.RIGHT)
    assert titles == ["Menu and pause", "Controls", "How to play", "Tips",
                      "Settings and sound", "High scores"]


def test_guide_in_russian():
    _, controller = menu_controller(settings=ru())
    controller.key_down(Key.GUIDE)
    texts = screen_texts(controller)
    assert texts[0] == "Меню и пауза"
    assert texts[-2:] == ["Страница 1 / 6", "Влево / Вправо - листать, Esc - закрыть"]
    assert guide_paragraphs(controller) == list(guide.paragraphs(0, "ru"))


def test_guide_titles_in_russian():
    _, controller = menu_controller(settings=ru())
    controller.key_down(Key.GUIDE)
    titles = []
    for _ in range(guide.PAGE_COUNT):
        titles.append(screen_texts(controller)[0])
        controller.key_down(Key.RIGHT)
    assert titles == ["Меню и пауза", "Управление", "Как играть", "Приёмы",
                      "Настройки и звук", "Рекорды"]


def test_guide_controls_page():
    _, controller = menu_controller()
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RIGHT)
    lines = guide_paragraphs(controller)
    assert lines == [f"{keys}: {action}" for keys, action in SPEC_HOTKEYS]
    assert len(lines) == 14
    assert lines[0] == "Left / Right: Move" and lines[-1] == "Enter: Select / new game"
    assert "F2: Guide" in lines


def test_guide_controls_page_in_russian():
    _, controller = menu_controller(settings=ru())
    controller.key_down(Key.GUIDE)
    controller.key_down(Key.RIGHT)
    lines = guide_paragraphs(controller)
    for line in ("Влево / Вправо: Сдвиг", "Пробел: Жёсткое падение", "F2: Инструкция",
                 "Enter: Выбор / новая игра"):
        assert line in lines


def test_guide_item_shows_the_first_page():
    _, controller = menu_controller()
    choose(controller, "Guide")
    texts = screen_texts(controller)
    assert texts[0] == "Menu and pause" and "Page 1 / 6" in texts


def test_controls_screen_lists_f2():
    _, controller = menu_controller()
    choose(controller, "Controls")
    texts = screen_texts(controller)
    assert ("F2", "Guide") in list(zip(texts[1:-1:2], texts[2:-1:2]))
    assert len(texts) == 1 + 2 * 14 + 1


# --- Game version in the main menu ---------------------------------------------


def version_entries(controller: Controller) -> list[tuple]:
    return [(text, pos, color)
            for text, pos, role, color in full_screen_texts(controller) if role == "version"]


def test_version_in_the_main_menu():
    _, controller = menu_controller()
    assert version_entries(controller) == [("v1.0.0", (510, 630), (130, 130, 140))]


def test_version_is_the_same_in_russian():
    _, controller = menu_controller(settings=ru())
    assert version_entries(controller) == [("v1.0.0", (510, 630), (130, 130, 140))]


@pytest.mark.parametrize("item", ["High scores", "Settings", "Controls", "Guide"])
def test_no_version_on_the_menu_screens(item):
    _, controller = menu_controller()
    choose(controller, item)
    assert "v1.0.0" not in screen_texts(controller)


def test_no_version_in_a_game():
    playing = Controller(Game(seed=1))
    paused = Controller(Game(seed=1))
    paused.key_down(Key.PAUSE)
    helped = Controller(Game(seed=1))
    helped.key_down(Key.HELP)
    guided = Controller(Game(seed=1))
    guided.key_down(Key.GUIDE)
    for controller in (playing, paused, helped, guided, Controller(finished_game()),
                       Controller(record_game())):
        assert "v1.0.0" not in screen_texts(controller)
