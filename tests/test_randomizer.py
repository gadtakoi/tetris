import random

from tests.helpers import ScriptedRng
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
