import random
from collections.abc import Iterable, Sequence

from tetris.pieces import PieceType


class ScriptedRng(random.Random):
    """RNG whose choice() returns a scripted sequence of piece types.

    After the script runs out it keeps returning the last piece.
    """

    def __init__(self, pieces: Iterable[PieceType]) -> None:
        super().__init__(0)
        self._pieces = list(pieces)
        self._index = 0

    def choice(self, seq: Sequence):
        piece = self._pieces[min(self._index, len(self._pieces) - 1)]
        self._index += 1
        assert piece in seq
        return piece
