"""Seedable 7-bag piece generator."""

from __future__ import annotations

import random

from tetris.pieces import PieceType


class Randomizer:
    """Deals pieces in bags of seven: every type once per bag, in random order.

    The order comes from the given random.Random, so a seeded rng gives a
    reproducible sequence.
    """

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._bag: list[PieceType] = []

    def next(self) -> PieceType:
        """The next piece type, opening a freshly shuffled bag when the last one is empty."""
        if not self._bag:
            self._bag = list(PieceType)
            self._rng.shuffle(self._bag)
        return self._bag.pop(0)

    def reset(self) -> None:
        """Drop the rest of the current bag, so the next piece opens a new one."""
        self._bag = []
