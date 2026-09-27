"""Draws the game state onto a pygame surface."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from tetris.board import HIDDEN_ROWS, HEIGHT, WIDTH
from tetris.pieces import PieceType, shape_cells
from tetris_ui import layout
from tetris_ui.input import Controller

TABLE_FONT_SIZE = 26
TABLE_LINE_STEP = 28


@dataclass(frozen=True)
class Fonts:
    """The fonts on screen: small for the panel and key screen, big for titles, table for high score rows."""

    small: pygame.font.Font
    big: pygame.font.Font
    table: pygame.font.Font


def make_fonts() -> Fonts:
    """Built-in pygame font, so no system fonts are needed. Requires pygame.font.init()."""
    return Fonts(
        small=pygame.font.Font(None, 32),
        big=pygame.font.Font(None, 56),
        table=pygame.font.Font(None, TABLE_FONT_SIZE),
    )


def draw(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    """Draw one frame: the key screen, or the field, pieces, panel and overlay."""
    if layout.key_screen(controller) is not None:
        _draw_key_screen(surface, controller, fonts)
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
        # The ghost goes first so the active piece covers it where they overlap.
        ghost = layout.ghost_color(game.active.type)
        for col, row in game.ghost_cells():
            if row >= HIDDEN_ROWS:
                _fill_ghost(surface, layout.cell_rect(col, row), ghost)
        for col, row in game.active.cells():
            if row >= HIDDEN_ROWS:
                _draw_cell(surface, layout.cell_rect(col, row), game.active.type)
    _draw_preview(surface, game.next_type)
    for text, pos in layout.panel_texts(controller):
        surface.blit(fonts.small.render(text, True, layout.TEXT), pos)
    overlay = layout.overlay_lines(controller)
    if overlay:
        _draw_overlay(surface, overlay, fonts)


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


def _draw_preview(surface: pygame.Surface, piece_type: PieceType) -> None:
    """Draw the next piece in orientation 0 in the preview box."""
    for r, c in shape_cells(piece_type, 0):
        rect = (
            layout.PREVIEW_X + c * layout.CELL,
            layout.PREVIEW_Y + r * layout.CELL,
            layout.CELL,
            layout.CELL,
        )
        _draw_cell(surface, rect, piece_type)


def _draw_key_screen(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    """Fill the window with the title, the hotkey table and the hint."""
    surface.fill(layout.WINDOW_BG)
    for text, pos, role in layout.key_screen_texts(controller):
        font = fonts.big if role == "title" else fonts.small
        color = layout.HIGHLIGHT if role == "key" else layout.TEXT
        image = font.render(text, True, color)
        if role in ("title", "hint"):
            surface.blit(image, image.get_rect(center=pos))
        else:
            surface.blit(image, pos)


def _draw_overlay(
    surface: pygame.Surface, lines: list[tuple[str, layout.Color]], fonts: Fonts
) -> None:
    """Shade the field and write the overlay lines over it.

    The first line is a big title; the other lines go below it in the table font. A lone
    title (PAUSE) is centered on the field.
    """
    shade = pygame.Surface((layout.FIELD_W, layout.FIELD_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, layout.OVERLAY_ALPHA))
    surface.blit(shade, (layout.FIELD_X, layout.FIELD_Y))
    center_x = layout.FIELD_X + layout.FIELD_W // 2
    (title, title_color), rest = lines[0], lines[1:]
    # A lone title (PAUSE) sits in the middle; with more lines it moves up to make room.
    title_y = layout.FIELD_Y + (layout.FIELD_H // 2 if not rest else 110)
    image = fonts.big.render(title, True, title_color)
    surface.blit(image, image.get_rect(center=(center_x, title_y)))
    y = title_y + 60
    for text, color in rest:
        image = fonts.table.render(text, True, color)
        surface.blit(image, image.get_rect(center=(center_x, y)))
        y += TABLE_LINE_STEP
