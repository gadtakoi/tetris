import pytest

from tests.helpers import ScriptedRng
from tetris.game import Game, StepResult
from tetris.pieces import PieceType
from tetris_ui.input import Controller, Key, KeyRepeater
from tetris_ui.layout import cell_rect, screen_texts


class FakeGame:
    """Records the commands the controller sends."""

    def __init__(self) -> None:
        self.is_over = False
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
    for key in (Key.LEFT, Key.RIGHT, Key.DOWN, Key.ROTATE_CW, Key.ROTATE_CCW):
        controller.key_down(key)
    controller.update(16)
    assert game.calls == []
    assert game.ticks == []


def finished_game() -> Game:
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        while game.step_down() is StepResult.MOVED:
            pass
    return game


def test_enter_restarts_after_game_over():
    game = finished_game()
    game.score, game.lines, game.level = 340, 5, 0
    controller = Controller(game)
    controller.key_down(Key.RESTART)
    assert not game.is_over
    assert (game.score, game.lines, game.level) == (0, 0, 0)
    assert all(cell is None for row in game.board.visible_rows() for cell in row)


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
        "NEXT", "SCORE", "1200", "LINES", "13", "LEVEL", "1",
    ]


def test_texts_on_pause():
    controller = Controller(Game(seed=1))
    controller.key_down(Key.PAUSE)
    assert screen_texts(controller)[-1] == "PAUSE"


def test_texts_after_game_over():
    game = finished_game()
    game.score = 340
    controller = Controller(game)
    texts = screen_texts(controller)
    assert texts[-2:] == ["GAME OVER", "Press Enter"]
    assert "340" in texts
    controller.key_down(Key.RESTART)
    assert "GAME OVER" not in screen_texts(controller)
    assert "Press Enter" not in screen_texts(controller)
