import random

import pytest

from tests.helpers import ScriptedRng
from tetris.board import HEIGHT, WIDTH
from tetris.game import ActivePiece, Game, StepResult
from tetris.pieces import PieceType


def make_game(*pieces: PieceType) -> Game:
    """Game whose active piece is pieces[0], next is pieces[1], and so on."""
    return Game(rng=ScriptedRng(pieces))


def occupied(game: Game) -> set[tuple[int, int]]:
    return {
        (c, r)
        for r in range(HEIGHT)
        for c in range(WIDTH)
        if game.board.get(c, r) is not None
    }


def drop_to_bottom(game: Game) -> None:
    while game.step_down() is StepResult.MOVED:
        pass


# --- Start of a game -------------------------------------------------------


def test_new_game_state():
    game = Game(seed=1)
    assert occupied(game) == set()
    assert game.active == ActivePiece.spawn(game.active.type)
    assert game.active.rotation == 0
    assert isinstance(game.next_type, PieceType)
    assert not game.is_over


def test_restart_after_game_over():
    game = make_game(PieceType.O)
    for _ in range(100):
        if game.is_over:
            break
        drop_to_bottom(game)
    assert game.is_over
    game.new_game()
    assert occupied(game) == set()
    assert not game.is_over
    assert game.move_left()


# --- Moving left and right -------------------------------------------------


def test_move_left_on_empty_board():
    game = make_game(PieceType.T, PieceType.T)
    assert game.move_left()
    assert set(game.active.cells()) == {(3, 2), (2, 3), (3, 3), (4, 3)}


def test_left_wall_rejects_move():
    game = make_game(PieceType.T, PieceType.T)
    while game.move_left():
        pass
    assert min(c for c, _ in game.active.cells()) == 0
    before = game.active
    assert not game.move_left()
    assert game.active == before


def test_right_wall_rejects_move():
    game = make_game(PieceType.T, PieceType.T)
    while game.move_right():
        pass
    assert max(c for c, _ in game.active.cells()) == 9
    before = game.active
    assert not game.move_right()
    assert game.active == before


def test_occupied_cell_rejects_move():
    game = make_game(PieceType.T, PieceType.T)
    game.board.place([(2, 3)], PieceType.Z)  # left of the T's (3, 3) cell
    before = game.active
    assert not game.move_left()
    assert game.active == before


# --- Rotation --------------------------------------------------------------


def test_rotate_on_empty_board():
    game = make_game(PieceType.T, PieceType.T)
    assert game.rotate_cw()
    assert game.active.rotation == 1
    assert set(game.active.cells()) == {(4, 2), (4, 3), (5, 3), (4, 4)}


def test_rotation_against_wall_is_rejected():
    game = make_game(PieceType.I, PieceType.I)
    game.step_down()
    assert game.rotate_cw()
    while game.move_left():
        pass
    assert {c for c, _ in game.active.cells()} == {0}
    before = game.active
    assert not game.rotate_cw()
    assert game.active == before


def test_rotation_into_hidden_rows_is_allowed():
    game = make_game(PieceType.I, PieceType.I)
    assert game.rotate_cw()
    assert set(game.active.cells()) == {(5, 1), (5, 2), (5, 3), (5, 4)}


def test_rotate_ccw_undoes_cw():
    game = make_game(PieceType.L, PieceType.L)
    before = game.active
    assert game.rotate_cw()
    assert game.rotate_ccw()
    assert game.active == before


# --- Stepping down and locking ---------------------------------------------


def test_step_down_on_empty_board():
    game = make_game(PieceType.T, PieceType.T)
    assert game.step_down() is StepResult.MOVED
    assert set(game.active.cells()) == {(4, 3), (3, 4), (4, 4), (5, 4)}


def test_lock_on_floor():
    game = make_game(PieceType.O, PieceType.J, PieceType.S)
    drop_to_bottom(game)
    assert occupied(game) == {(4, 20), (5, 20), (4, 21), (5, 21)}
    assert all(game.board.get(*cell) is PieceType.O for cell in occupied(game))
    assert game.active == ActivePiece.spawn(PieceType.J)


def test_step_down_at_floor_locks_instead_of_moving():
    game = make_game(PieceType.O, PieceType.O)
    for _ in range(18):
        assert game.step_down() is StepResult.MOVED
    assert max(r for _, r in game.active.cells()) == 21
    assert game.step_down() is StepResult.LOCKED


def test_lock_on_top_of_another_piece():
    game = make_game(PieceType.O, PieceType.O)
    game.board.place([(4, 10)], PieceType.Z)
    drop_to_bottom(game)
    assert {(4, 8), (5, 8), (4, 9), (5, 9)} <= occupied(game)


def test_next_piece_becomes_active():
    game = make_game(PieceType.T, PieceType.S, PieceType.Z)
    assert game.next_type is PieceType.S
    drop_to_bottom(game)
    assert game.active.type is PieceType.S
    assert game.next_type is PieceType.Z


# --- Game over -------------------------------------------------------------


def test_block_out_ends_game():
    game = make_game(PieceType.T, PieceType.O)
    for _ in range(3):
        assert game.move_left()
    assert set(game.active.cells()) == {(1, 2), (0, 3), (1, 3), (2, 3)}
    game.board.place([(0, 4), (1, 4), (2, 4)], PieceType.Z)  # T lands right away
    game.board.place([(4, 3)], PieceType.Z)  # inside O's spawn cells
    assert game.step_down() is StepResult.LOCKED
    assert game.is_over


def test_no_game_over_when_spawn_is_free():
    game = make_game(PieceType.T, PieceType.O)
    drop_to_bottom(game)
    assert not game.is_over
    assert game.active == ActivePiece.spawn(PieceType.O)


def test_commands_rejected_after_game_over():
    game = make_game(PieceType.O)
    while not game.is_over:
        drop_to_bottom(game)
    board_before = occupied(game)
    active_before = game.active
    next_before = game.next_type
    assert not game.move_left()
    assert not game.move_right()
    assert not game.rotate_cw()
    assert not game.rotate_ccw()
    assert game.step_down() is StepResult.REJECTED
    assert occupied(game) == board_before
    assert game.active == active_before
    assert game.next_type is next_before


# --- Invariants under random play ------------------------------------------


@pytest.mark.parametrize("seed", range(20))
def test_random_play_keeps_invariants(seed):
    game = Game(seed=seed)
    commands = [
        game.move_left,
        game.move_right,
        game.rotate_cw,
        game.rotate_ccw,
        game.step_down,
    ]
    actions = random.Random(1000 + seed)
    for _ in range(500):
        actions.choice(commands)()
        if not game.is_over:
            assert all(game.board.is_free(c, r) for c, r in game.active.cells())
        for r in range(HEIGHT):
            row_filled = sum(game.board.get(c, r) is not None for c in range(WIDTH))
            assert row_filled <= WIDTH
