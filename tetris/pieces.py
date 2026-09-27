"""Tetromino shapes, rotation states and spawn positions."""

from __future__ import annotations

from enum import Enum

# A cell inside a piece's bounding box, as (row, col) from its top-left corner.
BoxCell = tuple[int, int]


class PieceType(Enum):
    """The seven tetrominoes, named after the letters they look like."""

    I = "I"
    O = "O"
    T = "T"
    S = "S"
    Z = "Z"
    J = "J"
    L = "L"


# Bounding box size and cells of orientation 0 for each piece.
_BASE_SHAPES: dict[PieceType, tuple[int, tuple[BoxCell, ...]]] = {
    PieceType.I: (4, ((1, 0), (1, 1), (1, 2), (1, 3))),
    PieceType.O: (4, ((0, 1), (0, 2), (1, 1), (1, 2))),
    PieceType.T: (3, ((0, 1), (1, 0), (1, 1), (1, 2))),
    PieceType.S: (3, ((0, 1), (0, 2), (1, 0), (1, 1))),
    PieceType.Z: (3, ((0, 0), (0, 1), (1, 1), (1, 2))),
    PieceType.J: (3, ((0, 0), (1, 0), (1, 1), (1, 2))),
    PieceType.L: (3, ((0, 2), (1, 0), (1, 1), (1, 2))),
}

ROTATION_COUNT = 4

SPAWN_COL = 3
SPAWN_ROW = 2
SPAWN_ROW_I = 1


def _rotate_cw(cells: tuple[BoxCell, ...], size: int) -> tuple[BoxCell, ...]:
    """Rotate box cells 90 degrees clockwise: (r, c) -> (c, N - 1 - r)."""
    return tuple(sorted((c, size - 1 - r) for r, c in cells))


def _build_rotations() -> dict[PieceType, tuple[tuple[BoxCell, ...], ...]]:
    """Precompute the four orientations of every piece from its orientation 0."""
    rotations = {}
    for piece_type, (size, base) in _BASE_SHAPES.items():
        states = [tuple(sorted(base))]
        for _ in range(ROTATION_COUNT - 1):
            # O is rotation-invariant; the formula would shift it inside its 4x4 box.
            if piece_type is PieceType.O:
                states.append(states[0])
            else:
                states.append(_rotate_cw(states[-1], size))
        rotations[piece_type] = tuple(states)
    return rotations


_ROTATIONS = _build_rotations()


def box_size(piece_type: PieceType) -> int:
    """Side of the piece's square bounding box: 4 for I and O, 3 for the others."""
    return _BASE_SHAPES[piece_type][0]


def shape_cells(piece_type: PieceType, rotation: int) -> tuple[BoxCell, ...]:
    """Return the (row, col) box cells of a piece in the given orientation."""
    return _ROTATIONS[piece_type][rotation % ROTATION_COUNT]


def spawn_position(piece_type: PieceType) -> tuple[int, int]:
    """Return the (col, row) of the bounding box's top-left corner at spawn."""
    row = SPAWN_ROW_I if piece_type is PieceType.I else SPAWN_ROW
    return SPAWN_COL, row


# SRS wall kicks: (from, to) orientation -> the four offsets tried after the
# in-place rotation, as (dx, dy) in cells with dy pointing UP, as in the SRS tables.
Offset = tuple[int, int]

_JLSTZ_KICKS: dict[tuple[int, int], tuple[Offset, ...]] = {
    (0, 1): ((-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (1, 0): ((1, 0), (1, -1), (0, 2), (1, 2)),
    (1, 2): ((1, 0), (1, -1), (0, 2), (1, 2)),
    (2, 1): ((-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (2, 3): ((1, 0), (1, 1), (0, -2), (1, -2)),
    (3, 2): ((-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (3, 0): ((-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (0, 3): ((1, 0), (1, 1), (0, -2), (1, -2)),
}

_I_KICKS: dict[tuple[int, int], tuple[Offset, ...]] = {
    (0, 1): ((-2, 0), (1, 0), (-2, -1), (1, 2)),
    (1, 0): ((2, 0), (-1, 0), (2, 1), (-1, -2)),
    (1, 2): ((-1, 0), (2, 0), (-1, 2), (2, -1)),
    (2, 1): ((1, 0), (-2, 0), (1, -2), (-2, 1)),
    (2, 3): ((2, 0), (-1, 0), (2, 1), (-1, -2)),
    (3, 2): ((-2, 0), (1, 0), (-2, -1), (1, 2)),
    (3, 0): ((1, 0), (-2, 0), (1, -2), (-2, 1)),
    (0, 3): ((-1, 0), (2, 0), (-1, 2), (2, -1)),
}


def kick_offsets(piece_type: PieceType, from_rotation: int, to_rotation: int) -> tuple[Offset, ...]:
    """Positions to try for a rotation: in place first, then the four SRS kicks.

    Offsets are (dx, dy) with dy pointing up; O never kicks.
    """
    if piece_type is PieceType.O:
        return ((0, 0),)
    table = _I_KICKS if piece_type is PieceType.I else _JLSTZ_KICKS
    key = (from_rotation % ROTATION_COUNT, to_rotation % ROTATION_COUNT)
    return ((0, 0),) + table[key]
