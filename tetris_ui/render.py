"""Draws the game state onto a pygame surface."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from tetris.board import HIDDEN_ROWS, HEIGHT, WIDTH
from tetris.pieces import PieceType, shape_cells
from tetris_ui import layout
from tetris_ui.input import Controller, Phase

SMALL_FONT_SIZE = 32
BIG_FONT_SIZE = 56
TABLE_FONT_SIZE = 26
GUIDE_FONT_SIZE = TABLE_FONT_SIZE  # the guide's paragraphs
VERSION_FONT_SIZE = 20  # the version in the main menu
TABLE_LINE_STEP = 28
FONT_SIZE_STEP = 2  # how much smaller each try is when a text does not fit


@dataclass(frozen=True)
class Fonts:
    """The fonts on screen: small for the panel and full-window screens, big for titles,
    table for the lines over the field. Smaller sizes for texts that do not fit are
    made on demand and kept."""

    small: pygame.font.Font
    big: pygame.font.Font
    table: pygame.font.Font
    _by_size: dict[int, pygame.font.Font] = field(default_factory=dict, repr=False)

    def sized(self, size: int) -> pygame.font.Font:
        """The built-in font at `size` pixels."""
        if size not in self._by_size:
            self._by_size[size] = pygame.font.Font(None, size)
        return self._by_size[size]


def make_fonts() -> Fonts:
    """Built-in pygame font, so no system fonts are needed. Requires pygame.font.init()."""
    fonts = Fonts(
        small=pygame.font.Font(None, SMALL_FONT_SIZE),
        big=pygame.font.Font(None, BIG_FONT_SIZE),
        table=pygame.font.Font(None, TABLE_FONT_SIZE),
    )
    fonts._by_size.update({SMALL_FONT_SIZE: fonts.small, BIG_FONT_SIZE: fonts.big,
                           TABLE_FONT_SIZE: fonts.table})
    return fonts


def fitted_size(fonts: Fonts, base_size: int, text: str, max_width: int) -> int:
    """The largest size from base_size down, in FONT_SIZE_STEP steps, at which the text
    fits max_width; layout.MIN_FONT_SIZE if even that is too wide."""
    size = base_size
    while size > layout.MIN_FONT_SIZE and fonts.sized(size).size(text)[0] > max_width:
        size = max(layout.MIN_FONT_SIZE, size - FONT_SIZE_STEP)
    return size


def fitted_font(fonts: Fonts, base_size: int, text: str, max_width: int) -> pygame.font.Font:
    """The font for a text that must fit max_width: base_size if it fits, else smaller."""
    return fonts.sized(fitted_size(fonts, base_size, text, max_width))


def screen_font_size(role: str) -> int:
    """The base font size of a full-window screen text with this role."""
    if role == "paragraph":
        return GUIDE_FONT_SIZE
    if role == "version":
        return VERSION_FONT_SIZE
    return BIG_FONT_SIZE if role == "title" else SMALL_FONT_SIZE


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
    font = fonts.sized(GUIDE_FONT_SIZE)
    x, y = origin
    lines = []
    for paragraph in paragraphs:
        for line in wrap_text(font, paragraph, layout.screen_text_width("paragraph")):
            lines.append((line, (x, y)))
            y += layout.GUIDE_LINE_STEP
        y += layout.GUIDE_PARAGRAPH_GAP
    return lines


def draw(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    """Draw one frame: a full-window screen (menu, settings, key list...), or the field,
    pieces, panel and overlay."""
    if layout.full_screen(controller) is not None:
        _draw_full_screen(surface, controller, fonts)
        return
    game = controller.game
    surface.fill(layout.WINDOW_BG)
    _draw_field(surface)
    for row in range(HIDDEN_ROWS, HEIGHT):
        for col in range(WIDTH):
            piece_type = game.board.get(col, row)
            if piece_type is not None:
                _draw_cell(surface, layout.cell_rect(col, row), piece_type)
    if not game.is_over:
        if controller.settings.ghost:
            # The ghost goes first so the active piece covers it where they overlap.
            ghost = layout.ghost_color(game.active.type)
            for col, row in game.ghost_cells():
                if row >= HIDDEN_ROWS:
                    _fill_ghost(surface, layout.cell_rect(col, row), ghost)
        for col, row in game.active.cells():
            if row >= HIDDEN_ROWS:
                _draw_cell(surface, layout.cell_rect(col, row), game.active.type)
    _draw_preview(surface, game.next_type, layout.PREVIEW_X, layout.PREVIEW_Y,
                  layout.PIECE_COLORS[game.next_type])
    if game.held_type is not None:
        held_color = (layout.PIECE_COLORS[game.held_type] if game.can_hold
                      else layout.dimmed_color(game.held_type))
        _draw_preview(surface, game.held_type, layout.HOLD_X, layout.HOLD_Y, held_color)
    for text, pos in layout.panel_texts(controller):
        font = fitted_font(fonts, SMALL_FONT_SIZE, text, layout.PANEL_W)
        surface.blit(font.render(text, True, layout.TEXT), pos)
    overlay = layout.overlay_lines(controller)
    if overlay:
        _draw_overlay(surface, overlay, fonts, paused=controller.phase is Phase.PLAYING)


def _draw_field(surface: pygame.Surface) -> None:
    """Draw the field background, the grid lines and the border."""
    field = pygame.Rect(layout.FIELD_X, layout.FIELD_Y, layout.FIELD_W, layout.FIELD_H)
    surface.fill(layout.FIELD_BG, field)
    for col in range(1, WIDTH):
        x = field.x + col * layout.CELL
        pygame.draw.line(surface, layout.GRID, (x, field.top), (x, field.bottom - 1))
    for row in range(1, HEIGHT - HIDDEN_ROWS):
        y = field.y + row * layout.CELL
        pygame.draw.line(surface, layout.GRID, (field.left, y), (field.right - 1, y))
    pygame.draw.rect(surface, layout.BORDER, field.inflate(4, 4), width=2)


def _draw_cell(surface: pygame.Surface, rect: layout.Rect, piece_type: PieceType) -> None:
    """Draw one cell of a piece in the piece's color."""
    _fill_cell(surface, rect, layout.PIECE_COLORS[piece_type])


def _fill_cell(surface: pygame.Surface, rect: layout.Rect, color: layout.Color) -> None:
    """Fill a cell with a color and outline it."""
    surface.fill(color, rect)
    pygame.draw.rect(surface, layout.CELL_OUTLINE, rect, width=1)


def _fill_ghost(surface: pygame.Surface, rect: layout.Rect, color: layout.Color) -> None:
    """Fill a ghost cell without an outline, leaving its top and left grid lines visible."""
    x, y, w, h = rect
    surface.fill(color, (x + 1, y + 1, w - 1, h - 1))


def _draw_preview(
    surface: pygame.Surface, piece_type: PieceType, x: int, y: int, color: layout.Color
) -> None:
    """Draw a piece in orientation 0 in a 4 x 2 cell preview box at (x, y)."""
    for r, c in shape_cells(piece_type, 0):
        _fill_cell(surface, (x + c * layout.CELL, y + r * layout.CELL, layout.CELL, layout.CELL), color)


def _draw_full_screen(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    """Fill the window with the screen's title, lines and hint; the guide's paragraphs are
    wrapped and flowed down from the top of its text area."""
    surface.fill(layout.WINDOW_BG)
    texts = layout.full_screen_texts(controller)
    for text, pos, role, color in texts:
        if role == "paragraph":
            continue
        font = fitted_font(fonts, screen_font_size(role), text, layout.screen_text_width(role))
        image = font.render(text, True, color)
        if role in ("key", "action"):
            surface.blit(image, pos)
        elif role == "version":
            surface.blit(image, image.get_rect(bottomright=pos))
        else:
            surface.blit(image, image.get_rect(center=pos))
    paragraphs = [(text, pos, color) for text, pos, role, color in texts if role == "paragraph"]
    if paragraphs:
        font = fonts.sized(GUIDE_FONT_SIZE)
        color = paragraphs[0][2]
        for line, pos in guide_lines(fonts, [text for text, _, _ in paragraphs], paragraphs[0][1]):
            surface.blit(font.render(line, True, color), pos)


def _draw_overlay(
    surface: pygame.Surface, lines: list[tuple[str, layout.Color]], fonts: Fonts, paused: bool
) -> None:
    """Shade the field and write the overlay lines over it.

    The first line is a big title; the other lines go below it in the table font. The
    pause menu is centered on the field; the game over lines start near its top.
    """
    shade = pygame.Surface((layout.FIELD_W, layout.FIELD_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, layout.OVERLAY_ALPHA))
    surface.blit(shade, (layout.FIELD_X, layout.FIELD_Y))
    center_x = layout.FIELD_X + layout.FIELD_W // 2
    (title, title_color), rest = lines[0], lines[1:]
    if paused:
        title_y = layout.FIELD_Y + layout.FIELD_H // 2 - 40
    else:
        title_y = layout.FIELD_Y + 110
    font = fitted_font(fonts, BIG_FONT_SIZE, title, layout.FIELD_W)
    image = font.render(title, True, title_color)
    surface.blit(image, image.get_rect(center=(center_x, title_y)))
    y = title_y + 60
    for text, color in rest:
        font = fitted_font(fonts, TABLE_FONT_SIZE, text, layout.FIELD_W)
        image = font.render(text, True, color)
        surface.blit(image, image.get_rect(center=(center_x, y)))
        y += TABLE_LINE_STEP
