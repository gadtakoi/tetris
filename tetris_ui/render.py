"""Draws the game state onto a pygame surface."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from tetris.board import HIDDEN_ROWS, HEIGHT, WIDTH
from tetris.pieces import PieceType, shape_cells
from tetris_ui import layout
from tetris_ui.input import Controller


@dataclass(frozen=True)
class Fonts:
    small: pygame.font.Font
    big: pygame.font.Font


def make_fonts() -> Fonts:
    """Built-in pygame font, so no system fonts are needed. Requires pygame.font.init()."""
    return Fonts(small=pygame.font.Font(None, 32), big=pygame.font.Font(None, 56))


def draw(surface: pygame.Surface, controller: Controller, fonts: Fonts) -> None:
    game = controller.game
    surface.fill(layout.WINDOW_BG)
    _draw_field(surface)
    for row in range(HIDDEN_ROWS, HEIGHT):
        for col in range(WIDTH):
            piece_type = game.board.get(col, row)
            if piece_type is not None:
                _draw_cell(surface, layout.cell_rect(col, row), piece_type)
    if not game.is_over:
        for col, row in game.active.cells():
            if row >= HIDDEN_ROWS:
                _draw_cell(surface, layout.cell_rect(col, row), game.active.type)
    _draw_preview(surface, game.next_type)
    for text, pos in layout.panel_texts(controller):
        surface.blit(fonts.small.render(text, True, layout.TEXT), pos)
    overlay = layout.overlay_texts(controller)
    if overlay:
        _draw_overlay(surface, overlay, fonts)


def _draw_field(surface: pygame.Surface) -> None:
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
    surface.fill(layout.PIECE_COLORS[piece_type], rect)
    pygame.draw.rect(surface, layout.CELL_OUTLINE, rect, width=1)


def _draw_preview(surface: pygame.Surface, piece_type: PieceType) -> None:
    for r, c in shape_cells(piece_type, 0):
        rect = (
            layout.PREVIEW_X + c * layout.CELL,
            layout.PREVIEW_Y + r * layout.CELL,
            layout.CELL,
            layout.CELL,
        )
        _draw_cell(surface, rect, piece_type)


def _draw_overlay(surface: pygame.Surface, lines: list[str], fonts: Fonts) -> None:
    shade = pygame.Surface((layout.FIELD_W, layout.FIELD_H), pygame.SRCALPHA)
    shade.fill((0, 0, 0, layout.OVERLAY_ALPHA))
    surface.blit(shade, (layout.FIELD_X, layout.FIELD_Y))
    center_x = layout.FIELD_X + layout.FIELD_W // 2
    y = layout.FIELD_Y + layout.FIELD_H // 2 - 40 * (len(lines) - 1)
    for i, line in enumerate(lines):
        font = fonts.big if i == 0 else fonts.small
        image = font.render(line, True, layout.TEXT)
        surface.blit(image, image.get_rect(center=(center_x, y)))
        y += 70
