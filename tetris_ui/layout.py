"""Screen layout, colors and on-screen texts, without pygame."""

from __future__ import annotations

from tetris.board import HIDDEN_ROWS, HEIGHT, VISIBLE_HEIGHT, WIDTH
from tetris.pieces import PieceType
from tetris_ui import guide, menus
from tetris_ui.input import Controller, Phase
from tetris_ui.texts import music_volume_text, name_line, page_line, sound_volume_text, tr

WINDOW_SIZE = (520, 640)
TITLE = "SEVA Tetris"
FPS = 60

CELL = 30
FIELD_X, FIELD_Y = 20, 20
FIELD_W, FIELD_H = WIDTH * CELL, VISIBLE_HEIGHT * CELL

PANEL_X = 340
NEXT_LABEL_Y = 20
PREVIEW_X, PREVIEW_Y = PANEL_X, 50
PREVIEW_CELLS = 4  # preview width in cells
PREVIEW_ROWS = 2  # every piece fits two rows in orientation 0
HOLD_LABEL_Y = 125
HOLD_X, HOLD_Y = PANEL_X, 155
# (label, y of the label); each value is drawn 30 px below its label.
COUNTER_LABELS = (("SCORE", 235), ("LINES", 300), ("LEVEL", 365))
VALUE_OFFSET_Y = 30
MUSIC_Y, VOLUME_Y, SOUND_Y, SFX_VOLUME_Y = 470, 500, 530, 560

# The key list (Controls in the menu and F1 help): hotkeys as (keys, action), all ASCII
# because the built-in font has no arrow glyphs.
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

# Full-window screens; every y is a center, except rows of the key list (top edge).
MENU_TITLE_Y = 120
MENU_ITEMS_Y, MENU_ITEMS_STEP = 240, 50
SCREEN_TITLE_Y = 60  # high scores and settings
SCORES_ROWS_Y, SCORES_ROWS_STEP = 130, 34
SETTINGS_ROWS_Y, SETTINGS_ROWS_STEP = 130, 45
KEY_SCREEN_TITLE_Y = 60
KEY_TABLE_Y, KEY_TABLE_STEP = 120, 32  # top of the first row, row pitch
KEY_COLUMN_X, ACTION_COLUMN_X = 70, 270  # left edges of the two columns
SCREEN_HINT_Y = 590
KEY_SCREEN_HINT_Y = 600
# The guide: the title, then paragraphs from the top-left corner of the text area (render
# wraps them at spaces into lines GUIDE_LINE_STEP apart, with an extra gap between
# paragraphs), then the page number and the hint.
GUIDE_TITLE_Y = 50
GUIDE_TEXT_X, GUIDE_TEXT_Y = 20, 95
GUIDE_LINE_STEP = 24
GUIDE_PARAGRAPH_GAP = 8
GUIDE_PAGE_Y = 575
GUIDE_HINT_Y = 610

# Widths the texts must fit in; a text too wide for its font is drawn smaller.
PANEL_W = WINDOW_SIZE[0] - PANEL_X  # side panel
SCREEN_TEXT_W = WINDOW_SIZE[0] - 2 * 20  # full-window screens, 20 px margins
KEY_COLUMN_W = 190  # from KEY_COLUMN_X to 10 px before ACTION_COLUMN_X
ACTION_COLUMN_W = 240  # from ACTION_COLUMN_X to 10 px before the right edge
MIN_FONT_SIZE = 14

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


def dimmed_color(piece_type: PieceType) -> Color:
    """The piece color at half brightness, for a held piece that cannot be swapped now."""
    r, g, b = PIECE_COLORS[piece_type]
    return r // 2, g // 2, b // 2


def cell_rect(col: int, row: int) -> Rect:
    """Pixel rect (x, y, w, h) of a visible board cell (rows 2-21)."""
    if not (0 <= col < WIDTH and HIDDEN_ROWS <= row < HEIGHT):
        raise ValueError(f"cell ({col}, {row}) is not visible")
    return FIELD_X + CELL * col, FIELD_Y + CELL * (row - HIDDEN_ROWS), CELL, CELL


def _language(controller: Controller) -> str:
    """The interface language chosen in the settings."""
    return controller.settings.language


def panel_texts(controller: Controller) -> list[tuple[str, tuple[int, int]]]:
    """Side panel texts with their top-left positions."""
    language = _language(controller)
    game = controller.game
    values = (game.score, game.lines, game.level)
    texts = [(tr("NEXT", language), (PANEL_X, NEXT_LABEL_Y)),
             (tr("HOLD", language), (PANEL_X, HOLD_LABEL_Y))]
    for (label, y), value in zip(COUNTER_LABELS, values):
        texts.append((tr(label, language), (PANEL_X, y)))
        texts.append((str(value), (PANEL_X, y + VALUE_OFFSET_Y)))
    music = f"MUSIC {_on_off(controller.music_on)}"
    sound = f"SOUND {_on_off(controller.sound_on)}"
    texts.append((tr(music, language), (PANEL_X, MUSIC_Y)))
    texts.append((music_volume_text(controller.music_volume, language), (PANEL_X, VOLUME_Y)))
    texts.append((tr(sound, language), (PANEL_X, SOUND_Y)))
    texts.append((sound_volume_text(controller.settings.sfx_volume, language),
                  (PANEL_X, SFX_VOLUME_Y)))
    return texts


def _on_off(flag: bool) -> str:
    """Show a switch as "ON" or "OFF"."""
    return "ON" if flag else "OFF"


def overlay_lines(controller: Controller) -> list[tuple[str, Color]]:
    """Lines shown over the field with their colors, or none during normal play."""
    phase = controller.phase
    if phase is Phase.NAME_ENTRY:
        return _name_entry_lines(controller)
    if phase is Phase.TABLE:
        return _table_lines(controller)
    if controller.paused:
        return _pause_lines(controller)
    return []


def _name_entry_lines(controller: Controller) -> list[tuple[str, Color]]:
    """Game over with a record: the title, NEW RECORD and the name being typed."""
    language = _language(controller)
    return [(tr("GAME OVER", language), TEXT), (tr("NEW RECORD", language), TEXT),
            (name_line(controller.name, language), TEXT)]


def _table_lines(controller: Controller) -> list[tuple[str, Color]]:
    """Game over without name entry: the title, the high score table and the hints."""
    language = _language(controller)
    lines = [(tr("GAME OVER", language), TEXT), (tr(SCORES_TITLE, language), TEXT)]
    lines += score_rows(controller)
    lines += [(tr(hint, language), TEXT) for hint in TABLE_HINTS]
    return lines


def _pause_lines(controller: Controller) -> list[tuple[str, Color]]:
    """The pause title and the pause menu items."""
    language = _language(controller)
    return ([(tr(PAUSE_TITLE, language), TEXT)]
            + _items(menus.PAUSE_ITEMS, controller.pause_index, language))


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


def overlay_texts(controller: Controller) -> list[str]:
    """Just the texts of overlay_lines()."""
    return [text for text, _ in overlay_lines(controller)]


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


ScreenText = tuple[str, tuple[int, int], str, Color]
FULL_SCREENS = ("menu", "scores", "settings", "controls", "help")


def full_screen_texts(controller: Controller) -> list[ScreenText]:
    """Texts of the full-window screen as (text, position, role, color), or [] when none
    is shown.

    Roles: "title" (big font), "item" and "hint" are centered on their position; "key"
    and "action" (the two columns of the key list) start at it (left edge, top). The
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
    center_x = WINDOW_SIZE[0] // 2
    if screen == "menu":
        texts = [(TITLE, (center_x, MENU_TITLE_Y), "title", TEXT)]
        items = _items(menus.MAIN_ITEMS, controller.menu_index, language)
        texts += _column(items, center_x, MENU_ITEMS_Y, MENU_ITEMS_STEP)
        return texts + [(tr(MENU_HINT, language), (center_x, SCREEN_HINT_Y), "hint", TEXT)]
    if screen == "scores":
        texts = [(tr(SCORES_TITLE, language), (center_x, SCREEN_TITLE_Y), "title", TEXT)]
        texts += _column(score_rows(controller), center_x, SCORES_ROWS_Y, SCORES_ROWS_STEP)
        return texts + [(tr(RETURN_HINT, language), (center_x, SCREEN_HINT_Y), "hint", TEXT)]
    if screen == "settings":
        texts = [(tr(SETTINGS_TITLE, language), (center_x, SCREEN_TITLE_Y), "title", TEXT)]
        rows = [_setting_line(controller, row) for row in menus.SETTING_ROWS]
        items = _items((*rows, menus.BACK), controller.settings_index, language)
        texts += _column(items, center_x, SETTINGS_ROWS_Y, SETTINGS_ROWS_STEP)
        return texts + [(tr(SETTINGS_HINT, language), (center_x, SCREEN_HINT_Y), "hint", TEXT)]
    texts = [(TITLE, (center_x, KEY_SCREEN_TITLE_Y), "title", TEXT)]
    for row, (keys, action) in enumerate(HOTKEYS):
        y = KEY_TABLE_Y + row * KEY_TABLE_STEP
        texts.append((tr(keys, language), (KEY_COLUMN_X, y), "key", HIGHLIGHT))
        texts.append((tr(action, language), (ACTION_COLUMN_X, y), "action", TEXT))
    hint = RETURN_HINT if screen == "controls" else HELP_HINT
    return texts + [(tr(hint, language), (center_x, KEY_SCREEN_HINT_Y), "hint", TEXT)]


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
    center_x = WINDOW_SIZE[0] // 2
    if page == guide.CONTROLS_PAGE:
        paragraphs = [f"{tr(keys, language)}: {tr(action, language)}" for keys, action in HOTKEYS]
    else:
        paragraphs = list(guide.paragraphs(page, language))
    title = tr(guide.PAGE_TITLES[page], language)
    texts = [(title, (center_x, GUIDE_TITLE_Y), "title", TEXT)]
    texts += [(text, (GUIDE_TEXT_X, GUIDE_TEXT_Y), "paragraph", TEXT) for text in paragraphs]
    number = page_line(page + 1, guide.PAGE_COUNT, language)
    texts.append((number, (center_x, GUIDE_PAGE_Y), "item", TEXT))
    texts.append((tr(GUIDE_HINT, language), (center_x, GUIDE_HINT_Y), "hint", TEXT))
    return texts


def screen_text_width(role: str) -> int:
    """The width a full-window screen text of this role must fit in."""
    return {"key": KEY_COLUMN_W, "action": ACTION_COLUMN_W}.get(role, SCREEN_TEXT_W)


def _column(
    lines: list[tuple[str, Color]], center_x: int, first_y: int, step: int
) -> list[ScreenText]:
    """Lines centered one under another, starting at first_y, `step` apart."""
    return [
        (text, (center_x, first_y + i * step), "item", color)
        for i, (text, color) in enumerate(lines)
    ]


def screen_texts(controller: Controller) -> list[str]:
    """Every text drawn on screen, in drawing order."""
    full = full_screen_texts(controller)
    if full:
        return [text for text, _, _, _ in full]
    return [text for text, _ in panel_texts(controller)] + overlay_texts(controller)


def all_screen_texts(controller: Controller) -> list[str]:
    """The texts of every screen for the controller's settings, whatever is shown now:
    the panel, the pause, name entry and table overlays, all full-window screens and
    every page of the guide."""
    texts = [text for text, _ in panel_texts(controller)]
    for lines in (_pause_lines(controller), _name_entry_lines(controller),
                  _table_lines(controller)):
        texts += [text for text, _ in lines]
    for screen in FULL_SCREENS:
        texts += [text for text, _, _, _ in _screen_texts(controller, screen)]
    for page in range(guide.PAGE_COUNT):
        texts += [text for text, _, _, _ in _guide_texts(controller, page)]
    return texts
