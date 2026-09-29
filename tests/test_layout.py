"""The layout's palette, geometry and cards, without pygame."""

import pytest

from tetris.pieces import PieceType
from tetris_ui import layout
from tetris_ui.layout import PieceColors


def overlaps(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def with_shadow(rect, lift: int = layout.CARD_LIFT):
    x, y, w, h = rect
    return x, y, w + lift, h + lift


def inside(inner, outer) -> bool:
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh


def test_window_and_field():
    assert layout.WINDOW_SIZE == (960, 720)
    assert (layout.FIELD_X, layout.FIELD_Y, layout.CELL) == (330, 60, 30)
    assert layout.WELL_RECT == (318, 48, 324, 624)
    assert layout.cell_rect(0, 21) == (330, 630, 30, 30)


def test_palette():
    assert layout.WINDOW_BG == (232, 86, 42)
    assert layout.WELL == (217, 73, 29)
    assert layout.SHADOW == (184, 58, 20)
    assert layout.CREAM == (255, 244, 230)
    assert layout.PEACH == (255, 197, 158)
    assert layout.INK == (38, 10, 2)


def test_mixed_colors():
    assert layout.blend((255, 255, 255), (0, 0, 0), 0.5) == (128, 128, 128)
    assert layout.GRID_DOT == (205, 68, 26)
    assert layout.GHOST_OUTLINE == (236, 159, 130)
    assert layout.MUTED == (99, 76, 66)
    assert layout.dimmed_colors(PieceType.T).fill == (232, 107, 88)


def test_piece_colors_follow_the_spec():
    assert layout.PIECE_COLORS == {
        PieceType.I: PieceColors((255, 244, 230), (184, 58, 20)),
        PieceType.O: PieceColors((255, 213, 74), (169, 80, 12)),
        PieceType.T: PieceColors((255, 158, 176), (163, 48, 74)),
        PieceType.S: PieceColors((255, 181, 102), (164, 72, 17)),
        PieceType.Z: PieceColors((155, 34, 51), (77, 11, 20)),
        PieceType.J: PieceColors((110, 50, 28), (46, 18, 8)),
        PieceType.L: PieceColors((255, 197, 158), (176, 64, 26)),
    }


def test_blocks():
    assert layout.block(30) == (1, 28, 6, 5)
    assert layout.block(22) == (1, 20, 4, 4)
    assert layout.ghost_rect(4, 20) == (452, 602, 26, 26)


def test_grid_dots_sit_on_inner_crossings():
    dots = layout.grid_dots()
    assert len(dots) == 9 * 19
    assert (360, 90) in dots and (330, 60) not in dots and (630, 660) not in dots


def test_cards_fit_and_do_not_touch():
    window = (0, 0, *layout.WINDOW_SIZE)
    boxes = [with_shadow(card) for card in layout.CARDS]
    for i, box in enumerate(boxes):
        assert inside(box, window), layout.CARDS[i]
        assert not overlaps(box, layout.WELL_RECT), layout.CARDS[i]
        for other in boxes[i + 1:]:
            assert not overlaps(box, other), (layout.CARDS[i], other)
    assert not overlaps(layout.LOGO_RECT, layout.SCORE_CARD)


def test_preview_boxes_sit_in_their_cards():
    for box in layout.NEXT_BOXES:
        assert inside(box, layout.NEXT_CARD)
    assert inside(layout.HOLD_BOX, layout.HOLD_CARD)


@pytest.mark.parametrize("piece_type", list(PieceType))
def test_previews_are_centered_in_their_box(piece_type):
    box = layout.HOLD_BOX
    corners = layout.preview_blocks(piece_type, box)
    size, shift = layout.PREVIEW_CELL, layout.block(layout.PREVIEW_CELL).shift
    left = min(x for x, _ in corners)
    right = max(x for x, _ in corners) + size + shift
    top = min(y for _, y in corners)
    bottom = max(y for _, y in corners) + size + shift
    assert inside((left, top, right - left, bottom - top), box)
    assert abs((left - box[0]) - (box[0] + box[2] - right)) <= 1


def test_screen_panel_and_version():
    assert layout.SCREEN_PANEL == (160, 40, 640, 600)
    assert layout.VERSION_POS == (944, 708)


def test_roles_have_fonts_and_anchors():
    for role in layout.ROLE_FONTS:
        assert layout.text_anchor(role) in ("topleft", "midleft", "bottomright", "center")
    assert {spec.family for spec in layout.ROLE_FONTS.values()} == {"Unbounded", "Onest"}
    for role in ("game-title", "title", "brand", "value-big", "value", "item", "pause-item"):
        assert layout.ROLE_FONTS[role].family == "Unbounded", role
    for role in ("setting", "row", "entry", "label", "paragraph", "hint"):
        assert layout.ROLE_FONTS[role].family == "Onest", role


def test_key_labels_and_arrows():
    assert layout.key_labels("C / Shift") == ["C", "Shift"]
    assert [layout.arrow(label) for label in layout.key_labels("Left / Right")] == ["left", "right"]
    assert [layout.arrow(label) for label in layout.key_labels("Вверх / X")] == ["up", None]
    assert layout.arrow("Вниз") == "down"
