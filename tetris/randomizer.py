"""Uniform, seedable piece generator."""

from __future__ import annotations

import random

from tetris.pieces import PieceType

_PIECE_TYPES = list(PieceType)


class Randomizer:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def next(self) -> PieceType:
        return self._rng.choice(_PIECE_TYPES)
