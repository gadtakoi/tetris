import json
import os
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest

pygame = pytest.importorskip("pygame")

from tests.helpers import ScriptedRng  # noqa: E402
from tetris.board import HEIGHT, HIDDEN_ROWS, WIDTH  # noqa: E402
from tetris.game import ActivePiece, Game  # noqa: E402
from tetris.highscores import Entry, HighScores  # noqa: E402
from tetris.pieces import PieceType  # noqa: E402
from tetris_ui import app, guide, layout, menus, render, storage  # noqa: E402
from tetris_ui.audio import Audio  # noqa: E402
from tetris_ui.input import Controller, Key, Phase, Sound  # noqa: E402
from tetris_ui.settings import Settings  # noqa: E402
from tetris_ui.soundcheck import ITEMS, MUSIC, CheckKey, SoundCheck  # noqa: E402

VISIBLE_CELLS = [(c, r) for r in range(HIDDEN_ROWS, HEIGHT) for c in range(WIDTH)]
T_GHOST = [(4, 20), (3, 21), (4, 21), (5, 21)]


@pytest.fixture(autouse=True)
def pygame_session():
    pygame.init()
    yield
    pygame.quit()


def draw_game(game: Game, controller: Controller | None = None) -> pygame.Surface:
    surface = pygame.Surface(layout.WINDOW_SIZE)
    render.draw(surface, controller or Controller(game), render.make_fonts())
    return surface


def pixel(surface: pygame.Surface, point) -> tuple[int, int, int]:
    return tuple(surface.get_at(point))[:3]


def center_color(surface: pygame.Surface, rect) -> tuple[int, int, int]:
    x, y, w, h = rect
    return pixel(surface, (x + w // 2, y + h // 2))


def colors_in(surface: pygame.Surface, rect) -> set[tuple[int, int, int]]:
    rect = pygame.Rect(rect)
    return {pixel(surface, (x, y)) for x in range(rect.left, rect.right)
            for y in range(rect.top, rect.bottom)}


def game_with_hidden_active_piece() -> Game:
    """Game whose active piece sits entirely in the hidden rows, so it is not drawn."""
    game = Game(rng=ScriptedRng([PieceType.I, PieceType.T]))
    game.active = ActivePiece(PieceType.I, 0, 3, -1)  # cells in row 0
    return game


def assert_field_is_empty(surface: pygame.Surface) -> None:
    """Every visible cell shows the well in its middle (a ghost is only an outline)."""
    for cell in VISIBLE_CELLS:
        assert center_color(surface, layout.cell_rect(*cell)) == layout.WELL, cell


def fill(piece_type: PieceType) -> tuple[int, int, int]:
    return layout.PIECE_COLORS[piece_type].fill


# --- Rendering: the well -----------------------------------------------------------


def test_empty_field():
    assert_field_is_empty(draw_game(game_with_hidden_active_piece()))


def test_locked_cell_color():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 21)], PieceType.Z)
    surface = draw_game(game)
    assert pixel(surface, (345, 645)) == (155, 34, 51)


def test_hidden_rows_are_not_drawn():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 1)], PieceType.S)
    assert_field_is_empty(draw_game(game))


def test_grid_dots():
    surface = draw_game(Game(rng=ScriptedRng([PieceType.T, PieceType.S])))
    assert pixel(surface, (360, 90)) == (205, 68, 26)


def test_hard_shadow_of_a_block():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    game.board.place([(0, 21)], PieceType.Z)
    surface = draw_game(game)
    assert pixel(surface, (360, 650)) == (77, 11, 20)


def test_shadow_does_not_cover_a_neighbor():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 20), (0, 21)], PieceType.J)
    assert pixel(draw_game(game), (345, 645)) == (110, 50, 28)


def test_active_piece_color():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game)
    for cell in game.active.cells():
        if cell[1] >= HIDDEN_ROWS:
            assert center_color(surface, layout.cell_rect(*cell)) == (255, 158, 176)


def test_ghost_of_t_piece():
    surface = draw_game(Game(rng=ScriptedRng([PieceType.T, PieceType.S])))
    assert pixel(surface, (452, 615)) == (236, 159, 130)
    assert pixel(surface, (465, 615)) == (217, 73, 29)
    for cell in T_GHOST:
        assert center_color(surface, layout.cell_rect(*cell)) == layout.WELL


def test_grid_shows_through_the_ghost():
    surface = draw_game(Game(rng=ScriptedRng([PieceType.T, PieceType.S])))
    assert layout.cell_rect(4, 20)[:2] == (450, 600)
    assert pixel(surface, (450, 600)) == (205, 68, 26)


def test_piece_on_floor_covers_its_ghost():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    for _ in range(18):
        game.step_down()
    surface = draw_game(game)
    for cell in game.active.cells():
        assert center_color(surface, layout.cell_rect(*cell)) == (255, 158, 176)


def test_ghost_switched_off():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game, Controller(game, settings=Settings(ghost=False)))
    assert pixel(surface, (452, 615)) == layout.WELL


def test_no_ghost_after_game_over():
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    surface = draw_game(game)
    assert layout.GHOST_OUTLINE not in colors_in(surface, layout.WELL_RECT)


def test_game_over_hides_active_piece_and_shades_field():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    active_cells = [cell for cell in game.active.cells() if cell[1] >= HIDDEN_ROWS]
    game.is_over = True
    surface = draw_game(game)
    for cell in active_cells:
        assert center_color(surface, layout.cell_rect(*cell)) != fill(PieceType.T)


def test_pause_keeps_board_visible_under_shade():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 21)], PieceType.Z)
    controller = Controller(game)
    controller.key_down(Key.PAUSE)
    surface = draw_game(game, controller)
    color = pixel(surface, (345, 645))
    assert color not in (fill(PieceType.Z), layout.WELL)  # dimmed, not hidden
    assert pixel(surface, (270, 130)) == layout.CREAM  # the cards are not shaded


# --- Rendering: cards around the well -------------------------------------------------


def test_window_background_and_a_card():
    surface = draw_game(Game(rng=ScriptedRng([PieceType.T, PieceType.S])))
    assert pixel(surface, (10, 10)) == (232, 86, 42)
    assert pixel(surface, (270, 130)) == (255, 244, 230)
    assert pixel(surface, (283, 200)) == (184, 58, 20)


def preview_centers(piece_type: PieceType, box) -> list[tuple[int, int]]:
    half = layout.PREVIEW_CELL // 2
    return [(x + half, y + half) for x, y in layout.preview_blocks(piece_type, box)]


def test_next_piece_preview():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.I, PieceType.S, PieceType.Z]))
    surface = draw_game(game)
    centers = preview_centers(PieceType.I, layout.NEXT_BOXES[0])
    assert len({y for _, y in centers}) == 1  # one horizontal row
    assert [pixel(surface, c) for c in centers] == [(255, 244, 230)] * 4


def test_three_next_pieces():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S, PieceType.Z, PieceType.O]))
    assert game.next_types == (PieceType.S, PieceType.Z, PieceType.O)
    surface = draw_game(game)
    for piece_type, box in zip(game.next_types, layout.NEXT_BOXES):
        for center in preview_centers(piece_type, box):
            assert pixel(surface, center) == fill(piece_type), piece_type


def test_held_piece_on_the_panel():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S, PieceType.Z]))
    game.hold()
    game.hard_drop()  # hold is allowed again
    surface = draw_game(game)
    for center in preview_centers(PieceType.T, layout.HOLD_BOX):
        assert pixel(surface, center) == (255, 158, 176)


def test_held_piece_is_dimmed_while_hold_is_used():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S, PieceType.Z]))
    game.hold()
    surface = draw_game(game)
    for center in preview_centers(PieceType.T, layout.HOLD_BOX):
        assert pixel(surface, center) == (232, 107, 88)


def test_empty_hold_slot():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game)
    radius = layout.BOX_RADIUS
    inner = pygame.Rect(layout.HOLD_BOX).inflate(-2 * radius, -2 * radius)
    assert colors_in(surface, inner) == {layout.WELL}
    assert "HOLD" in layout.screen_texts(Controller(game))


def placed_rect(fonts, role: str, text: str, pos) -> pygame.Rect:
    rect = render.text_rect(fonts, role, text, pos)
    if role not in layout.KEY_ROLES:
        size = render.fitted_size(fonts, layout.ROLE_FONTS[role], text,
                                  layout.screen_text_width(role))
        assert size >= min(layout.MIN_FONT_SIZE, layout.ROLE_FONTS[role].size), text
        assert rect.width <= layout.screen_text_width(role), text
    return rect


def extreme_panel(language: str) -> Controller:
    settings = Settings(language=language, music_on=False, sound_on=False, music_volume=100)
    controller = Controller(Game(seed=1), settings=settings)
    controller.game.score = 9_999_999
    controller.game.lines, controller.game.level = 99_999, 99
    return controller


def card_of(pos) -> tuple:
    return next((card for card in layout.CARDS if pygame.Rect(card).collidepoint(pos)),
                (0, 0, 0, 0))


@pytest.mark.parametrize("language", ["en", "ru"])
def test_panel_texts_fit_their_cards(language):
    fonts = render.make_fonts()
    for text, pos, role, _ in layout.panel_texts(extreme_panel(language)):
        rect = placed_rect(fonts, role, text, pos)
        if role == "brand":
            assert rect.left >= layout.LOGO_RECT[0] + layout.LOGO_RECT[2], text
            assert rect.right <= layout.SCORE_CARD[0] + layout.SCORE_CARD[2], text
            continue
        card = pygame.Rect(card_of(pos)).inflate(-2 * layout.CARD_PAD_X, 0)
        assert card.contains(rect), (text, rect, card)
        if role == "card-key":
            assert rect.right <= layout.CONTROL_ACTION_X - 8, text


def test_keys_are_drawn_as_keys_with_arrows():
    fonts = render.make_fonts()
    height = render.KEY_HEIGHTS["key"]
    assert render.keys_width(fonts, "key", "Left / Right") == 2 * height + render.KEY_GAP
    assert render.keys_width(fonts, "key", "C / Shift") > 2 * height
    surface = draw_game(Game(seed=1))
    x, y = next(pos for text, pos, role, _ in layout.panel_texts(Controller(Game(seed=1)))
                if role == "card-key" and text == "Left / Right")
    cap = render.KEY_HEIGHTS["card-key"]
    assert layout.INK in colors_in(surface, (x, y, cap, cap))  # the arrow in the first key
    assert layout.CREAM in colors_in(surface, (x, y, cap, cap))


# --- Rendering: fonts -------------------------------------------------------------------


def test_fonts_come_with_the_game():
    fonts = render.make_fonts()
    assert sorted(path.name for path in render.FONT_DIR.glob("*.ttf")) == sorted(
        layout.FONT_FILES.values())
    assert (render.FONT_DIR / "OFL.txt").is_file()
    assert fonts.for_role("game-title").name == "Unbounded"
    assert fonts.for_role("paragraph").name == "Onest"
    for (family, weight), _ in layout.FONT_FILES.items():
        font = fonts.get(layout.FontSpec(family, weight, 20))
        assert (font.name, font.style_name) == (family, weight)


def glyph(font, char: str):
    image = font.render(char, True, (255, 255, 255), (0, 0, 0))
    return image.get_size(), pygame.image.tobytes(image, "RGB")


def missing_chars(fonts, entries) -> list[tuple[str, str]]:
    """(role, char) of every character not in the font of its text's role."""
    chars_by_role: dict[str, set[str]] = {}
    for text, role in entries:
        chars_by_role.setdefault(role, set()).update(set(text) - {" "})
    missing = []
    for role, chars in chars_by_role.items():
        font = fonts.for_role(role)
        blank = glyph(font, "")  # private use area: not in the font
        missing += [(role, char) for char in sorted(chars) if glyph(font, char) == blank]
    return missing


@pytest.mark.parametrize("language", ["en", "ru"])
def test_every_character_is_in_the_font(language):
    fonts = render.make_fonts()
    blank = glyph(fonts.for_role("paragraph"), "")
    assert glyph(fonts.for_role("paragraph"), "") == blank  # the check sees a gap
    controller = Controller(Game(seed=1), settings=Settings(language=language))
    assert missing_chars(fonts, layout.all_screen_entries(controller)) == []


def test_fitted_size_stops_at_the_minimum():
    fonts = render.make_fonts()
    spec = layout.FontSpec(layout.ONEST, layout.REGULAR, 32)
    assert render.fitted_size(fonts, spec, "Ш" * 100, 50) == layout.MIN_FONT_SIZE


def test_long_title_fits_the_panel():
    fonts = render.make_fonts()
    spec = layout.ROLE_FONTS["overlay-title"]
    assert fonts.get(spec).size("ИГРА ОКОНЧЕНА")[0] > layout.OVERLAY_INNER_W  # must shrink
    font = render.role_font(fonts, "overlay-title", "ИГРА ОКОНЧЕНА")
    assert font.size("ИГРА ОКОНЧЕНА")[0] <= layout.OVERLAY_INNER_W == 240


def test_english_texts_keep_their_size():
    fonts = render.make_fonts()
    spec = layout.ROLE_FONTS["overlay-title"]
    for text in ("GAME OVER", "PAUSE"):
        assert render.fitted_size(fonts, spec, text, layout.OVERLAY_INNER_W) == spec.size
    sound = layout.ROLE_FONTS["sound"]
    assert render.fitted_size(fonts, sound, "SOUND 100%", layout.screen_text_width("sound")) == 15


# --- Rendering: the panel over the well ------------------------------------------------


def finished(language: str, record: bool) -> Controller:
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    table = HighScores()
    for place in range(9):
        table.add(Entry("Ш" * 10, 9_999_999 - place, 0, 0))
    game.score = 340 if record else 0
    if not record:
        table.add(Entry("Ш" * 10, 1_000_000, 0, 0))
    controller = Controller(game, table, settings=Settings(language=language))
    controller.text_input("Ш" * 10)
    return controller


def overlay_controllers(language: str) -> list[Controller]:
    paused = Controller(Game(seed=1), settings=Settings(language=language))
    paused.key_down(Key.PAUSE)
    return [paused, finished(language, record=True), finished(language, record=False)]


@pytest.mark.parametrize("language", ["en", "ru"])
def test_overlay_texts_fit_the_panel(language):
    fonts = render.make_fonts()
    for controller in overlay_controllers(language):
        panel, texts = layout.overlay_layout(controller)
        assert pygame.Rect(layout.WELL_RECT).contains(pygame.Rect(panel))
        inner = pygame.Rect(panel).inflate(-2 * layout.OVERLAY_PAD_X, 0)
        rects = []
        for text, pos, role, _ in texts:
            rect = placed_rect(fonts, role, text, pos)
            assert inner.contains(rect), text
            rects.append(rect)
        for i, rect in enumerate(rects):
            assert rect.collidelist(rects[i + 1:]) == -1, texts[i][0]
        draw_game(controller.game, controller)  # renders without errors


def test_full_table_fits_the_well():
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    table = HighScores()
    for place in range(10):
        table.add(Entry("Ш" * 10, 9_999_999 - place, 0, 0))
    controller = Controller(game, table)
    assert controller.phase is Phase.TABLE
    panel, texts = layout.overlay_layout(controller)
    assert len([t for t in texts if t[2] == "table-row"]) == 10
    assert pygame.Rect(layout.WELL_RECT).contains(pygame.Rect(panel))


def button_color(surface, role: str, pos) -> tuple[int, int, int]:
    """The color just inside the left end of the button a selected item would have."""
    x, y, w, h = layout.selection_rect(role, pos)
    return pixel(surface, (x + 3, y + h // 2))


def test_pause_selection_is_a_dark_button():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    controller = Controller(game)
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.DOWN)
    surface = draw_game(game, controller)
    _, texts = layout.overlay_layout(controller)
    items = {text: pos for text, pos, role, _ in texts if role == "pause-item"}
    assert button_color(surface, "pause-item", items["Main menu"]) == layout.INK
    assert button_color(surface, "pause-item", items["Continue"]) == layout.CREAM


def test_new_record_row_on_a_peach_plaque():
    table = HighScores()
    table.add(Entry("ANNA", 1200, 13, 1))
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    game.score = 340
    controller = Controller(game, table)
    controller.text_input("Ann")
    controller.key_down(Key.RESTART)
    surface = draw_game(game, controller)
    _, texts = layout.overlay_layout(controller)
    rows = {text: pos for text, pos, role, _ in texts if role == "table-row"}
    x, y = rows["2. Ann 340"]
    assert pixel(surface, (x - 4, y + 10)) == layout.PEACH
    x, y = rows["1. ANNA 1200"]
    assert pixel(surface, (x - 4, y + 10)) == layout.CREAM


def test_new_record_badge():
    controller = finished("en", record=True)
    surface = draw_game(controller.game, controller)
    _, texts = layout.overlay_layout(controller)
    ((x, y),) = [pos for _, pos, role, _ in texts if role == "badge"]
    assert pixel(surface, (x - 4, y + 10)) == layout.PEACH


# --- Window and events -----------------------------------------------------


def test_window_size_and_title():
    screen = app.create_window()
    assert screen.get_size() == (960, 720)
    assert pygame.display.get_caption()[0] == "Tetris Shmetris"


def test_window_icon_is_the_logo():
    icon = pygame.image.load(app.ICON_FILE)
    width, height = icon.get_size()
    assert width == height >= 256  # enough for the exe's biggest icon
    assert icon.get_at((0, 0)).a == 0  # rounded corners
    assert tuple(icon.get_at((width // 2, 40)))[:3] == layout.WINDOW_BG
    assert app.ICON_FILE.parent == render.FONT_DIR.parent  # inside the package, as the fonts


@pytest.fixture
def data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    return tmp_path


def test_main_runs_frames(data_dir):
    assert app.main(max_frames=3) == 0


def test_quit_event_ends_main_early(data_dir):
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    start = time.monotonic()
    assert app.main(max_frames=600) == 0  # 600 frames would take ~10 s
    assert time.monotonic() - start < 3


@pytest.mark.parametrize(
    ("pygame_key", "key"),
    [
        (pygame.K_LEFT, Key.LEFT),
        (pygame.K_RIGHT, Key.RIGHT),
        (pygame.K_DOWN, Key.DOWN),
        (pygame.K_SPACE, Key.HARD_DROP),
        (pygame.K_c, Key.HOLD),
        (pygame.K_LSHIFT, Key.HOLD),
        (pygame.K_RSHIFT, Key.HOLD),
        (pygame.K_UP, Key.UP),
        (pygame.K_x, Key.ROTATE_CW),
        (pygame.K_z, Key.ROTATE_CCW),
        (pygame.K_LCTRL, Key.ROTATE_CCW),
        (pygame.K_p, Key.PAUSE),
        (pygame.K_ESCAPE, Key.ESCAPE),
        (pygame.K_RETURN, Key.RESTART),
        (pygame.K_m, Key.TOGGLE_MUSIC),
        (pygame.K_n, Key.TOGGLE_SOUND),
        (pygame.K_MINUS, Key.VOLUME_DOWN),
        (pygame.K_KP_MINUS, Key.VOLUME_DOWN),
        (pygame.K_EQUALS, Key.VOLUME_UP),
        (pygame.K_PLUS, Key.VOLUME_UP),
        (pygame.K_KP_PLUS, Key.VOLUME_UP),
        (pygame.K_9, Key.SFX_DOWN),
        (pygame.K_KP9, Key.SFX_DOWN),
        (pygame.K_0, Key.SFX_UP),
        (pygame.K_KP0, Key.SFX_UP),
        (pygame.K_F1, Key.HELP),
        (pygame.K_F2, Key.GUIDE),
    ],
)
def test_key_map(pygame_key, key):
    assert app.KEY_MAP[pygame_key] is key


def test_unmapped_key_sends_no_command():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    active = game.active
    controller = Controller(game)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
    assert app.handle_event(event, controller)
    assert game.active == active


def test_keydown_event_reaches_game():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    controller = Controller(game)
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), controller)
    assert game.active.col == ActivePiece.spawn(PieceType.T).col - 1


def test_text_input_event_reaches_name():
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    game.score = 340
    controller = Controller(game)
    app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="Иван"), controller)
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE), controller)
    assert controller.name == "Ива"


def test_longest_table_row_fits_the_panel():
    fonts = render.make_fonts()
    text = "10. ШШШШШШШШШШ 9999999"
    size = render.fitted_size(fonts, layout.ROLE_FONTS["table-row"], text,
                              layout.screen_text_width("table-row"))
    assert size >= layout.MIN_FONT_SIZE
    assert render.role_font(fonts, "table-row", text).size(text)[0] <= layout.screen_text_width(
        "table-row")


def test_game_over_table_renders():
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    game.score = 340
    controller = Controller(game)
    controller.text_input("Ann")
    controller.key_down(Key.RESTART)
    draw_game(game, controller)  # must not raise with a highlighted row


def test_quit_event_stops_loop():
    controller = Controller(Game(seed=1))
    assert not app.handle_event(pygame.event.Event(pygame.QUIT), controller)


# --- Saved sound settings --------------------------------------------------


def test_saved_settings_apply_after_restart(data_dir):
    (data_dir / "settings.json").write_text(
        '{"version": 1, "music_on": false, "sound_on": true, "music_volume": 30}',
        encoding="utf-8",
    )
    controller = app.create_controller()
    assert (controller.music_on, controller.sound_on, controller.music_volume) == (False, True, 30)
    controller.key_down(Key.RESTART)  # New game, so the side panel is shown
    assert "MUSIC OFF" in layout.screen_texts(controller)


def test_settings_change_is_saved(data_dir):
    controller = app.create_controller()
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n), controller)
    saved = json.loads((data_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["sound_on"] is False
    assert app.create_controller().sound_on is False  # the next launch picks it up

# --- Menu, its screens and the help screen ---------------------------------


def post_keys(*keys: int) -> None:
    for key in keys:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))


def press(controller: Controller, *keys: int) -> None:
    for key in keys:
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key), controller)


def controller_on(screen: str, language: str = "en") -> Controller:
    """A controller showing one of the full-window screens."""
    table = HighScores()
    for place in range(10):
        table.add(Entry("Ш" * 10, 9_999_999 - place, 0, 0))
    controller = Controller(Game(rng=ScriptedRng([PieceType.T, PieceType.S])), table,
                            settings=Settings(language=language), start_in_menu=True)
    if screen == "help":
        controller.key_down(Key.RESTART)
        controller.key_down(Key.HELP)
    elif screen != "menu":
        item = {"scores": "High scores", "settings": "Settings", "controls": "Controls"}[screen]
        while menus.MAIN_ITEMS[controller.menu_index] != item:
            controller.key_down(Key.DOWN)
        controller.key_down(Key.RESTART)
    assert layout.full_screen(controller) == screen
    return controller


def test_menu_covers_the_field():
    controller = controller_on("menu")
    surface = draw_game(controller.game, controller)
    assert center_color(surface, layout.cell_rect(4, 19)) == layout.CREAM  # the panel
    assert center_color(surface, layout.cell_rect(4, 2)) != fill(PieceType.T)


def test_main_menu_panel():
    controller = controller_on("menu")
    surface = draw_game(controller.game, controller)
    assert pixel(surface, (480, 60)) == (255, 244, 230)
    assert pixel(surface, (100, 360)) == (232, 86, 42)
    fonts = render.make_fonts()
    (hint,) = [placed_rect(fonts, role, t, p)
               for t, p, role, _ in layout.full_screen_texts(controller) if role == "hint"]
    assert hint.top > 648


UNDER_PANEL = ("hint", "version")


@pytest.mark.parametrize("language", ["en", "ru"])
@pytest.mark.parametrize("screen", ["menu", "scores", "settings", "controls", "help"])
def test_full_screen_texts_fit_the_panel(screen, language):
    controller = controller_on(screen, language)
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    panel = pygame.Rect(layout.SCREEN_PANEL)
    rects = []
    for text, pos, role, _ in layout.full_screen_texts(controller):
        rect = placed_rect(fonts, role, text, pos)
        if role in UNDER_PANEL:
            assert window.contains(rect) and rect.top >= panel.bottom + layout.PANEL_LIFT, text
        else:
            assert panel.contains(rect), text
        if role == "key":  # the key column ends before the action column starts
            assert rect.right < layout.ACTION_COLUMN_X, text
        rects.append(rect)
    for i, rect in enumerate(rects):  # lines do not run into each other
        assert rect.collidelist(rects[i + 1:]) == -1, i
    draw_game(controller.game, controller)  # renders without errors


def test_settings_values_fit_the_button():
    settings = Settings(language="ru", music_on=False, music_volume=100, start_level=19,
                        autorepeat="normal")
    fonts = render.make_fonts()
    for row in menus.SETTING_ROWS:
        text = menus.setting_line(settings, row)
        placed_rect(fonts, "setting", text, (layout.CENTER_X, layout.SETTINGS_ROWS_Y))


def test_selected_menu_item_is_a_dark_button():
    controller = controller_on("menu")
    surface = draw_game(controller.game, controller)
    items = {text: pos for text, pos, role, _ in layout.full_screen_texts(controller)
             if role == "item"}
    assert button_color(surface, "item", items["New game"]) == layout.INK
    assert button_color(surface, "item", items["Quit"]) == layout.CREAM
    fonts = render.make_fonts()
    assert layout.CREAM in colors_in(surface, placed_rect(fonts, "item", "New game",
                                                          items["New game"]))
    assert layout.INK in colors_in(surface, placed_rect(fonts, "item", "Quit", items["Quit"]))


def test_selected_setting_is_a_dark_button():
    controller = controller_on("settings")
    surface = draw_game(controller.game, controller)
    rows = [(text, pos) for text, pos, role, _ in layout.full_screen_texts(controller)
            if role == "setting"]
    assert button_color(surface, "setting", rows[0][1]) == layout.INK
    assert button_color(surface, "setting", rows[1][1]) == layout.CREAM


def test_key_list_draws_keys():
    controller = controller_on("controls")
    surface = draw_game(controller.game, controller)
    x, y = next(pos for text, pos, role, _ in layout.full_screen_texts(controller)
                if role == "key" and text == "Left / Right")
    first_key = (x, y, layout.KEY_H, layout.KEY_H)
    assert {layout.INK, layout.CREAM} <= colors_in(surface, first_key)


def test_pause_menu_renders():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    controller = Controller(game)
    controller.key_down(Key.PAUSE)
    controller.key_down(Key.DOWN)
    draw_game(game, controller)


def test_app_starts_in_the_menu(data_dir):
    controller = app.create_controller()
    assert controller.phase is Phase.MENU
    assert layout.screen_texts(controller)[:2] == ["Tetris Shmetris", "New game"]
    press(controller, pygame.K_RETURN)
    assert controller.phase is Phase.PLAYING


def test_quit_item_ends_main(data_dir):
    post_keys(pygame.K_UP, pygame.K_RETURN)  # the selection goes round to Quit
    start = time.monotonic()
    assert app.main(max_frames=600) == 0  # 600 frames would take ~10 s
    assert time.monotonic() - start < 3


def test_signed_record_is_loaded_by_the_same_installation(data_dir):
    assert app.create_controller().scores.entries == ()  # creates the installation ID
    install_id = (data_dir / "install-id").read_text(encoding="utf-8").strip()
    table = HighScores()
    table.add(Entry("Иван", 1200, 13, 1))
    assert storage.save(table, data_dir / "highscores.json", install_id)
    assert app.create_controller().scores.entries == (Entry("Иван", 1200, 13, 1),)


def test_game_settings_survive_a_restart(data_dir):
    (data_dir / "settings.json").write_text(
        '{"version": 1, "music_on": false, "sound_on": true, "music_volume": 30}',
        encoding="utf-8",
    )
    controller = app.create_controller()
    press(controller, pygame.K_DOWN, pygame.K_DOWN, pygame.K_RETURN)  # Settings
    for _ in range(menus.SETTING_ROWS.index("start_level")):
        press(controller, pygame.K_DOWN)
    press(controller, *[pygame.K_RIGHT] * 5)  # Start level: 5
    press(controller, pygame.K_DOWN, pygame.K_RIGHT)  # Ghost: Off
    again = app.create_controller()
    press(again, pygame.K_DOWN, pygame.K_DOWN, pygame.K_RETURN)
    texts = layout.screen_texts(again)
    assert "Start level: 5" in texts and "Ghost: Off" in texts
    assert "Music: Off" in texts and "Music volume: 30%" in texts


def test_broken_start_level_falls_back(data_dir):
    (data_dir / "settings.json").write_text(
        '{"version": 1, "music_on": false, "start_level": 25, "ghost": false}',
        encoding="utf-8",
    )
    settings = app.create_controller().settings
    assert (settings.start_level, settings.ghost, settings.music_on) == (0, False, False)


def test_effects_volume_is_saved(data_dir):
    controller = app.create_controller()
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_9), controller)
    saved = json.loads((data_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["sfx_volume"] == 90
    assert app.create_controller().settings.sfx_volume == 90


# --- Russian interface -----------------------------------------------------


def test_russian_screens_render():
    for screen in ("menu", "scores", "settings", "controls", "help"):
        controller = controller_on(screen, "ru")
        draw_game(controller.game, controller)


def test_language_survives_a_restart(data_dir):
    controller = app.create_controller()
    press(controller, pygame.K_DOWN, pygame.K_DOWN, pygame.K_RETURN)  # Settings
    press(controller, pygame.K_RIGHT)  # Language: Русский
    again = app.create_controller()
    assert layout.screen_texts(again)[:2] == ["Tetris Shmetris", "Новая игра"]
    screen = app.create_window()
    assert screen.get_size() == (960, 720)
    assert pygame.display.get_caption()[0] == "Tetris Shmetris"


# --- Guide (F2) ---------------------------------------------------------------

GUIDE_LANGUAGES = ("en", "ru")
GUIDE_WIDTH = 560


def guide_controller(language: str, page: int) -> Controller:
    """A game with the guide open on a page (0-based)."""
    controller = Controller(Game(rng=ScriptedRng([PieceType.T, PieceType.S])),
                            settings=Settings(language=language))
    controller.key_down(Key.GUIDE)
    for _ in range(page):
        controller.key_down(Key.RIGHT)
    assert controller.guide_page == page
    return controller


def test_wrap_text_by_words():
    font = render.make_fonts().for_role("paragraph")
    paragraph = guide.paragraphs(0, "ru")[1]
    assert font.size(paragraph)[0] > GUIDE_WIDTH
    lines = render.wrap_text(font, paragraph, GUIDE_WIDTH)
    assert len(lines) > 1
    assert all(font.size(line)[0] <= GUIDE_WIDTH for line in lines)
    assert " ".join(lines) == paragraph


def test_long_word_gets_a_line_of_its_own():
    font = render.make_fonts().for_role("paragraph")
    word = "Ш" * 60
    assert render.wrap_text(font, f"a {word} b", GUIDE_WIDTH) == ["a", word, "b"]


@pytest.mark.parametrize("language", GUIDE_LANGUAGES)
@pytest.mark.parametrize("page", range(guide.PAGE_COUNT))
def test_guide_page_fits(language, page):
    controller = guide_controller(language, page)
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    panel = pygame.Rect(layout.SCREEN_PANEL)
    texts = layout.full_screen_texts(controller)
    title, number, hint = (placed_rect(fonts, role, text, pos)
                           for text, pos, role, _ in texts if role != "paragraph")
    assert panel.contains(title) and panel.contains(number)
    assert window.contains(hint) and hint.top >= panel.bottom
    paragraphs = [text for text, _, role, _ in texts if role == "paragraph"]
    origin = next(pos for _, pos, role, _ in texts if role == "paragraph")
    font = fonts.for_role("paragraph")
    bottom = title.bottom
    for line, pos in render.guide_lines(fonts, paragraphs, origin):
        rect = pygame.Rect(pos, font.size(line))
        assert rect.left == 200 and rect.width <= GUIDE_WIDTH, line
        assert rect.top >= bottom, line  # below the title and the line before it
        bottom = rect.bottom
    assert bottom <= number.top  # the last line is above the page number


@pytest.mark.parametrize("language", GUIDE_LANGUAGES)
def test_guide_pages_render(language):
    for page in range(guide.PAGE_COUNT):
        controller = guide_controller(language, page)
        surface = draw_game(controller.game, controller)
        # Neither the well nor the cards are drawn: the window shows the guide's panel.
        assert pixel(surface, (100, 300)) == layout.WINDOW_BG
        assert pixel(surface, (345, 600)) == layout.CREAM


# --- Game version in the main menu ---------------------------------------------


def test_version_label_in_the_menu():
    controller = controller_on("menu")
    fonts = render.make_fonts()
    texts = layout.full_screen_texts(controller)
    ((text, pos, _, _),) = [entry for entry in texts if entry[2] == "version"]
    rect = placed_rect(fonts, "version", text, pos)
    assert pygame.Rect((0, 0), layout.WINDOW_SIZE).contains(rect)
    assert rect.right <= 944 and rect.bottom <= 708
    assert rect.left > 808 and rect.top > 648  # clear of the panel and its shadow
    hint = next(placed_rect(fonts, role, t, p) for t, p, role, _ in texts if role == "hint")
    assert not rect.colliderect(hint)
    surface = draw_game(controller.game, controller)
    assert (255, 197, 158) in colors_in(surface, rect)


# --- Sound check screen --------------------------------------------------------


def check_with(index: int, marked: bool = False) -> SoundCheck:
    """A sound check with item `index` selected and, if `marked`, every item marked."""
    check = SoundCheck()
    for _ in range(index):
        check.key_down(CheckKey.DOWN)
    if marked:
        check.marked = [True] * len(ITEMS)
    return check


def check_rects(fonts, check: SoundCheck, language: str, has_audio: bool):
    """(text, role, rect) of every sound check text at its fitted size and place."""
    return [(text, role, placed_rect(fonts, role, text, pos))
            for text, pos, role, _ in layout.sound_check_texts(check, language, has_audio)]


@pytest.mark.parametrize("has_audio", [True, False])
@pytest.mark.parametrize("language", ["en", "ru"])
def test_sound_check_texts_fit_the_panel(language, has_audio):
    fonts = render.make_fonts()
    panel = pygame.Rect(layout.SCREEN_PANEL)
    for index in range(len(ITEMS)):
        placed = check_rects(fonts, check_with(index, marked=True), language, has_audio)
        rects = [rect for _, _, rect in placed]
        for text, role, rect in placed:
            assert panel.contains(rect), text
            if role == "row":  # rows end before the column of marks starts
                assert rect.right < layout.CHECK_MARK_X, text
        for i, rect in enumerate(rects):  # lines do not run into each other
            assert rect.collidelist(rects[i + 1:]) == -1, placed[i][0]


@pytest.mark.parametrize("language", ["en", "ru"])
def test_sound_check_texts_keep_their_size(language):
    fonts = render.make_fonts()
    for text, pos, role, _ in layout.sound_check_texts(check_with(8, True), language, True):
        spec = layout.ROLE_FONTS[role]
        size = render.fitted_size(fonts, spec, text, layout.screen_text_width(role))
        assert size == spec.size, text  # nothing had to shrink


@pytest.mark.parametrize("language", ["en", "ru"])
def test_every_sound_check_character_is_in_the_font(language):
    fonts = render.make_fonts()
    entries = []
    for index in range(len(ITEMS)):
        for has_audio in (True, False):
            texts = layout.sound_check_texts(check_with(index, True), language, has_audio)
            entries += [(text, role) for text, _, role, _ in texts]
    assert missing_chars(fonts, entries) == []


def test_selected_sound_check_row_is_a_dark_button():
    check = check_with(4)  # item 5
    surface = pygame.Surface(layout.WINDOW_SIZE)
    render.draw_sound_check(surface, check, "en", True, render.make_fonts())
    rows = [pos for _, pos, role, _ in layout.sound_check_texts(check, "en", True)
            if role == "row"]
    for i, pos in enumerate(rows):
        assert (button_color(surface, "row", pos) == layout.INK) == (i == 4), i


@pytest.mark.parametrize("language", ["en", "ru"])
def test_sound_check_screen_renders(language):
    surface = pygame.Surface(layout.WINDOW_SIZE)
    check = check_with(12, marked=True)
    render.draw_sound_check(surface, check, language, False, render.make_fonts())
    mark = next(rect for _, role, rect in check_rects(render.make_fonts(), check, language, False)
                if role == "mark")
    assert layout.MARK_COLOR in colors_in(surface, mark)
    assert pixel(surface, (5, 5)) == layout.WINDOW_BG


# --- Sound check mode ----------------------------------------------------------

MIXER_STEP = 1 / 128  # SDL keeps volumes in 128 steps


def report_items(data_dir) -> list[dict]:
    data = json.loads((data_dir / "sound-check.json").read_text(encoding="utf-8"))
    assert data["version"] == 1
    return data["items"]


@pytest.fixture
def seen_checks(monkeypatch):
    """(check, language, has_audio) of every frame run_sound_check draws."""
    frames = []
    draw = render.draw_sound_check

    def recording_draw(surface, check, language, has_audio, fonts):
        frames.append((check, language, has_audio))
        draw(surface, check, language, has_audio, fonts)

    monkeypatch.setattr(render, "draw_sound_check", recording_draw)
    return frames


def shown_texts(frame) -> list[str]:
    check, language, has_audio = frame
    return [text for text, _, _, _ in layout.sound_check_texts(check, language, has_audio)]


@pytest.mark.parametrize(
    ("pygame_key", "key"),
    [
        (pygame.K_UP, CheckKey.UP),
        (pygame.K_DOWN, CheckKey.DOWN),
        (pygame.K_SPACE, CheckKey.PLAY),
        (pygame.K_RETURN, CheckKey.PLAY),
        (pygame.K_KP_ENTER, CheckKey.PLAY),
        (pygame.K_x, CheckKey.MARK),
        (pygame.K_ESCAPE, CheckKey.EXIT),
    ],
)
def test_sound_check_key_map(pygame_key, key):
    assert app.SOUND_CHECK_KEYS[pygame_key] is key


def test_sound_check_key_map_has_no_other_keys():
    assert len(app.SOUND_CHECK_KEYS) == 7
    for other in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_m, pygame.K_n, pygame.K_9,
                  pygame.K_0, pygame.K_MINUS, pygame.K_EQUALS, pygame.K_p, pygame.K_F1,
                  pygame.K_F2):
        assert other not in app.SOUND_CHECK_KEYS


def test_sound_check_runs_frames(data_dir, seen_checks):
    assert app.run_sound_check(max_frames=3) == 0
    assert len(seen_checks) == 3
    assert [i["played"] for i in report_items(data_dir)] == [True] + [False] * 12
    assert sorted(path.name for path in data_dir.iterdir()) == ["sound-check.json"]


def test_held_keys_do_not_repeat_in_the_sound_check(data_dir, monkeypatch):
    repeats = []
    draw = render.draw_sound_check

    def checking_draw(*args):
        repeats.append(pygame.key.get_repeat())
        draw(*args)

    monkeypatch.setattr(render, "draw_sound_check", checking_draw)
    assert app.run_sound_check(max_frames=2) == 0
    assert repeats == [(0, 0), (0, 0)]  # a held key gives one KEYDOWN


def test_game_keys_do_nothing_in_the_sound_check(data_dir, seen_checks):
    post_keys(pygame.K_m, pygame.K_n, pygame.K_9, pygame.K_F2, pygame.K_LEFT, pygame.K_RIGHT)
    assert app.run_sound_check(max_frames=3) == 0
    check = seen_checks[-1][0]
    assert check.index == 0 and not any(check.marked)
    assert shown_texts(seen_checks[-1])[0] == "Sound check"  # no guide, no menu
    assert not (data_dir / "settings.json").exists()


def test_mark_then_escape_ends_the_sound_check(data_dir):
    post_keys(pygame.K_x, pygame.K_ESCAPE)
    start = time.monotonic()
    assert app.run_sound_check(max_frames=600) == 0  # 600 frames would take ~10 s
    assert time.monotonic() - start < 3
    first = report_items(data_dir)[0]
    assert (first["id"], first["unpleasant"]) == ("move", True)
    assert not (data_dir / "settings.json").exists()


def test_mark_is_in_the_report_while_the_check_runs(data_dir, monkeypatch):
    in_file = []
    draw = render.draw_sound_check

    def reading_draw(*args):
        in_file.append(report_items(data_dir)[3])
        draw(*args)

    monkeypatch.setattr(render, "draw_sound_check", reading_draw)
    post_keys(pygame.K_DOWN, pygame.K_DOWN, pygame.K_DOWN, pygame.K_x)
    assert app.run_sound_check(max_frames=1) == 0
    assert (in_file[0]["id"], in_file[0]["unpleasant"]) == ("lock", True)


def test_closing_the_window_ends_the_sound_check(data_dir):
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    start = time.monotonic()
    assert app.run_sound_check(max_frames=600) == 0
    assert time.monotonic() - start < 3


def test_sound_check_ignores_the_saved_sound_settings(data_dir, monkeypatch):
    settings_file = data_dir / "settings.json"
    settings_file.write_text(json.dumps(
        {"version": 1, "sound_on": False, "sfx_volume": 30, "music_volume": 100}),
        encoding="utf-8")
    saved = settings_file.read_text(encoding="utf-8")
    heard = []
    play_check = Audio.play_check

    def recording_play_check(self, playback):
        play_check(self, playback)
        for cue in playback.cues:
            sound = self._channel if cue == MUSIC else self._effects[Sound(cue)]
            heard.append((cue, sound.get_volume()))

    draw = render.draw_sound_check

    def stepping_draw(surface, check, language, has_audio, fonts):
        draw(surface, check, language, has_audio, fonts)
        if check.index == 0:
            post_keys(*[pygame.K_DOWN] * 12)  # on to the music
        else:
            post_keys(pygame.K_ESCAPE)

    monkeypatch.setattr(Audio, "play_check", recording_play_check)
    monkeypatch.setattr(render, "draw_sound_check", stepping_draw)
    assert app.run_sound_check(max_frames=100) == 0
    assert [cue for cue, _ in heard] == ["move", MUSIC]
    assert heard[0][1] == pytest.approx(1.0, abs=MIXER_STEP)
    assert heard[1][1] == pytest.approx(0.5, abs=MIXER_STEP)
    assert settings_file.read_text(encoding="utf-8") == saved


def test_sound_check_speaks_the_saved_language(data_dir, seen_checks):
    (data_dir / "settings.json").write_text('{"version": 1, "language": "ru"}', encoding="utf-8")
    assert app.run_sound_check(max_frames=1) == 0
    assert shown_texts(seen_checks[0])[0] == "Проверка звуков"


def test_sound_check_without_a_sound_device(data_dir, monkeypatch, seen_checks):
    def broken_init(*args, **kwargs):
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "init", broken_init)
    post_keys(pygame.K_x)
    assert app.run_sound_check(max_frames=3) == 0
    assert seen_checks[-1][2] is False
    assert "No sound device" in shown_texts(seen_checks[-1])
    items = report_items(data_dir)
    assert not any(i["played"] for i in items)
    assert items[0]["unpleasant"] is True


def test_sound_check_goes_on_when_the_report_cannot_be_written(monkeypatch, tmp_path,
                                                               seen_checks):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("TETRIS_DATA_DIR", str(blocker / "data"))  # a folder inside a file
    post_keys(pygame.K_x)
    assert app.run_sound_check(max_frames=3) == 0
    assert len(seen_checks) == 3
    assert "unpleasant" in shown_texts(seen_checks[-1])


def test_a_new_sound_check_starts_a_new_report(data_dir):
    old = {"version": 1, "items": [{"number": 4, "id": "lock", "played": True,
                                    "unpleasant": True}]}
    (data_dir / "sound-check.json").write_text(json.dumps(old), encoding="utf-8")
    assert app.run_sound_check(max_frames=1) == 0
    items = report_items(data_dir)
    assert len(items) == 13
    assert not any(i["unpleasant"] for i in items)
