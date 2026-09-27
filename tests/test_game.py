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


def fill_rows(game: Game, rows: range, cols: range, piece_type=PieceType.J) -> None:
    game.board.place([(c, r) for r in rows for c in cols], piece_type)


def clear_single_row_with_o(game: Game) -> None:
    """Active O drops into the gap at columns 8-9 of a row 21 filled in 0-7."""
    assert game.active.type is PieceType.O
    fill_rows(game, range(21, 22), range(8))
    for _ in range(4):
        assert game.move_right()
    drop_to_bottom(game)


def vertical_i_at_right_wall(game: Game) -> None:
    """Turn the freshly spawned I upright and push it into column 9."""
    assert game.active.type is PieceType.I
    assert game.rotate_cw()
    for _ in range(4):
        assert game.move_right()
    assert {c for c, _ in game.active.cells()} == {9}


# --- Start of a game -------------------------------------------------------


def test_new_game_state():
    game = Game(seed=1)
    assert occupied(game) == set()
    assert game.active == ActivePiece.spawn(game.active.type)
    assert game.active.rotation == 0
    assert isinstance(game.next_type, PieceType)
    assert not game.is_over
    assert (game.score, game.lines, game.level, game.last_cleared) == (0, 0, 0, 0)


def test_restart_after_game_over():
    game = make_game(PieceType.O)
    clear_single_row_with_o(game)
    for _ in range(100):
        if game.is_over:
            break
        drop_to_bottom(game)
    assert game.is_over
    assert (game.score, game.lines) == (40, 1)
    game.new_game()
    assert occupied(game) == set()
    assert not game.is_over
    assert (game.score, game.lines, game.level, game.last_cleared) == (0, 0, 0, 0)
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


# --- Line clears and scoring ----------------------------------------------


def test_lock_clears_single_row():
    game = make_game(PieceType.O, PieceType.T)
    clear_single_row_with_o(game)
    assert occupied(game) == {(8, 21), (9, 21)}
    assert game.board.get(8, 21) is PieceType.O
    assert (game.score, game.lines, game.level, game.last_cleared) == (40, 1, 0, 1)


def test_lock_clears_four_rows():
    game = make_game(PieceType.I, PieceType.T)
    vertical_i_at_right_wall(game)
    fill_rows(game, range(18, 22), range(9))
    drop_to_bottom(game)
    assert occupied(game) == set()
    assert (game.score, game.lines, game.last_cleared) == (1200, 4, 4)


def test_lock_without_full_rows_scores_nothing():
    game = make_game(PieceType.O, PieceType.T, PieceType.T)
    clear_single_row_with_o(game)
    assert game.last_cleared == 1
    drop_to_bottom(game)
    assert game.last_cleared == 0
    assert (game.score, game.lines) == (40, 1)


def test_level_up_after_tenth_line():
    game = make_game(PieceType.O, PieceType.T)
    game.lines = 8
    fill_rows(game, range(20, 21), range(8))
    clear_single_row_with_o(game)
    assert (game.score, game.lines, game.level, game.last_cleared) == (100, 10, 1, 2)


def test_points_use_level_before_the_lock():
    game = make_game(PieceType.I, PieceType.T)
    game.lines = 9
    vertical_i_at_right_wall(game)
    fill_rows(game, range(18, 22), range(9))
    drop_to_bottom(game)
    assert (game.score, game.lines, game.level) == (1200, 13, 1)


def test_counters_kept_after_game_over():
    game = make_game(PieceType.O)
    game.score, game.lines = 340, 5
    while not game.is_over:
        drop_to_bottom(game)
    assert (game.score, game.lines, game.level) == (340, 5, 0)


def test_rows_cleared_before_next_piece_spawns():
    game = make_game(PieceType.I, PieceType.T)
    vertical_i_at_right_wall(game)
    assert set(game.active.cells()) == {(9, 1), (9, 2), (9, 3), (9, 4)}
    fill_rows(game, range(3, 4), range(9))  # covers T's spawn cells in row 3
    game.board.place([(9, 5)], PieceType.Z)  # I cannot move down
    assert game.step_down() is StepResult.LOCKED
    assert game.last_cleared == 1
    assert not game.is_over
    assert game.active == ActivePiece.spawn(PieceType.T)
    assert occupied(game) == {(9, 2), (9, 3), (9, 4), (9, 5)}


# --- Gravity ---------------------------------------------------------------

T_SPAWN_CELLS = {(4, 2), (3, 3), (4, 3), (5, 3)}
T_ONE_ROW_DOWN = {(4, 3), (3, 4), (4, 4), (5, 4)}


def lower_o_to_floor(game: Game) -> None:
    """Step the freshly spawned O down until it rests on row 21 without locking."""
    assert game.active.type is PieceType.O
    for _ in range(18):
        assert game.step_down() is StepResult.MOVED
    assert max(r for _, r in game.active.cells()) == 21


def test_gravity_waits_for_the_interval():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(799)
    assert set(game.active.cells()) == T_SPAWN_CELLS


def test_gravity_accumulates_across_ticks():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(799)
    game.tick(1)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_one_tick_can_apply_several_steps():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(1600)
    assert game.active.row == ActivePiece.spawn(PieceType.T).row + 2


def test_gravity_interval_is_exact_on_level_1():
    game = make_game(PieceType.T, PieceType.T)
    game.lines, game.level = 10, 1
    game.tick(716)
    assert set(game.active.cells()) == T_SPAWN_CELLS
    game.tick(1)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_zero_tick_changes_nothing():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(799)
    game.tick(0)
    assert set(game.active.cells()) == T_SPAWN_CELLS


def test_negative_tick_is_rejected_without_changes():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(400)
    with pytest.raises(ValueError):
        game.tick(-1)
    assert set(game.active.cells()) == T_SPAWN_CELLS
    game.tick(399)
    assert set(game.active.cells()) == T_SPAWN_CELLS
    game.tick(1)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_gravity_locks_piece_on_floor():
    game = make_game(PieceType.O, PieceType.T)
    lower_o_to_floor(game)
    game.tick(800)
    assert occupied(game) == {(4, 20), (5, 20), (4, 21), (5, 21)}
    assert game.active == ActivePiece.spawn(PieceType.T)


def test_leftover_time_after_lock_is_dropped():
    game = make_game(PieceType.O, PieceType.T)
    lower_o_to_floor(game)
    game.tick(1500)
    assert game.active == ActivePiece.spawn(PieceType.T)
    game.tick(799)
    assert game.active == ActivePiece.spawn(PieceType.T)
    game.tick(1)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_player_step_down_restarts_gravity_interval():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(500)
    assert game.step_down() is StepResult.MOVED
    game.tick(500)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_move_does_not_restart_gravity_interval():
    game = make_game(PieceType.T, PieceType.T)
    game.tick(500)
    assert game.move_left()
    game.tick(300)
    assert set(game.active.cells()) == {(c - 1, r) for c, r in T_ONE_ROW_DOWN}


def test_new_game_restarts_gravity_interval():
    game = make_game(PieceType.T, PieceType.T, PieceType.T)
    game.tick(500)
    game.new_game()
    game.tick(500)
    assert game.active == ActivePiece.spawn(game.active.type)


def test_level_up_speeds_up_the_next_piece():
    game = make_game(PieceType.O, PieceType.T)
    game.lines = 9
    fill_rows(game, range(21, 22), range(8))
    for _ in range(4):
        assert game.move_right()
    lower_o_to_floor(game)
    game.tick(800)
    assert (game.lines, game.level) == (10, 1)
    assert game.active == ActivePiece.spawn(PieceType.T)
    game.tick(716)
    assert set(game.active.cells()) == T_SPAWN_CELLS
    game.tick(1)
    assert set(game.active.cells()) == T_ONE_ROW_DOWN


def test_time_after_game_over_changes_nothing():
    game = make_game(PieceType.O)
    while not game.is_over:
        drop_to_bottom(game)
    before = (occupied(game), game.active, game.next_type, game.score, game.lines, game.level)
    game.tick(10_000)
    after = (occupied(game), game.active, game.next_type, game.score, game.lines, game.level)
    assert after == before


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
    prev_score, prev_lines = 0, 0
    for _ in range(500):
        actions.choice(commands)()
        if not game.is_over:
            assert all(game.board.is_free(c, r) for c, r in game.active.cells())
        for r in range(HEIGHT):
            row_filled = sum(game.board.get(c, r) is not None for c in range(WIDTH))
            assert row_filled < WIDTH  # full rows never survive a lock
        assert game.level == game.lines // 10
        assert 0 <= game.last_cleared <= 4
        assert game.score >= prev_score and game.lines >= prev_lines
        prev_score, prev_lines = game.score, game.lines


def assert_consistent(game: Game) -> None:
    if not game.is_over:
        assert all(game.board.is_free(c, r) for c, r in game.active.cells())
    for r in range(HEIGHT):
        assert sum(game.board.get(c, r) is not None for c in range(WIDTH)) < WIDTH
    assert game.level == game.lines // 10


@pytest.mark.parametrize("seed", range(20))
def test_random_play_with_gravity_keeps_invariants(seed):
    game = Game(seed=seed)
    commands = [
        game.move_left,
        game.move_right,
        game.rotate_cw,
        game.rotate_ccw,
        game.step_down,
    ]
    actions = random.Random(2000 + seed)
    for _ in range(1000):
        if actions.random() < 0.5:
            game.tick(actions.randint(0, 200))
        else:
            actions.choice(commands)()
        assert_consistent(game)


def test_gravity_alone_ends_the_game():
    game = Game(seed=7)
    for _ in range(200_000):
        if game.is_over:
            break
        game.tick(16)
        assert_consistent(game)
    assert game.is_over
