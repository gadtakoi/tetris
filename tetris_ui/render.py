"""Draws the game state onto a pygame surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pygame

from tetris.board import HIDDEN_ROWS, HEIGHT, WIDTH
from tetris.pieces import PieceType
from tetris_ui import layout
from tetris_ui.input import Controller
from tetris_ui.layout import FontSpec
from tetris_ui.soundcheck import SoundCheck

FONT_DIR = Path(__file__).parent / "fonts"  # inside the exe too: build_exe.py adds it
FONT_SIZE_STEP = 2  # how much smaller each try is when a text does not fit
KEY_GAP = 6  # between two keys of one key list entry
KEY_PAD_X = {"card-key": 6, "key": 9}  # text inside a key
KEY_HEIGHTS = {"card-key": layout.CONTROL_KEY_H, "key": layout.KEY_H}
KEY_RADIUS = 6
KEY_LIFT = 2
PLAQUE_RADIUS = 8

# The logo, as the game's icon: a 512 x 512 tile with three cream blocks in a column and
# a peach "heel" to the right of the bottom one, each over its hard shadow.
_LOGO_BLOCKS = ((124, 64), (124, 184), (124, 304), (244, 304))
_LOGO_BLOCK, _LOGO_BLOCK_RADIUS, _LOGO_SHIFT, _LOGO_RADIUS = 112, 22, 22, 112


@dataclass
class Fonts:
    """The game's fonts, loaded from FONT_DIR on demand and kept by file and size."""

    _by_spec: dict[FontSpec, pygame.font.Font] = field(default_factory=dict, repr=False)

    def get(self, spec: FontSpec) -> pygame.font.Font:
        """The font of a family and weight at a size in pixels."""
        if spec not in self._by_spec:
            path = FONT_DIR / layout.FONT_FILES[spec.family, spec.weight]
            self._by_spec[spec] = pygame.font.Font(path, spec.size)
        return self._by_spec[spec]

    def for_role(self, role: str) -> pygame.font.Font:
        """The font of a role at its base size."""
        return self.get(layout.ROLE_FONTS[role])


def make_fonts() -> Fonts:
    """The fonts, with every role's font loaded at once, so a missing font file fails at
    start. Requires pygame.font.init()."""
    fonts = Fonts()
    for spec in layout.ROLE_FONTS.values():
        fonts.get(spec)
    return fonts


def fitted_size(fonts: Fonts, spec: FontSpec, text: str, max_width: int) -> int:
    """The largest size from spec.size down, in FONT_SIZE_STEP steps, at which the text
    fits max_width; layout.MIN_FONT_SIZE if even that is too wide. A base size below the
    minimum is kept."""
    size = spec.size
    while (size > layout.MIN_FONT_SIZE
           and fonts.get(spec._replace(size=size)).size(text)[0] > max_width):
        size = max(layout.MIN_FONT_SIZE, size - FONT_SIZE_STEP)
    return size


def fitted_font(fonts: Fonts, spec: FontSpec, text: str, max_width: int) -> pygame.font.Font:
    """The font for a text that must fit max_width: spec's size if it fits, else smaller."""
    return fonts.get(spec._replace(size=fitted_size(fonts, spec, text, max_width)))


def role_font(fonts: Fonts, role: str, text: str) -> pygame.font.Font:
    """The font a text of this role is drawn with: its role's font, made smaller if the
    text does not fit the role's width."""
    return fitted_font(fonts, layout.ROLE_FONTS[role], text, layout.screen_text_width(role))


def text_rect(fonts: Fonts, role: str, text: str, pos: layout.Point) -> pygame.Rect:
    """Where a text of this role at this position lands on screen."""
    if role in layout.KEY_ROLES:
        return pygame.Rect(pos, (keys_width(fonts, role, text), KEY_HEIGHTS[role] + KEY_LIFT))
    rect = pygame.Rect((0, 0), role_font(fonts, role, text).size(text))
    setattr(rect, layout.text_anchor(role), pos)
    return rect


def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    """Break text into lines no wider than width at the spaces between words; a single
    word wider than width gets a line of its own."""
    lines: list[str] = []
    line = ""
    for word in text.split(" "):
        candidate = f"{line} {word}" if line else word
        if line and font.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    return lines


def guide_lines(
    fonts: Fonts, paragraphs: list[str], origin: tuple[int, int]
) -> list[tuple[str, tuple[int, int]]]:
    """The guide's paragraphs wrapped to the text width and placed one under another from
    origin (top-left): (line, top-left position) for every line."""
    font = fonts.for_role("paragraph")
    x, y = origin
    lines = []
    for paragraph in paragraphs:
        for line in wrap_text(font, paragraph, layout.screen_text_width("paragraph")):
            lines.append((line, (x, y)))
            y += layout.GUIDE_LINE_STEP
        y += layout.GUIDE_PARAGRAPH_GAP
    return lines


# --- Shapes ------------------------------------------------------------------------------


def _rounded(surface: pygame.Surface, color: layout.Color, rect, radius: int,
             width: int = 0) -> None:
    """A rectangle with rounded corners, filled or (width > 0) outlined, without smoothing."""
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)


def _lifted(surface: pygame.Surface, rect: layout.Rect, color: layout.Color, radius: int,
            lift: int) -> None:
    """A rounded rectangle over its hard shadow, moved `lift` px right and down."""
    x, y, w, h = rect
    _rounded(surface, layout.SHADOW, (x + lift, y + lift, w, h), radius)
    _rounded(surface, color, rect, radius)


def _card(surface: pygame.Surface, rect: layout.Rect, radius: int = layout.CARD_RADIUS,
          lift: int = layout.CARD_LIFT) -> None:
    """A cream card or panel with its hard shadow."""
    _lifted(surface, rect, layout.CREAM, radius, lift)


def _button(surface: pygame.Surface, rect: layout.Rect) -> None:
    """The dark button behind a selected item."""
    _lifted(surface, rect, layout.INK, layout.BUTTON_RADIUS, layout.BUTTON_LIFT)


def _block_square(x: int, y: int, size: int, shadow: bool) -> tuple[pygame.Rect, int]:
    """The square of a cell's block (or of its shadow) and its corner radius."""
    geometry = layout.block(size)
    shift = geometry.shift if shadow else 0
    rect = pygame.Rect(x + geometry.inset + shift, y + geometry.inset + shift,
                       geometry.side, geometry.side)
    return rect, geometry.radius


def _blocks(surface: pygame.Surface, blocks: list[tuple[int, int, layout.PieceColors]],
            size: int) -> None:
    """Blocks of `size` px cells at their top-left corners: every shadow first, then every
    fill, so a neighbor's shadow never covers a block."""
    for x, y, colors in blocks:
        rect, radius = _block_square(x, y, size, shadow=True)
        _rounded(surface, colors.shadow, rect, radius)
    for x, y, colors in blocks:
        rect, radius = _block_square(x, y, size, shadow=False)
        _rounded(surface, colors.fill, rect, radius)


def _logo(surface: pygame.Surface, rect: layout.Rect) -> None:
    """The game's logo scaled into a square rect."""
    x0, y0, size, _ = rect
    scale = size / 512

    def scaled(value: float) -> int:
        """A length of the 512 px icon in this logo's pixels."""
        return round(value * scale)

    _rounded(surface, layout.WINDOW_BG, rect, scaled(_LOGO_RADIUS))
    for i, (bx, by) in enumerate(_LOGO_BLOCKS):
        fill = layout.PEACH if i == len(_LOGO_BLOCKS) - 1 else layout.CREAM
        for dx, color in ((_LOGO_SHIFT, layout.SHADOW), (0, fill)):
            square = (x0 + scaled(bx + dx), y0 + scaled(by + dx), scaled(_LOGO_BLOCK),
                      scaled(_LOGO_BLOCK))
            _rounded(surface, color, square, scaled(_LOGO_BLOCK_RADIUS))


def _arrow(surface: pygame.Surface, center: tuple[float, float], size: float,
           direction: str) -> None:
    """An arrow icon pointing left, right, up or down, `size` px long."""
    half, head, stem = size / 2, size * 0.45, max(1.0, size / 9)
    # Drawn pointing right around (0, 0), then turned.
    points = [(-half, -stem), (half - head, -stem), (half - head, -head), (half, 0),
              (half - head, head), (half - head, stem), (-half, stem)]
    turn = {"right": lambda px, py: (px, py), "left": lambda px, py: (-px, py),
            "down": lambda px, py: (py, px), "up": lambda px, py: (py, -px)}[direction]
    cx, cy = center
    pygame.draw.polygon(surface, layout.INK,
                        [(cx + tx, cy + ty) for tx, ty in (turn(px, py) for px, py in points)])


def _key_width(font: pygame.font.Font, role: str, label: str) -> int:
    """How wide one keyboard key is: square for an arrow and a short name, else the name
    plus paddings."""
    height = KEY_HEIGHTS[role]
    if layout.arrow(label):
        return height
    return max(height, font.size(label)[0] + 2 * KEY_PAD_X[role])


def keys_width(fonts: Fonts, role: str, keys: str) -> int:
    """How wide the keys of one key list entry are together, gaps included."""
    font = fonts.for_role(role)
    labels = layout.key_labels(keys)
    return sum(_key_width(font, role, label) for label in labels) + KEY_GAP * (len(labels) - 1)


def _keys(surface: pygame.Surface, fonts: Fonts, role: str, keys: str,
          pos: layout.Point) -> None:
    """The keys of one key list entry as keyboard keys from pos (top-left); arrow keys
    show an arrow instead of their name."""
    font = fonts.for_role(role)
    height = KEY_HEIGHTS[role]
    x, y = pos
    for label in layout.key_labels(keys):
        width = _key_width(font, role, label)
        rect = pygame.Rect(x, y, width, height)
        _lifted(surface, tuple(rect), layout.CREAM, KEY_RADIUS, KEY_LIFT)
        direction = layout.arrow(label)
        if direction:
            _arrow(surface, rect.center, height * 0.5, direction)
        else:
            image = font.render(label, True, layout.INK)
            surface.blit(image, image.get_rect(center=rect.center))
        x += width + KEY_GAP


def _texts(surface: pygame.Surface, texts: list[layout.ScreenText], fonts: Fonts) -> None:
    """Draw texts at their role's font (smaller if a text does not fit its role's width),
    placed by their role's anchor; key list entries are drawn as keys. The guide's
    paragraphs are left to _paragraphs()."""
    for text, pos, role, color in texts:
        if role == "paragraph":
            continue
        if role in layout.KEY_ROLES:
            _keys(surface, fonts, role, text, pos)
            continue
        image = role_font(fonts, role, text).render(text, True, color)
        rect = image.get_rect()
        setattr(rect, layout.text_anchor(role), pos)
        surface.blit(image, rect)


# --- Frames --------------------------------------------------------------------------------


def draw(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    """Draw one frame: a full-window screen (menu, settings, key list...), or the well,
    the cards around it and the panel over it."""
    if layout.full_screen(controller) is not None:
        _draw_full_screen(surface, controller, fonts)
        return
    surface.fill(layout.WINDOW_BG)
    _logo(surface, layout.LOGO_RECT)
    for card in layout.CARDS:
        _card(surface, card)
    _draw_well(surface, controller)
    _draw_previews(surface, controller)
    _texts(surface, layout.panel_texts(controller), fonts)
    overlay = layout.overlay_layout(controller)
    if overlay is not None:
        _draw_overlay(surface, *overlay, fonts)


def _draw_well(surface: pygame.Surface, controller: Controller) -> None:
    """The well with its grid dots, the locked cells, the ghost and the active piece."""
    game = controller.game
    _rounded(surface, layout.WELL, layout.WELL_RECT, layout.WELL_RADIUS)
    for dot in layout.grid_dots():
        pygame.draw.circle(surface, layout.GRID_DOT, dot, layout.GRID_DOT_RADIUS)
    locked = [(col, row, game.board.get(col, row))
              for row in range(HIDDEN_ROWS, HEIGHT) for col in range(WIDTH)
              if game.board.get(col, row) is not None]
    active = [] if game.is_over else [(col, row, game.active.type)
                                      for col, row in game.active.cells() if row >= HIDDEN_ROWS]
    blocks = [(*layout.cell_rect(col, row)[:2], layout.PIECE_COLORS[piece_type])
              for col, row, piece_type in locked + active]
    geometry = layout.block(layout.CELL)
    for x, y, colors in blocks:
        rect, radius = _block_square(x, y, layout.CELL, shadow=True)
        _rounded(surface, colors.shadow, rect, radius)
    if not game.is_over and controller.settings.ghost:
        # Outlines of the ghost go under the active piece's fills.
        piece_cells = set(game.active.cells())
        for col, row in game.ghost_cells():
            if row >= HIDDEN_ROWS and (col, row) not in piece_cells:
                _rounded(surface, layout.GHOST_OUTLINE, layout.ghost_rect(col, row),
                         layout.GHOST_RADIUS, width=layout.GHOST_WIDTH)
    for x, y, colors in blocks:
        rect, _ = _block_square(x, y, layout.CELL, shadow=False)
        _rounded(surface, colors.fill, rect, geometry.radius)


def _draw_previews(surface: pygame.Surface, controller: Controller) -> None:
    """The three next pieces and the held piece, each in its box."""
    game = controller.game
    boxes = list(zip(layout.NEXT_BOXES, game.next_types))
    held = None
    if game.held_type is not None:
        held = (layout.PIECE_COLORS[game.held_type] if game.can_hold
                else layout.dimmed_colors(game.held_type))
    for box in (*layout.NEXT_BOXES, layout.HOLD_BOX):
        _rounded(surface, layout.WELL, box, layout.BOX_RADIUS)
    for box, piece_type in boxes:
        _preview(surface, piece_type, box, layout.PIECE_COLORS[piece_type])
    if held is not None:
        _preview(surface, game.held_type, layout.HOLD_BOX, held)


def _preview(surface: pygame.Surface, piece_type: PieceType, box: layout.Rect,
             colors: layout.PieceColors) -> None:
    """A piece in orientation 0, centered in its preview box."""
    blocks = [(x, y, colors) for x, y in layout.preview_blocks(piece_type, box)]
    _blocks(surface, blocks, layout.PREVIEW_CELL)


def _draw_overlay(surface: pygame.Surface, panel: layout.Rect,
                  texts: list[layout.ScreenText], fonts: Fonts) -> None:
    """Shade the well with its own color and put the panel with its lines over it: the
    selected pause item on a dark button, the badge and this game's record on a peach
    plaque."""
    x, y, w, h = layout.WELL_RECT
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    _rounded(shade, (*layout.WELL, layout.SHADE_ALPHA), (0, 0, w, h), layout.WELL_RADIUS)
    surface.blit(shade, (x, y))
    _card(surface, panel, layout.PANEL_RADIUS, layout.PANEL_LIFT)
    shown = []
    for text, pos, role, color in texts:
        if role == "pause-item" and color == layout.HIGHLIGHT:
            _button(surface, layout.selection_rect(role, pos))
        elif role == "badge" or (role == "table-row" and color == layout.HIGHLIGHT):
            height = layout.OVERLAY_LINES[role][0]
            if role == "badge":
                width = role_font(fonts, role, text).size(text)[0] + 2 * layout.PLAQUE_PAD_X
            else:
                width = layout.OVERLAY_INNER_W
            _rounded(surface, layout.PEACH, (pos[0] - layout.PLAQUE_PAD_X,
                                             pos[1] - layout.PLAQUE_PAD_Y, width, height),
                     PLAQUE_RADIUS)
            color = layout.TEXT
        shown.append((text, pos, role, color))
    _texts(surface, shown, fonts)


def draw_sound_check(
    surface: pygame.Surface, check: SoundCheck, language: str, has_audio: bool, fonts: Fonts
) -> None:
    """Draw one frame of the sound check screen."""
    _screen(surface, layout.sound_check_texts(check, language, has_audio), fonts)


def _draw_full_screen(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    """The orange window with the screen's panel, title, lines and hint; the guide's
    paragraphs are wrapped and flowed down from the top of its text area."""
    texts = layout.full_screen_texts(controller)
    _screen(surface, texts, fonts)
    if layout.full_screen(controller) == "menu":
        _logo(surface, layout.MENU_LOGO_RECT)
    paragraphs = [(text, pos, color) for text, pos, role, color in texts if role == "paragraph"]
    if paragraphs:
        font = fonts.for_role("paragraph")
        color = paragraphs[0][2]
        for line, pos in guide_lines(fonts, [text for text, _, _ in paragraphs], paragraphs[0][1]):
            surface.blit(font.render(line, True, color), pos)


def _screen(surface: pygame.Surface, texts: list[layout.ScreenText], fonts: Fonts) -> None:
    """A full-window screen: the panel, dark buttons behind selected items, the texts."""
    surface.fill(layout.WINDOW_BG)
    _card(surface, layout.SCREEN_PANEL, layout.SCREEN_RADIUS, layout.PANEL_LIFT)
    for _, pos, role, color in texts:
        if color == layout.HIGHLIGHT and role in ("item", "setting", "row"):
            _button(surface, layout.selection_rect(role, pos))
    _texts(surface, texts, fonts)
