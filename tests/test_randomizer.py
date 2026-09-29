import random

import pytest

from tests.helpers import ScriptedRng
from tetris.game import Game
from tetris.pieces import PieceType
from tetris.randomizer import Randomizer


def _sequence(randomizer: Randomizer, count: int) -> list[PieceType]:
    return [randomizer.next() for _ in range(count)]


def test_same_seed_gives_same_sequence():
    first = _sequence(Randomizer(random.Random(42)), 100)
    second = _sequence(Randomizer(random.Random(42)), 100)
    assert first == second


def test_all_types_appear_in_700_pieces():
    pieces = _sequence(Randomizer(random.Random(7)), 700)
    assert set(pieces) == set(PieceType)


def test_scripted_rng_drives_sequence():
    script = [PieceType.S, PieceType.I, PieceType.O, PieceType.T]
    assert _sequence(Randomizer(ScriptedRng(script)), 4) == script


# --- 7-bag -----------------------------------------------------------------


@pytest.mark.parametrize("seed", range(20))
def test_every_group_of_seven_is_a_full_bag(seed):
    pieces = _sequence(Randomizer(random.Random(seed)), 70)
    for start in range(0, 70, 7):
        assert sorted(p.value for p in pieces[start:start + 7]) == sorted(p.value for p in PieceType)


@pytest.mark.parametrize("seed", range(20))
def test_no_long_droughts_or_floods(seed):
    pieces = _sequence(Randomizer(random.Random(seed)), 700)
    last_seen: dict[PieceType, int] = {}
    run = 1
    for index, piece in enumerate(pieces):
        if piece in last_seen:
            assert index - last_seen[piece] - 1 <= 12  # other pieces in between
        last_seen[piece] = index
        run = run + 1 if index and pieces[index - 1] is piece else 1
        assert run <= 2


def game_sequence(game: Game, count: int) -> list[PieceType]:
    """The pieces a game deals: its active piece and queue, then the following ones."""
    dealt = [game.active.type, *game.next_types]
    return dealt + [game._randomizer.next() for _ in range(count - len(dealt))]


def test_new_game_starts_a_new_bag():
    for seed in range(20):
        game = Game(seed=seed)
        game._randomizer.next()  # five pieces dealt: active, queue and one more
        game.new_game()
        assert set(game_sequence(game, 7)) == set(PieceType)


def test_games_with_the_same_seed_deal_the_same_pieces():
    assert game_sequence(Game(seed=5), 100) == game_sequence(Game(seed=5), 100)


def test_scripted_rng_still_scripts_the_game():
    game = Game(rng=ScriptedRng([PieceType.O, PieceType.O, PieceType.I]))
    assert (game.active.type, game.next_type) == (PieceType.O, PieceType.O)
