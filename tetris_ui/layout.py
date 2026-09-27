"""Screen layout, colors and on-screen texts, without pygame."""

from __future__ import annotations

from tetris.board import HIDDEN_ROWS, HEIGHT, VISIBLE_HEIGHT, WIDTH
from tetris.pieces import PieceType
from tetris_ui.input import Controller, Phase

WINDOW_SIZE = (520, 640)
TITLE = "SEVA Tetris"
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
MUSIC_Y, VOLUME_Y, SOUND_Y = 470, 500, 530

# The key screen (splash and F1 help): hotkeys as (keys, action), all ASCII because
# the built-in font has no arrow glyphs.
HOTKEYS: tuple[tuple[str, str], ...] = (
    ("Left / Right", "Move"),
    ("Down", "Soft drop"),
    ("Space", "Hard drop"),
    ("Up / X", "Rotate right"),
    ("Z / Ctrl", "Rotate left"),
    ("P / Esc", "Pause"),
    ("F1", "Help"),
    ("M", "Music on/off"),
    ("- / +", "Music volume"),
    ("N", "Sound on/off"),
    ("Enter", "Start / restart"),
)
SPLASH_HINT = "Press Enter to start"
HELP_HINT = "Press F1 or Enter to return"
KEY_SCREEN_TITLE_Y = 70  # center of the title
KEY_TABLE_Y, KEY_TABLE_STEP = 150, 36  # top of the first row, row pitch
KEY_COLUMN_X, ACTION_COLUMN_X = 70, 270  # left edges of the two columns
KEY_SCREEN_HINT_Y = 590  # center of the hint

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
HIGHLIGHT: Color = (240, 240, 0)
CELL_OUTLINE: Color = (20, 20, 20)
OVERLAY_ALPHA = 160
GHOST_DIVISOR = 8  # the ghost is the piece color at 1/8 brightness


def ghost_color(piece_type: PieceType) -> Color:
    """The piece color dimmed GHOST_DIVISOR times, used for the drop shadow."""
    r, g, b = PIECE_COLORS[piece_type]
    return r // GHOST_DIVISOR, g // GHOST_DIVISOR, b // GHOST_DIVISOR


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
    texts.append((f"MUSIC {_on_off(controller.music_on)}", (PANEL_X, MUSIC_Y)))
    texts.append((f"VOLUME {controller.music_volume}%", (PANEL_X, VOLUME_Y)))
    texts.append((f"SOUND {_on_off(controller.sound_on)}", (PANEL_X, SOUND_Y)))
    return texts


def _on_off(flag: bool) -> str:
    """Show a switch as "ON" or "OFF"."""
    return "ON" if flag else "OFF"


def overlay_lines(controller: Controller) -> list[tuple[str, Color]]:
    """Lines shown over the field with their colors, or none during normal play."""
    phase = controller.phase
    if phase is Phase.NAME_ENTRY:
        return [("GAME OVER", TEXT), ("NEW RECORD", TEXT), (f"Name: {controller.name}_", TEXT)]
    if phase is Phase.TABLE:
        lines = [("GAME OVER", TEXT), ("HIGH SCORES", TEXT)]
        entries = controller.scores.entries
        for place, entry in enumerate(entries, start=1):
            color = HIGHLIGHT if place == controller.highlight else TEXT
            lines.append((f"{place}. {entry.name} {entry.score}", color))
        if not entries:
            lines.append(("No records yet", TEXT))
        lines.append(("Press Enter", TEXT))
        return lines
    if controller.paused:
        return [("PAUSE", TEXT)]
    return []


def overlay_texts(controller: Controller) -> list[str]:
    """Just the texts of overlay_lines()."""
    return [text for text, _ in overlay_lines(controller)]


def key_screen(controller: Controller) -> str | None:
    """Which key screen covers the window: "splash", "help" (F1) or None."""
    if controller.phase is Phase.SPLASH:
        return "splash"
    if controller.help_open:
        return "help"
    return None


def key_screen_texts(controller: Controller) -> list[tuple[str, tuple[int, int], str]]:
    """Texts of the key screen as (text, position, role), or [] when none is shown.

    Roles: "title" and "hint" are centered on their position; "key" and "action"
    start at it (left edge, top).
    """
    screen = key_screen(controller)
    if screen is None:
        return []
    center_x = WINDOW_SIZE[0] // 2
    texts = [(TITLE, (center_x, KEY_SCREEN_TITLE_Y), "title")]
    for row, (keys, action) in enumerate(HOTKEYS):
        y = KEY_TABLE_Y + row * KEY_TABLE_STEP
        texts.append((keys, (KEY_COLUMN_X, y), "key"))
        texts.append((action, (ACTION_COLUMN_X, y), "action"))
    hint = SPLASH_HINT if screen == "splash" else HELP_HINT
    texts.append((hint, (center_x, KEY_SCREEN_HINT_Y), "hint"))
    return texts


def screen_texts(controller: Controller) -> list[str]:
    """Every text drawn on screen, in drawing order."""
    key_texts = key_screen_texts(controller)
    if key_texts:
        return [text for text, _, _ in key_texts]
    return [text for text, _ in panel_texts(controller)] + overlay_texts(controller)
