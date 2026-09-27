import random
from collections.abc import Iterable, Sequence

from tetris.pieces import PieceType


class ScriptedRng(random.Random):
    """RNG that deals a scripted sequence of piece types.

    shuffle() fills the bag it is given with the next scripted pieces, so the
    7-bag randomizer hands out exactly the script, repeats included; choice()
    returns the next scripted piece. After the script runs out it keeps
    returning the last piece.
    """

    def __init__(self, pieces: Iterable[PieceType]) -> None:
        super().__init__(0)
        self._pieces = list(pieces)
        self._index = 0

    def _next_piece(self) -> PieceType:
        piece = self._pieces[min(self._index, len(self._pieces) - 1)]
        self._index += 1
        return piece

    def choice(self, seq: Sequence):
        piece = self._next_piece()
        assert piece in seq
        return piece

    def shuffle(self, x: list) -> None:
        x[:] = [self._next_piece() for _ in x]
