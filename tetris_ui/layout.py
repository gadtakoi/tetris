"""Screen layout, colors and on-screen texts, without pygame."""

from __future__ import annotations

from tetris.board import HIDDEN_ROWS, HEIGHT, VISIBLE_HEIGHT, WIDTH
from tetris.pieces import PieceType
from tetris_ui.input import Controller

WINDOW_SIZE = (520, 640)
TITLE = "Tetris"
FPS = 60

CELL = 30
FIELD_X, FIELD_Y = 20, 20
FIELD_W, FIELD_H = WIDTH * CELL, VISIBLE_HEIGHT * CELL

PANEL_X = 340
NEXT_LABEL_Y = 20
PREVIEW_X, PREVIEW_Y = PANEL_X, 60
PREVIEW_CELLS = 4
# (label, y of the label); each value is drawn 30 px below its label.
COUNTER_LABELS = (("SCORE", 220), ("LINES", 300), ("LEVEL", 380))
VALUE_OFFSET_Y = 30

Color = tuple[int, int, int]
Rect = tuple[int, int, int, int]

PIECE_COLORS: dict[PieceType, Color] = {
    PieceType.I: (0, 240, 240),
    PieceType.O: (240, 240, 0),
    PieceType.T: (160, 0, 240),
    PieceType.S: (0, 240, 0),
    PieceType.Z: (240, 0, 0),
    PieceType.J: (0, 0, 240),
    PieceType.L: (240, 160, 0),
}
WINDOW_BG: Color = (24, 24, 32)
FIELD_BG: Color = (0, 0, 0)
GRID: Color = (40, 40, 48)
BORDER: Color = (200, 200, 200)
TEXT: Color = (230, 230, 230)
CELL_OUTLINE: Color = (20, 20, 20)
OVERLAY_ALPHA = 160


def cell_rect(col: int, row: int) -> Rect:
    """Pixel rect (x, y, w, h) of a visible board cell (rows 2-21)."""
    if not (0 <= col < WIDTH and HIDDEN_ROWS <= row < HEIGHT):
        raise ValueError(f"cell ({col}, {row}) is not visible")
    return FIELD_X + CELL * col, FIELD_Y + CELL * (row - HIDDEN_ROWS), CELL, CELL


def panel_texts(controller: Controller) -> list[tuple[str, tuple[int, int]]]:
    """Side panel texts with their top-left positions."""
    game = controller.game
    values = (game.score, game.lines, game.level)
    texts = [("NEXT", (PANEL_X, NEXT_LABEL_Y))]
    for (label, y), value in zip(COUNTER_LABELS, values):
        texts.append((label, (PANEL_X, y)))
        texts.append((str(value), (PANEL_X, y + VALUE_OFFSET_Y)))
    return texts


def overlay_texts(controller: Controller) -> list[str]:
    """Lines shown centered over the field, or none during normal play."""
    if controller.game.is_over:
        return ["GAME OVER", "Press Enter"]
    if controller.paused:
        return ["PAUSE"]
    return []


def screen_texts(controller: Controller) -> list[str]:
    """Every text drawn on screen, in drawing order."""
    return [text for text, _ in panel_texts(controller)] + overlay_texts(controller)
