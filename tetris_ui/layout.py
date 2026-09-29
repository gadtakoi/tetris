"""Screen layout, colors, fonts of the texts and on-screen texts, without pygame.

The look follows the "Stopka" mockup: an orange window, the well in the middle, cream
cards with a hard shadow (no blur) on both sides, Unbounded for titles and numbers and
Onest for everything else. Every rectangle is (x, y, w, h) in window pixels.
"""

from __future__ import annotations

from typing import NamedTuple

from tetris.board import HIDDEN_ROWS, HEIGHT, VISIBLE_HEIGHT, WIDTH
from tetris.pieces import PieceType, shape_cells
from tetris_ui import GAME_TITLE, __version__, guide, menus, soundcheck
from tetris_ui.input import Controller, Phase
from tetris_ui.settings import DEFAULT_SFX_VOLUME, DEFAULT_VOLUME
from tetris_ui.texts import (
    check_volume_text,
    music_volume_text,
    name_line,
    page_line,
    sound_volume_text,
    tr,
)

WINDOW_SIZE = (960, 720)
TITLE = GAME_TITLE
FPS = 60

Color = tuple[int, int, int]
Rect = tuple[int, int, int, int]
Point = tuple[int, int]


def blend(fg: Color, bg: Color, alpha: float) -> Color:
    """fg laid over bg with the given opacity (0-1), each channel rounded half up."""
    return tuple(int(b + (f - b) * alpha + 0.5) for f, b in zip(fg, bg))  # type: ignore[return-value]


# --- Palette -----------------------------------------------------------------

WINDOW_BG: Color = (232, 86, 42)  # orange, as the icon
WELL: Color = (217, 73, 29)  # the well and the preview boxes
SHADOW: Color = (184, 58, 20)  # hard shadows of cards, panels, buttons and keys
CREAM: Color = (255, 244, 230)  # cards and panels
PEACH: Color = (255, 197, 158)  # the accent: badges, the logo's heel, the version
INK: Color = (38, 10, 2)  # text and dark buttons
MUTED: Color = blend(INK, CREAM, 0.72)  # card labels and hints on a panel

TEXT: Color = INK
HIGHLIGHT: Color = CREAM  # the text of a selected item, drawn on a dark button
HINT_COLOR: Color = CREAM  # hints under a full-window panel, on the orange background
VERSION_COLOR: Color = PEACH
NOTE_COLOR: Color = MUTED  # the sound check's volume and report lines
MARK_COLOR: Color = (155, 34, 51)  # "unpleasant" next to a marked sound check row
GRID_DOT: Color = blend(SHADOW, WELL, 0.35)
GHOST_OUTLINE: Color = blend(CREAM, WELL, 0.5)
SHADE_ALPHA = 199  # the well is shaded with its own color at 78 % on pause and game over
DIM_ALPHA = 0.4  # a held piece that cannot be swapped now: 40 % piece, 60 % well


class PieceColors(NamedTuple):
    """A piece type's fill and the color of its hard shadow."""

    fill: Color
    shadow: Color


PIECE_COLORS: dict[PieceType, PieceColors] = {
    PieceType.I: PieceColors((255, 244, 230), (184, 58, 20)),
    PieceType.O: PieceColors((255, 213, 74), (169, 80, 12)),
    PieceType.T: PieceColors((255, 158, 176), (163, 48, 74)),
    PieceType.S: PieceColors((255, 181, 102), (164, 72, 17)),
    PieceType.Z: PieceColors((155, 34, 51), (77, 11, 20)),
    PieceType.J: PieceColors((110, 50, 28), (46, 18, 8)),
    PieceType.L: PieceColors((255, 197, 158), (176, 64, 26)),
}


def dimmed_colors(piece_type: PieceType) -> PieceColors:
    """A held piece's colors while it cannot be swapped: fill and shadow mixed into the well."""
    fill, shadow = PIECE_COLORS[piece_type]
    return PieceColors(blend(fill, WELL, DIM_ALPHA), blend(shadow, WELL, DIM_ALPHA))


# --- The well and the field ----------------------------------------------------

CELL = 30
FIELD_X, FIELD_Y = 330, 60
FIELD_W, FIELD_H = WIDTH * CELL, VISIBLE_HEIGHT * CELL
WELL_PAD = 12
WELL_RECT: Rect = (FIELD_X - WELL_PAD, FIELD_Y - WELL_PAD, FIELD_W + 2 * WELL_PAD,
                   FIELD_H + 2 * WELL_PAD)
WELL_RADIUS = 22
GRID_DOT_RADIUS = 2
GHOST_WIDTH = 2  # the ghost's outline
GHOST_RADIUS = 5


class Block(NamedTuple):
    """How a cell of `size` pixels is drawn: a rounded square inset from the cell's
    corner, and the same square in the shadow color moved right and down by `shift`."""

    inset: int
    side: int
    radius: int
    shift: int


def block(size: int) -> Block:
    """The block of a cell `size` pixels wide, as in the mockup: a 1 px gap on each side,
    corners at a fifth of the side, the shadow moved by 16 % of the cell."""
    side = size - 2
    return Block(1, side, round(0.2 * side), round(0.16 * size))


def cell_rect(col: int, row: int) -> Rect:
    """Pixel rect (x, y, w, h) of a visible board cell (rows 2-21)."""
    if not (0 <= col < WIDTH and HIDDEN_ROWS <= row < HEIGHT):
        raise ValueError(f"cell ({col}, {row}) is not visible")
    return FIELD_X + CELL * col, FIELD_Y + CELL * (row - HIDDEN_ROWS), CELL, CELL


def ghost_rect(col: int, row: int) -> Rect:
    """The outer square of a ghost cell's outline, 2 px inside the cell on every side."""
    x, y, _, _ = cell_rect(col, row)
    return x + 2, y + 2, CELL - 4, CELL - 4


def grid_dots() -> list[Point]:
    """Centers of the grid dots: where the inner cell borders cross."""
    return [(FIELD_X + CELL * i, FIELD_Y + CELL * j)
            for j in range(1, VISIBLE_HEIGHT) for i in range(1, WIDTH)]


# --- Cards -----------------------------------------------------------------------

CARD_RADIUS = 16
CARD_LIFT = 6  # how far the hard shadow of a card is moved right and down
CARD_PAD_X = 16
LABEL_DY, VALUE_DY = 14, 36  # label and value tops below the card's top

LOGO_RECT: Rect = (40, 48, 52, 52)
BRAND_POS: Point = (104, 74)  # left edge and vertical middle of the game's name
BRAND_W = 176
SCORE_CARD: Rect = (40, 120, 240, 96)
LEVEL_CARD: Rect = (40, 236, 112, 80)
LINES_CARD: Rect = (168, 236, 112, 80)
BEST_CARD: Rect = (40, 336, 240, 80)
SOUND_CARD: Rect = (40, 436, 240, 136)
SOUND_LINE_YS = (452, 480, 508, 536)
NEXT_CARD: Rect = (680, 48, 240, 262)
HOLD_CARD: Rect = (680, 330, 240, 116)
CONTROLS_CARD: Rect = (680, 466, 240, 206)
CARDS: tuple[Rect, ...] = (SCORE_CARD, LEVEL_CARD, LINES_CARD, BEST_CARD, SOUND_CARD,
                           NEXT_CARD, HOLD_CARD, CONTROLS_CARD)

BOX_W, BOX_H = 132, 64  # a preview box
BOX_RADIUS = 11
NEXT_BOXES: tuple[Rect, ...] = tuple((734, y, BOX_W, BOX_H) for y in (88, 158, 228))
HOLD_BOX: Rect = (734, 370, BOX_W, BOX_H)
PREVIEW_CELL = 22

# The controls card: rows of keys and actions, keys from the left, actions in a column.
CONTROL_ROWS_Y, CONTROL_ROW_STEP = 504, 22
CONTROL_KEYS_X = CONTROLS_CARD[0] + CARD_PAD_X
CONTROL_ACTION_X = 780
CONTROL_KEY_H = 20  # height of a key on the card


def card_inner_width(card: Rect) -> int:
    """How wide a text in a card may be: the card less its side paddings."""
    return card[2] - 2 * CARD_PAD_X


def preview_blocks(piece_type: PieceType, box: Rect) -> list[Point]:
    """Top-left corners of a piece's cells in orientation 0, centered in a preview box
    (with its shadow)."""
    cells = shape_cells(piece_type, 0)
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    shift = block(PREVIEW_CELL).shift
    width = (max(cols) - min(cols) + 1) * PREVIEW_CELL + shift
    height = (max(rows) - min(rows) + 1) * PREVIEW_CELL + shift
    x0 = box[0] + (box[2] - width) // 2 - min(cols) * PREVIEW_CELL
    y0 = box[1] + (box[3] - height) // 2 - min(rows) * PREVIEW_CELL
    return [(x0 + c * PREVIEW_CELL, y0 + r * PREVIEW_CELL) for r, c in cells]


# --- Panel over the well (pause, game over) -----------------------------------------

OVERLAY_PANEL_W = 284
OVERLAY_PANEL_X = FIELD_X + (FIELD_W - OVERLAY_PANEL_W) // 2
OVERLAY_PAD_X, OVERLAY_PAD_Y = 22, 24
OVERLAY_INNER_X = OVERLAY_PANEL_X + OVERLAY_PAD_X
OVERLAY_INNER_W = OVERLAY_PANEL_W - 2 * OVERLAY_PAD_X
OVERLAY_CENTER_Y = WELL_RECT[1] + WELL_RECT[3] // 2
PANEL_RADIUS = 20
PANEL_LIFT = 8
# Height of each kind of line over the well and the space after it.
OVERLAY_LINES: dict[str, tuple[int, int]] = {
    "overlay-title": (36, 16),
    "pause-item": (44, 10),
    "badge": (28, 10),
    "name": (26, 4),
    "table-label": (20, 8),
    "table-row": (26, 0),
    "table-hint": (20, 2),
}
BUTTON_PAD_X = 18  # text inside a pause button
# A peach plaque around a text. 4 px at the sides leaves the longest table row a few pixels
# to spare at 14 px: Linux's FreeType draws it 1 px wider than Windows'.
PLAQUE_PAD_X, PLAQUE_PAD_Y = 4, 3

# --- Full-window screens ------------------------------------------------------------

SCREEN_PANEL: Rect = (160, 40, 640, 600)
SCREEN_RADIUS = 24
SCREEN_TEXT_X = SCREEN_PANEL[0] + 40
SCREEN_TEXT_W = SCREEN_PANEL[2] - 80
CENTER_X = WINDOW_SIZE[0] // 2
MENU_LOGO_RECT: Rect = (448, 64, 64, 64)
MENU_TITLE_Y = 168
MENU_ITEMS_Y, MENU_ITEMS_STEP = 250, 58
SCREEN_TITLE_Y = 100  # high scores, settings, key list, guide
SCORES_ROWS_Y, SCORES_ROWS_STEP = 168, 40
SETTINGS_ROWS_Y, SETTINGS_ROWS_STEP = 160, 50
KEY_TABLE_Y, KEY_TABLE_STEP = 146, 30  # top of the first row, row pitch
KEY_COLUMN_X, ACTION_COLUMN_X = 220, 440  # left edges of the two columns
KEY_H = 26  # height of a key in the key list
SCREEN_HINT_Y = 680  # under the panel
# The guide: paragraphs from the top-left corner of the text area (render wraps them at
# spaces into lines GUIDE_LINE_STEP apart, with an extra gap between paragraphs), then
# the page number inside the panel and the hint under it.
GUIDE_TEXT_X, GUIDE_TEXT_Y = SCREEN_TEXT_X, 150
GUIDE_LINE_STEP = 24
GUIDE_PARAGRAPH_GAP = 6
GUIDE_PAGE_Y = 604
VERSION_POS: Point = (944, 708)  # bottom-right corner of the version in the main menu
# The sound check: everything inside the panel, rows from the top-left corner of the
# first one with the marks in a column to their right.
CHECK_TITLE_Y = 84
CHECK_ROWS_X, CHECK_ROWS_Y, CHECK_ROWS_STEP = SCREEN_TEXT_X, 120, 26
CHECK_MARK_X = 600
CHECK_DESCRIPTION_Y = 488
CHECK_VOLUME_Y = 516
CHECK_REPORT_Y = 542
CHECK_HINT_YS = (578, 606)
BUTTON_RADIUS = 14
BUTTON_LIFT = 5
# Dark buttons behind selected items: (width, height) centered on the text.
BUTTON_SIZES: dict[str, tuple[int, int]] = {"item": (300, 46), "setting": (480, 42)}
CHECK_BUTTON_PAD = (16, 3)  # around a selected sound check row, left and top
CHECK_BUTTON_W = CHECK_MARK_X - 8 - (CHECK_ROWS_X - CHECK_BUTTON_PAD[0])

# --- Texts ------------------------------------------------------------------------

# The key list (Controls in the menu and F1 help): hotkeys as (keys, action). Keys are
# drawn as keyboard keys and the arrows as icons, so no arrow characters are needed.
HOTKEYS: tuple[tuple[str, str], ...] = (
    ("Left / Right", "Move"),
    ("Down", "Soft drop"),
    ("Space", "Hard drop"),
    ("Up / X", "Rotate right"),
    ("Z / Ctrl", "Rotate left"),
    ("C / Shift", "Hold"),
    ("P / Esc", "Pause"),
    ("F1", "Help"),
    ("F2", "Guide"),
    ("M", "Music on/off"),
    ("- / +", "Music volume"),
    ("N", "Sound on/off"),
    ("9 / 0", "Sound volume"),
    ("Enter", "Select / new game"),
)
# The controls card next to the well: the seven keys of a game, in the mockup's order.
CONTROL_CARD_ROWS: tuple[tuple[str, str], ...] = tuple(
    HOTKEYS[i] for i in (0, 1, 3, 4, 2, 5, 6)
)
KEY_SEPARATOR = " / "
# Arrow keys by name, in both languages: drawn as arrows pointing that way.
ARROWS: dict[str, str] = {
    "Left": "left", "Right": "right", "Up": "up", "Down": "down",
    "Влево": "left", "Вправо": "right", "Вверх": "up", "Вниз": "down",
}
MENU_HINT = "Up / Down - choose, Enter - select"
RETURN_HINT = "Press Enter or Esc to return"  # high scores and Controls from the menu
HELP_HINT = "Press F1 or Enter to return"
SETTINGS_TITLE = "Settings"
SETTINGS_HINT = "Left / Right - change, Esc - back"
SCORES_TITLE = "HIGH SCORES"
NO_RECORDS = "No records yet"
TABLE_HINTS = ("Enter - new game", "Esc - main menu")
PAUSE_TITLE = "PAUSE"
GUIDE_HINT = "Left / Right - page, Esc - close"
VERSION_TEXT = f"v{__version__}"  # the same in both languages
CHECK_TITLE = "Sound check"
CHECK_MARK = "unpleasant"
NO_SOUND_DEVICE = "No sound device"
CHECK_REPORT_NOTE = "Marks are saved to sound-check.json"
CHECK_HINTS = ("Up / Down - choose, Space - play again", "X - unpleasant, Esc - exit")

# --- Fonts and roles -------------------------------------------------------------------

UNBOUNDED, ONEST = "Unbounded", "Onest"
REGULAR, SEMIBOLD, EXTRABOLD = "Regular", "SemiBold", "ExtraBold"
FONT_FILES: dict[tuple[str, str], str] = {
    (UNBOUNDED, SEMIBOLD): "Unbounded-SemiBold.ttf",
    (UNBOUNDED, EXTRABOLD): "Unbounded-ExtraBold.ttf",
    (ONEST, REGULAR): "Onest-Regular.ttf",
    (ONEST, SEMIBOLD): "Onest-SemiBold.ttf",
}
MIN_FONT_SIZE = 14  # a text that does not fit is drawn smaller, but not below this


class FontSpec(NamedTuple):
    """A font file (family and weight) at a size in pixels."""

    family: str
    weight: str
    size: int


# Every text on screen has a role; the role gives its font, the width it must fit in and
# the point of the text its position stands for.
ROLE_FONTS: dict[str, FontSpec] = {
    # the game screen
    "brand": FontSpec(UNBOUNDED, EXTRABOLD, 22),
    "label": FontSpec(ONEST, SEMIBOLD, 13),
    "label-half": FontSpec(ONEST, SEMIBOLD, 13),
    "value-big": FontSpec(UNBOUNDED, EXTRABOLD, 34),
    "value": FontSpec(UNBOUNDED, EXTRABOLD, 22),
    "value-half": FontSpec(UNBOUNDED, EXTRABOLD, 22),
    "sound": FontSpec(ONEST, SEMIBOLD, 15),
    "card-key": FontSpec(ONEST, SEMIBOLD, 12),
    "card-action": FontSpec(ONEST, REGULAR, 14),
    # over the well
    "overlay-title": FontSpec(UNBOUNDED, EXTRABOLD, 26),
    "pause-item": FontSpec(UNBOUNDED, SEMIBOLD, 16),
    "badge": FontSpec(ONEST, SEMIBOLD, 14),
    "name": FontSpec(ONEST, SEMIBOLD, 18),
    "table-label": FontSpec(ONEST, SEMIBOLD, 13),
    "table-row": FontSpec(ONEST, SEMIBOLD, 16),
    "table-hint": FontSpec(ONEST, REGULAR, 14),
    # full-window screens
    "game-title": FontSpec(UNBOUNDED, EXTRABOLD, 40),
    "title": FontSpec(UNBOUNDED, EXTRABOLD, 34),
    "item": FontSpec(UNBOUNDED, SEMIBOLD, 18),
    "setting": FontSpec(ONEST, SEMIBOLD, 20),
    "entry": FontSpec(ONEST, SEMIBOLD, 20),
    "key": FontSpec(ONEST, SEMIBOLD, 16),
    "action": FontSpec(ONEST, REGULAR, 20),
    "paragraph": FontSpec(ONEST, REGULAR, 17),
    "page": FontSpec(ONEST, SEMIBOLD, 16),
    "hint": FontSpec(ONEST, REGULAR, 16),
    "version": FontSpec(ONEST, SEMIBOLD, 15),
    # the sound check
    "row": FontSpec(ONEST, REGULAR, 17),
    "mark": FontSpec(ONEST, SEMIBOLD, 17),
    "note": FontSpec(ONEST, REGULAR, 16),
}
TOP_LEFT_ROLES = ("label", "label-half", "value-big", "value", "value-half", "sound",
                  "card-key", "card-action", "overlay-title", "badge", "name", "table-label",
                  "table-row", "table-hint", "key", "action", "paragraph", "row", "mark")
MID_LEFT_ROLES = ("brand", "pause-item")
KEY_ROLES = ("card-key", "key")  # drawn as keyboard keys
_ROLE_WIDTHS: dict[str, int] = {
    "brand": BRAND_W,
    "label": card_inner_width(SCORE_CARD),
    "label-half": card_inner_width(LEVEL_CARD),
    "value-big": card_inner_width(SCORE_CARD),
    "value": card_inner_width(BEST_CARD),
    "value-half": card_inner_width(LEVEL_CARD),
    "sound": card_inner_width(SOUND_CARD),
    "card-key": CONTROL_ACTION_X - 8 - CONTROL_KEYS_X,
    "card-action": CONTROLS_CARD[0] + CONTROLS_CARD[2] - CARD_PAD_X - CONTROL_ACTION_X,
    "overlay-title": OVERLAY_INNER_W,
    "pause-item": OVERLAY_INNER_W - 2 * BUTTON_PAD_X,
    "badge": OVERLAY_INNER_W - 2 * PLAQUE_PAD_X,
    "name": OVERLAY_INNER_W,
    "table-label": OVERLAY_INNER_W,
    "table-row": OVERLAY_INNER_W - 2 * PLAQUE_PAD_X,
    "table-hint": OVERLAY_INNER_W,
    "item": BUTTON_SIZES["item"][0] - 32,
    "setting": BUTTON_SIZES["setting"][0] - 32,
    "key": ACTION_COLUMN_X - 20 - KEY_COLUMN_X,
    "action": SCREEN_PANEL[0] + SCREEN_PANEL[2] - 40 - ACTION_COLUMN_X,
    "version": 120,
    "row": CHECK_MARK_X - 8 - CHECK_BUTTON_PAD[0] - CHECK_ROWS_X,
    "mark": SCREEN_PANEL[0] + SCREEN_PANEL[2] - 40 - CHECK_MARK_X,
}

ScreenText = tuple[str, Point, str, Color]


def screen_text_width(role: str) -> int:
    """The width a text of this role must fit in."""
    return _ROLE_WIDTHS.get(role, SCREEN_TEXT_W)


def text_anchor(role: str) -> str:
    """Which point of a text of this role its position stands for: "topleft",
    "midleft", "bottomright" (the version) or "center"."""
    if role in TOP_LEFT_ROLES:
        return "topleft"
    if role in MID_LEFT_ROLES:
        return "midleft"
    if role == "version":
        return "bottomright"
    return "center"


def key_labels(keys: str) -> list[str]:
    """The keys of a key list entry, one per keyboard key: "C / Shift" -> ["C", "Shift"]."""
    return keys.split(KEY_SEPARATOR)


def arrow(label: str) -> str | None:
    """The direction of an arrow key ("left", "right", "up", "down"), or None."""
    return ARROWS.get(label)


def selection_rect(role: str, pos: Point) -> Rect:
    """The dark button behind a selected item of this role at this position."""
    x, y = pos
    if role == "row":
        pad_x, pad_y = CHECK_BUTTON_PAD
        return x - pad_x, y - pad_y, CHECK_BUTTON_W, CHECK_ROWS_STEP
    if role == "pause-item":
        height = OVERLAY_LINES["pause-item"][0]
        return OVERLAY_INNER_X, y - height // 2, OVERLAY_INNER_W, height
    w, h = BUTTON_SIZES[role]
    return x - w // 2, y - h // 2, w, h


# --- The game screen -------------------------------------------------------------------


def _language(controller: Controller) -> str:
    """The interface language chosen in the settings."""
    return controller.settings.language


def best_score(controller: Controller) -> int:
    """The BEST card: the best score in the table (0 when it is empty) or this game's
    score, whichever is higher."""
    entries = controller.scores.entries
    return max(entries[0].score if entries else 0, controller.game.score)


def _label_pos(card: Rect) -> Point:
    """Top-left corner of a card's label."""
    return card[0] + CARD_PAD_X, card[1] + LABEL_DY


def _value_pos(card: Rect) -> Point:
    """Top-left corner of a card's value, under its label."""
    return card[0] + CARD_PAD_X, card[1] + VALUE_DY


def panel_texts(controller: Controller) -> list[ScreenText]:
    """The texts of the game screen around the well: the game's name, the cards' labels
    and values, the sound lines and the controls card, as (text, position, role, color)."""
    language = _language(controller)
    game = controller.game
    texts: list[ScreenText] = [(TITLE, BRAND_POS, "brand", CREAM)]
    counters = (("SCORE", SCORE_CARD, str(game.score), "label", "value-big"),
                ("LEVEL", LEVEL_CARD, str(game.level), "label-half", "value-half"),
                ("LINES", LINES_CARD, str(game.lines), "label-half", "value-half"),
                ("BEST", BEST_CARD, str(best_score(controller)), "label", "value"))
    for label, card, value, label_role, value_role in counters:
        texts.append((tr(label, language), _label_pos(card), label_role, MUTED))
        texts.append((value, _value_pos(card), value_role, TEXT))
    sound_lines = (
        tr(f"MUSIC {_on_off(controller.music_on)}", language),
        music_volume_text(controller.music_volume, language),
        tr(f"SOUND {_on_off(controller.sound_on)}", language),
        sound_volume_text(controller.settings.sfx_volume, language),
    )
    for text, y in zip(sound_lines, SOUND_LINE_YS):
        texts.append((text, (SOUND_CARD[0] + CARD_PAD_X, y), "sound", TEXT))
    for label, card in (("NEXT", NEXT_CARD), ("HOLD", HOLD_CARD), ("CONTROLS", CONTROLS_CARD)):
        texts.append((tr(label, language), _label_pos(card), "label", MUTED))
    for row, (keys, action) in enumerate(CONTROL_CARD_ROWS):
        y = CONTROL_ROWS_Y + row * CONTROL_ROW_STEP
        texts.append((tr(keys, language), (CONTROL_KEYS_X, y), "card-key", TEXT))
        texts.append((tr(action, language), (CONTROL_ACTION_X, y + 2), "card-action", TEXT))
    return texts


def _on_off(flag: bool) -> str:
    """Show a switch as "ON" or "OFF"."""
    return "ON" if flag else "OFF"


# --- Over the well -----------------------------------------------------------------------


def overlay_items(controller: Controller) -> list[tuple[str, str, Color]]:
    """Lines shown on the panel over the well as (text, role, color), or none during
    normal play. HIGHLIGHT marks the selected pause item and this game's record."""
    phase = controller.phase
    if phase is Phase.NAME_ENTRY:
        return _name_entry_lines(controller)
    if phase is Phase.TABLE:
        return _table_lines(controller)
    if controller.paused:
        return _pause_lines(controller)
    return []


def overlay_lines(controller: Controller) -> list[tuple[str, Color]]:
    """overlay_items() without the roles: (text, color)."""
    return [(text, color) for text, _, color in overlay_items(controller)]


def overlay_texts(controller: Controller) -> list[str]:
    """Just the texts of overlay_items()."""
    return [text for text, _, _ in overlay_items(controller)]


def overlay_layout(controller: Controller) -> tuple[Rect, list[ScreenText]] | None:
    """The panel over the well and its lines placed on it, or None during normal play.

    Lines go one under another from the panel's top-left padding; the panel is as high as
    its lines and centered on the well.
    """
    items = overlay_items(controller)
    if not items:
        return None
    height = 2 * OVERLAY_PAD_Y + sum(sum(OVERLAY_LINES[role]) for _, role, _ in items)
    height -= OVERLAY_LINES[items[-1][1]][1]  # no space after the last line
    top = OVERLAY_CENTER_Y - height // 2
    panel = (OVERLAY_PANEL_X, top, OVERLAY_PANEL_W, height)
    y = top + OVERLAY_PAD_Y
    placed: list[ScreenText] = []
    for text, role, color in items:
        line_h, gap = OVERLAY_LINES[role]
        if role == "pause-item":
            pos = (OVERLAY_INNER_X + BUTTON_PAD_X, y + line_h // 2)
        elif role in ("badge", "table-row"):
            pos = (OVERLAY_INNER_X + PLAQUE_PAD_X, y + PLAQUE_PAD_Y)
        else:
            pos = (OVERLAY_INNER_X, y)
        placed.append((text, pos, role, color))
        y += line_h + gap
    return panel, placed


def _name_entry_lines(controller: Controller) -> list[tuple[str, str, Color]]:
    """Game over with a record: the title, the NEW RECORD badge and the name being typed."""
    language = _language(controller)
    return [(tr("GAME OVER", language), "overlay-title", TEXT),
            (tr("NEW RECORD", language), "badge", TEXT),
            (name_line(controller.name, language), "name", TEXT)]


def _table_lines(controller: Controller) -> list[tuple[str, str, Color]]:
    """Game over without name entry: the title, the high score table and the hints."""
    language = _language(controller)
    lines = [(tr("GAME OVER", language), "overlay-title", TEXT),
             (tr(SCORES_TITLE, language), "table-label", MUTED)]
    lines += [(text, "table-row", color) for text, color in score_rows(controller)]
    lines += [(tr(hint, language), "table-hint", MUTED) for hint in TABLE_HINTS]
    return lines


def _pause_lines(controller: Controller) -> list[tuple[str, str, Color]]:
    """The pause title and the pause menu items."""
    language = _language(controller)
    items = _items(menus.PAUSE_ITEMS, controller.pause_index, language)
    return ([(tr(PAUSE_TITLE, language), "overlay-title", TEXT)]
            + [(text, "pause-item", color) for text, color in items])


def score_rows(controller: Controller) -> list[tuple[str, Color]]:
    """High score rows "<place>. <name> <score>", this game's record highlighted, or the
    no-records line for an empty table."""
    entries = controller.scores.entries
    if not entries:
        return [(tr(NO_RECORDS, _language(controller)), TEXT)]
    return [
        (f"{place}. {entry.name} {entry.score}",
         HIGHLIGHT if place == controller.highlight else TEXT)
        for place, entry in enumerate(entries, start=1)
    ]


def _items(items: tuple[str, ...], selected: int, language: str) -> list[tuple[str, Color]]:
    """Menu items in the language, with the selected one highlighted."""
    return [(tr(item, language), HIGHLIGHT if i == selected else TEXT)
            for i, item in enumerate(items)]


# --- Full-window screens -------------------------------------------------------------------


def full_screen(controller: Controller) -> str | None:
    """Which screen covers the whole window: "guide" (F2, over any other screen),
    "menu", "scores", "settings", "controls", "help" (the key list opened with F1) or
    None when the field is shown."""
    if controller.guide_open:
        return "guide"
    screen = {
        Phase.MENU: "menu",
        Phase.SCORES: "scores",
        Phase.SETTINGS: "settings",
        Phase.CONTROLS: "controls",
    }.get(controller.phase)
    if screen is None and controller.help_open:
        return "help"
    return screen


FULL_SCREENS = ("menu", "scores", "settings", "controls", "help")


def full_screen_texts(controller: Controller) -> list[ScreenText]:
    """Texts of the full-window screen as (text, position, role, color), or [] when none
    is shown.

    The position stands for the point of the text given by text_anchor(role). The
    guide's "paragraph" texts all carry the top-left corner of its text area: render
    wraps them and puts them one under another from there.
    """
    screen = full_screen(controller)
    if screen is None:
        return []
    return _screen_texts(controller, screen)


def _screen_texts(controller: Controller, screen: str) -> list[ScreenText]:
    """Texts of one of FULL_SCREENS or "guide" for the controller's state and language."""
    if screen == "guide":
        return _guide_texts(controller, controller.guide_page)
    language = _language(controller)
    if screen == "menu":
        texts = [(TITLE, (CENTER_X, MENU_TITLE_Y), "game-title", TEXT)]
        items = _items(menus.MAIN_ITEMS, controller.menu_index, language)
        texts += _column(items, "item", MENU_ITEMS_Y, MENU_ITEMS_STEP)
        texts.append((tr(MENU_HINT, language), (CENTER_X, SCREEN_HINT_Y), "hint", HINT_COLOR))
        return texts + [(VERSION_TEXT, VERSION_POS, "version", VERSION_COLOR)]
    if screen == "scores":
        texts = [(tr(SCORES_TITLE, language), (CENTER_X, SCREEN_TITLE_Y), "title", TEXT)]
        rows = [(text, TEXT) for text, _ in score_rows(controller)]
        texts += _column(rows, "entry", SCORES_ROWS_Y, SCORES_ROWS_STEP)
        return texts + [(tr(RETURN_HINT, language), (CENTER_X, SCREEN_HINT_Y), "hint",
                         HINT_COLOR)]
    if screen == "settings":
        texts = [(tr(SETTINGS_TITLE, language), (CENTER_X, SCREEN_TITLE_Y), "title", TEXT)]
        rows = [_setting_line(controller, row) for row in menus.SETTING_ROWS]
        items = _items((*rows, menus.BACK), controller.settings_index, language)
        texts += _column(items, "setting", SETTINGS_ROWS_Y, SETTINGS_ROWS_STEP)
        return texts + [(tr(SETTINGS_HINT, language), (CENTER_X, SCREEN_HINT_Y), "hint",
                         HINT_COLOR)]
    texts = [(TITLE, (CENTER_X, SCREEN_TITLE_Y), "title", TEXT)]
    for row, (keys, action) in enumerate(HOTKEYS):
        y = KEY_TABLE_Y + row * KEY_TABLE_STEP
        texts.append((tr(keys, language), (KEY_COLUMN_X, y), "key", TEXT))
        texts.append((tr(action, language), (ACTION_COLUMN_X, y), "action", TEXT))
    hint = RETURN_HINT if screen == "controls" else HELP_HINT
    return texts + [(tr(hint, language), (CENTER_X, SCREEN_HINT_Y), "hint", HINT_COLOR)]


def _setting_line(controller: Controller, row: str) -> str:
    """A settings row "<label>: <value>" with the label and value in the language."""
    language = _language(controller)
    label = menus.setting_label(row)
    value = menus.setting_value(controller.settings, row)
    return f"{tr(label, language)}: {tr(value, language)}"


def _guide_texts(controller: Controller, page: int) -> list[ScreenText]:
    """Texts of one guide page (0-based): the title, the paragraphs, the page number and
    the hint. The Controls page lists the key list as "<keys>: <action>" lines."""
    language = _language(controller)
    if page == guide.CONTROLS_PAGE:
        paragraphs = [f"{tr(keys, language)}: {tr(action, language)}" for keys, action in HOTKEYS]
    else:
        paragraphs = list(guide.paragraphs(page, language))
    title = tr(guide.PAGE_TITLES[page], language)
    texts = [(title, (CENTER_X, SCREEN_TITLE_Y), "title", TEXT)]
    texts += [(text, (GUIDE_TEXT_X, GUIDE_TEXT_Y), "paragraph", TEXT) for text in paragraphs]
    number = page_line(page + 1, guide.PAGE_COUNT, language)
    texts.append((number, (CENTER_X, GUIDE_PAGE_Y), "page", MUTED))
    texts.append((tr(GUIDE_HINT, language), (CENTER_X, SCREEN_HINT_Y), "hint", HINT_COLOR))
    return texts


def sound_check_texts(
    check: soundcheck.SoundCheck, language: str, has_audio: bool
) -> list[ScreenText]:
    """Texts of the sound check screen as (text, position, role, color).

    Roles: "title", "note" and "hint" are centered on their position; "row" (an item of
    the list, "<number>. <title>") and "mark" (to the right of a marked row) start at it
    (left edge, top). Without a sound device the volume line gives way to a notice.
    """
    texts = [(tr(CHECK_TITLE, language), (CENTER_X, CHECK_TITLE_Y), "title", TEXT)]
    for i, item in enumerate(soundcheck.ITEMS):
        y = CHECK_ROWS_Y + i * CHECK_ROWS_STEP
        color = HIGHLIGHT if i == check.index else TEXT
        texts.append((f"{i + 1}. {tr(item.title, language)}", (CHECK_ROWS_X, y), "row", color))
        if check.marked[i]:
            texts.append((tr(CHECK_MARK, language), (CHECK_MARK_X, y), "mark", MARK_COLOR))
    if has_audio:
        volume = check_volume_text(DEFAULT_SFX_VOLUME, DEFAULT_VOLUME, language)
    else:
        volume = tr(NO_SOUND_DEVICE, language)
    texts += [
        (tr(check.item.description, language), (CENTER_X, CHECK_DESCRIPTION_Y), "note", TEXT),
        (volume, (CENTER_X, CHECK_VOLUME_Y), "note", NOTE_COLOR),
        (tr(CHECK_REPORT_NOTE, language), (CENTER_X, CHECK_REPORT_Y), "note", NOTE_COLOR),
    ]
    texts += [(tr(hint, language), (CENTER_X, y), "hint", MUTED)
              for hint, y in zip(CHECK_HINTS, CHECK_HINT_YS)]
    return texts


def _column(
    lines: list[tuple[str, Color]], role: str, first_y: int, step: int
) -> list[ScreenText]:
    """Lines centered on the window one under another, starting at first_y, `step` apart."""
    return [
        (text, (CENTER_X, first_y + i * step), role, color)
        for i, (text, color) in enumerate(lines)
    ]


# --- All texts ----------------------------------------------------------------------------


def screen_texts(controller: Controller) -> list[str]:
    """Every text drawn on screen, in drawing order."""
    full = full_screen_texts(controller)
    if full:
        return [text for text, _, _, _ in full]
    return [text for text, _, _, _ in panel_texts(controller)] + overlay_texts(controller)


def all_screen_texts(controller: Controller) -> list[str]:
    """The texts of every screen for the controller's settings, whatever is shown now:
    the cards, the pause, name entry and table overlays, all full-window screens and
    every page of the guide."""
    texts = [text for text, _, _, _ in panel_texts(controller)]
    for lines in (_pause_lines(controller), _name_entry_lines(controller),
                  _table_lines(controller)):
        texts += [text for text, _, _ in lines]
    for screen in FULL_SCREENS:
        texts += [text for text, _, _, _ in _screen_texts(controller, screen)]
    for page in range(guide.PAGE_COUNT):
        texts += [text for text, _, _, _ in _guide_texts(controller, page)]
    return texts


def all_screen_entries(controller: Controller) -> list[tuple[str, str]]:
    """(text, role) of every text of every screen, as all_screen_texts() gathers them, so
    each text can be checked in the font of its role."""
    entries = [(text, role) for text, _, role, _ in panel_texts(controller)]
    for lines in (_pause_lines(controller), _name_entry_lines(controller),
                  _table_lines(controller)):
        entries += [(text, role) for text, role, _ in lines]
    for screen in FULL_SCREENS:
        entries += [(text, role) for text, _, role, _ in _screen_texts(controller, screen)]
    for page in range(guide.PAGE_COUNT):
        entries += [(text, role) for text, _, role, _ in _guide_texts(controller, page)]
    return entries
