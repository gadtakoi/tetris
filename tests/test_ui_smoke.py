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
from tetris_ui import app, guide, layout, menus, render  # noqa: E402
from tetris_ui.audio import Audio  # noqa: E402
from tetris_ui.input import Controller, Key, Phase, Sound  # noqa: E402
from tetris_ui.settings import Settings  # noqa: E402
from tetris_ui.soundcheck import ITEMS, MUSIC, CheckKey, SoundCheck  # noqa: E402

VISIBLE_CELLS = [(c, r) for r in range(HIDDEN_ROWS, HEIGHT) for c in range(WIDTH)]


@pytest.fixture(autouse=True)
def pygame_session():
    pygame.init()
    yield
    pygame.quit()


def draw_game(game: Game, controller: Controller | None = None) -> pygame.Surface:
    surface = pygame.Surface(layout.WINDOW_SIZE)
    render.draw(surface, controller or Controller(game), render.make_fonts())
    return surface


def center_color(surface: pygame.Surface, rect) -> tuple[int, int, int]:
    x, y, w, h = rect
    return tuple(surface.get_at((x + w // 2, y + h // 2)))[:3]


def game_with_hidden_active_piece() -> Game:
    """Game whose active piece sits entirely in the hidden rows, so it is not drawn."""
    game = Game(rng=ScriptedRng([PieceType.I, PieceType.T]))
    game.active = ActivePiece(PieceType.I, 0, 3, -1)  # cells in row 0
    return game


def assert_only_ghost_on_field(surface: pygame.Surface, game: Game) -> None:
    """Every visible cell shows the field background, except the active piece's ghost."""
    ghost = set(game.ghost_cells())
    assert ghost  # the hidden piece still casts a shadow onto the floor
    for cell in VISIBLE_CELLS:
        expected = layout.ghost_color(game.active.type) if cell in ghost else layout.FIELD_BG
        assert center_color(surface, layout.cell_rect(*cell)) == expected


# --- Rendering -------------------------------------------------------------


def test_empty_field():
    game = game_with_hidden_active_piece()
    assert_only_ghost_on_field(draw_game(game), game)


def test_locked_cell_color():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 21)], PieceType.Z)
    surface = draw_game(game)
    assert tuple(surface.get_at((35, 605)))[:3] == layout.PIECE_COLORS[PieceType.Z]


def test_hidden_rows_are_not_drawn():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 1)], PieceType.S)
    assert_only_ghost_on_field(draw_game(game), game)


def test_active_piece_color():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game)
    for cell in game.active.cells():
        assert center_color(surface, layout.cell_rect(*cell)) == (160, 0, 240)


def preview_colors(surface, x: int, y: int) -> list[list[tuple[int, int, int]]]:
    """Center colors of the 4 x 2 cells of a preview box."""
    return [
        [center_color(surface, (x + c * layout.CELL, y + r * layout.CELL, layout.CELL, layout.CELL))
         for c in range(layout.PREVIEW_CELLS)]
        for r in range(layout.PREVIEW_ROWS)
    ]


def test_next_piece_preview():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.I]))
    surface = draw_game(game)
    cyan = layout.PIECE_COLORS[PieceType.I]
    rows = preview_colors(surface, layout.PREVIEW_X, layout.PREVIEW_Y)
    assert rows[1] == [cyan] * 4  # I in orientation 0 fills box row 1 only
    assert cyan not in rows[0]


def t_shape(color) -> list[list]:
    return [[None, color, None, None], [color, color, color, None]]


def mask(rows, color) -> list[list]:
    return [[cell if cell == color else None for cell in row] for row in rows]


def test_held_piece_on_the_panel():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S, PieceType.Z]))
    game.hold()
    game.hard_drop()  # hold is allowed again
    purple = layout.PIECE_COLORS[PieceType.T]
    rows = preview_colors(draw_game(game), layout.HOLD_X, layout.HOLD_Y)
    assert mask(rows, purple) == t_shape(purple)


def test_held_piece_is_dimmed_while_hold_is_used():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S, PieceType.Z]))
    game.hold()
    assert layout.dimmed_color(PieceType.T) == (80, 0, 120)
    rows = preview_colors(draw_game(game), layout.HOLD_X, layout.HOLD_Y)
    assert mask(rows, (80, 0, 120)) == t_shape((80, 0, 120))


def test_empty_hold_slot():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    rows = preview_colors(draw_game(game), layout.HOLD_X, layout.HOLD_Y)
    piece_colors = set(layout.PIECE_COLORS.values())
    assert not any(color in piece_colors for row in rows for color in row)
    assert "HOLD" in layout.screen_texts(Controller(game))


def test_panel_layout_fits():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    controller = Controller(game)
    fonts = render.make_fonts()
    texts = dict(layout.panel_texts(controller))
    next_box = pygame.Rect(layout.PREVIEW_X, layout.PREVIEW_Y, 4 * layout.CELL, 2 * layout.CELL)
    hold_box = pygame.Rect(layout.HOLD_X, layout.HOLD_Y, 4 * layout.CELL, 2 * layout.CELL)
    assert not next_box.colliderect(hold_box)
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    for text, (x, y) in layout.panel_texts(controller):
        rect = pygame.Rect((x, y), fonts.small.size(text))
        assert window.contains(rect), text
        assert not rect.colliderect(next_box) and not rect.colliderect(hold_box), text
    for label in ("SCORE", "LINES", "LEVEL"):
        value_bottom = texts[label][1] + layout.VALUE_OFFSET_Y + fonts.small.get_height()
        assert value_bottom <= 460


def test_ghost_of_t_piece():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game)
    assert layout.ghost_color(PieceType.T) == (20, 0, 30)
    for cell in [(4, 20), (3, 21), (4, 21), (5, 21)]:
        assert center_color(surface, layout.cell_rect(*cell)) == (20, 0, 30)


def test_grid_shows_through_the_ghost():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game)
    assert layout.cell_rect(4, 20)[:2] == (140, 560)
    for pixel in [(140, 575), (155, 560)]:  # left and top edges of ghost cell (4, 20)
        assert tuple(surface.get_at(pixel))[:3] == layout.GRID


def test_piece_on_floor_covers_its_ghost():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    for _ in range(18):
        game.step_down()
    surface = draw_game(game)
    for cell in game.active.cells():
        assert center_color(surface, layout.cell_rect(*cell)) == (160, 0, 240)


def test_ghost_switched_off():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game, Controller(game, settings=Settings(ghost=False)))
    for cell in [(4, 20), (3, 21), (4, 21), (5, 21)]:
        assert center_color(surface, layout.cell_rect(*cell)) == layout.FIELD_BG


def test_no_ghost_after_game_over():
    game = Game(rng=ScriptedRng([PieceType.O]))
    while not game.is_over:
        game.hard_drop()
    surface = draw_game(game)
    ghost_colors = {layout.ghost_color(t) for t in PieceType}
    for cell in VISIBLE_CELLS:
        assert center_color(surface, layout.cell_rect(*cell)) not in ghost_colors


def test_game_over_hides_active_piece_and_shades_field():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    active_cells = game.active.cells()
    game.is_over = True
    surface = draw_game(game)
    for cell in active_cells:
        color = center_color(surface, layout.cell_rect(*cell))
        assert color != layout.PIECE_COLORS[PieceType.T]


def test_pause_keeps_board_visible_under_shade():
    game = game_with_hidden_active_piece()
    game.board.place([(0, 21)], PieceType.Z)
    controller = Controller(game)
    controller.key_down(Key.PAUSE)
    surface = draw_game(game, controller)
    r, g, b = tuple(surface.get_at((35, 605)))[:3]
    assert r > 0 and (r, g, b) != layout.PIECE_COLORS[PieceType.Z]  # darkened, not hidden


# --- Window and events -----------------------------------------------------


def test_window_size_and_title():
    screen = app.create_window()
    assert screen.get_size() == (520, 640)
    assert pygame.display.get_caption()[0] == "Tetris Shmetris"


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


def test_longest_table_row_fits_the_field():
    width = render.make_fonts().table.size("10. ШШШШШШШШШШ 9999999")[0]
    assert width < layout.FIELD_W


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
    assert center_color(surface, layout.cell_rect(4, 21)) == layout.WINDOW_BG
    assert center_color(surface, layout.cell_rect(4, 2)) != layout.PIECE_COLORS[PieceType.T]


@pytest.mark.parametrize("language", ["en", "ru"])
@pytest.mark.parametrize("screen", ["menu", "scores", "settings", "controls", "help"])
def test_full_screen_texts_fit_the_window(screen, language):
    controller = controller_on(screen, language)
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    rects = []
    for text, pos, role, _ in layout.full_screen_texts(controller):
        width = layout.screen_text_width(role)
        size = render.fitted_size(fonts, render.screen_font_size(role), text, width)
        assert size >= layout.MIN_FONT_SIZE, text
        rect = pygame.Rect((0, 0), fonts.sized(size).size(text))
        assert rect.width <= width, text
        if role in ("key", "action"):
            rect.topleft = pos
        elif role == "version":
            rect.bottomright = pos
        else:
            rect.center = pos
        assert window.contains(rect), text
        if role == "key":  # the key column ends before the action column starts
            assert rect.right < layout.ACTION_COLUMN_X, text
        rects.append(rect)
    for i, rect in enumerate(rects):  # lines do not run into each other
        assert rect.collidelist(rects[i + 1:]) == -1, i
    draw_game(controller.game, controller)  # renders without errors


def test_settings_values_fit_the_window():
    settings = Settings(language="ru", music_on=False, music_volume=100, start_level=19,
                        autorepeat="normal")
    fonts = render.make_fonts()
    for row in menus.SETTING_ROWS:
        assert fonts.small.size(menus.setting_line(settings, row))[0] < layout.WINDOW_SIZE[0]


def test_selected_menu_item_is_highlighted():
    controller = controller_on("menu")
    controller.key_down(Key.DOWN)
    surface = draw_game(controller.game, controller)
    colors = {tuple(surface.get_at((x, y)))[:3]
              for x in range(160, 360) for y in range(layout.MENU_ITEMS_Y + 40,
                                                        layout.MENU_ITEMS_Y + 60)}
    assert layout.HIGHLIGHT in colors  # "High scores", the second item


def test_key_columns_do_not_overlap():
    fonts = render.make_fonts()
    widest_key = max(fonts.small.size(keys)[0] for keys, _ in layout.HOTKEYS)
    assert layout.KEY_COLUMN_X + widest_key < layout.ACTION_COLUMN_X


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


def test_sound_indicators_fit_the_window():
    controller = Controller(Game(seed=1), settings=Settings(music_on=False, sound_on=False,
                                                           music_volume=100, sfx_volume=100))
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    for text, (x, y) in layout.panel_texts(controller):
        assert window.contains(pygame.Rect((x, y), fonts.small.size(text))), text


# --- Russian interface -----------------------------------------------------


def fitted_rect(fonts, base_size: int, text: str, width: int) -> pygame.Rect:
    size = render.fitted_size(fonts, base_size, text, width)
    assert size >= layout.MIN_FONT_SIZE, text
    return pygame.Rect((0, 0), fonts.sized(size).size(text))


def test_long_title_fits_the_field():
    fonts = render.make_fonts()
    assert fonts.big.size("ИГРА ОКОНЧЕНА")[0] > layout.FIELD_W  # needs a smaller size
    rect = fitted_rect(fonts, render.BIG_FONT_SIZE, "ИГРА ОКОНЧЕНА", layout.FIELD_W)
    assert rect.width <= layout.FIELD_W


def test_english_texts_keep_their_size():
    fonts = render.make_fonts()
    for text in ("GAME OVER", "PAUSE", "HIGH SCORES"):
        assert render.fitted_size(fonts, render.BIG_FONT_SIZE, text, layout.FIELD_W) == 56
    assert render.fitted_size(fonts, 32, "SOUND 100%", layout.PANEL_W) == 32


def test_fitted_size_stops_at_the_minimum():
    fonts = render.make_fonts()
    assert render.fitted_size(fonts, 32, "Ш" * 100, 50) == layout.MIN_FONT_SIZE


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
def test_overlay_and_panel_texts_fit(language):
    fonts = render.make_fonts()
    for controller in overlay_controllers(language):
        lines = layout.overlay_lines(controller)
        assert lines
        (title, _), rest = lines[0], lines[1:]
        assert fitted_rect(fonts, render.BIG_FONT_SIZE, title, layout.FIELD_W).width <= layout.FIELD_W
        for text, _ in rest:
            rect = fitted_rect(fonts, render.TABLE_FONT_SIZE, text, layout.FIELD_W)
            assert rect.width <= layout.FIELD_W, text
        draw_game(controller.game, controller)  # renders without errors
    settings = Settings(language=language, music_on=False, sound_on=False, music_volume=100)
    panel = Controller(Game(seed=1), settings=settings)
    panel.game.score = 9_999_999
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    for text, (x, y) in layout.panel_texts(panel):
        rect = fitted_rect(fonts, render.SMALL_FONT_SIZE, text, layout.PANEL_W)
        rect.topleft = (x, y)
        assert rect.width <= layout.PANEL_W and window.contains(rect), text


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
    assert screen.get_size() == (520, 640)
    assert pygame.display.get_caption()[0] == "Tetris Shmetris"


# --- Guide (F2) ---------------------------------------------------------------

GUIDE_LANGUAGES = ("en", "ru")


def guide_controller(language: str, page: int) -> Controller:
    """A game with the guide open on a page (0-based)."""
    controller = Controller(Game(rng=ScriptedRng([PieceType.T, PieceType.S])),
                            settings=Settings(language=language))
    controller.key_down(Key.GUIDE)
    for _ in range(page):
        controller.key_down(Key.RIGHT)
    assert controller.guide_page == page
    return controller


def centered_rect(fonts, role: str, text: str, pos) -> pygame.Rect:
    base = render.screen_font_size(role)
    rect = fitted_rect(fonts, base, text, layout.screen_text_width(role))
    rect.center = pos
    return rect


def glyph(font, char: str):
    image = font.render(char, True, (255, 255, 255), (0, 0, 0))
    return image.get_size(), pygame.image.tobytes(image, "RGB")


def test_wrap_text_by_words():
    font = render.make_fonts().sized(render.GUIDE_FONT_SIZE)
    paragraph = guide.paragraphs(0, "ru")[1]
    assert font.size(paragraph)[0] > 480
    lines = render.wrap_text(font, paragraph, 480)
    assert len(lines) > 1
    assert all(font.size(line)[0] <= 480 for line in lines)
    assert " ".join(lines) == paragraph


def test_long_word_gets_a_line_of_its_own():
    font = render.make_fonts().sized(render.GUIDE_FONT_SIZE)
    word = "Ш" * 60
    assert render.wrap_text(font, f"a {word} b", 480) == ["a", word, "b"]


@pytest.mark.parametrize("language", GUIDE_LANGUAGES)
@pytest.mark.parametrize("page", range(guide.PAGE_COUNT))
def test_guide_page_fits(language, page):
    controller = guide_controller(language, page)
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    texts = layout.full_screen_texts(controller)
    title, number, hint = (centered_rect(fonts, role, text, pos)
                           for text, pos, role, _ in texts if role != "paragraph")
    for rect in (title, number, hint):
        assert window.contains(rect)
    assert number.bottom <= hint.top
    paragraphs = [text for text, _, role, _ in texts if role == "paragraph"]
    origin = next(pos for _, pos, role, _ in texts if role == "paragraph")
    font = fonts.sized(render.GUIDE_FONT_SIZE)
    bottom = title.bottom
    for line, pos in render.guide_lines(fonts, paragraphs, origin):
        rect = pygame.Rect(pos, font.size(line))
        assert rect.left == 20 and rect.width <= 480, line
        assert rect.top >= bottom, line  # below the title and the line before it
        bottom = rect.bottom
    assert bottom <= number.top  # the last line is above the page number


@pytest.mark.parametrize("language", GUIDE_LANGUAGES)
def test_guide_pages_render(language):
    for page in range(guide.PAGE_COUNT):
        controller = guide_controller(language, page)
        surface = draw_game(controller.game, controller)
        # Neither the field border (x = 18) nor its top-left cell is drawn; no text is there.
        assert tuple(surface.get_at((18, 300)))[:3] == layout.WINDOW_BG
        assert tuple(surface.get_at((35, 35)))[:3] == layout.WINDOW_BG


@pytest.mark.parametrize("language", GUIDE_LANGUAGES)
def test_every_character_is_in_the_font(language):
    font = render.make_fonts().sized(render.GUIDE_FONT_SIZE)
    missing = glyph(font, "")  # private use area: not in the font
    assert glyph(font, "←") == missing  # the check does see a missing glyph
    controller = Controller(Game(seed=1), settings=Settings(language=language))
    chars = set("".join(layout.all_screen_texts(controller))) - {" "}
    assert [char for char in sorted(chars) if glyph(font, char) == missing] == []


# --- Game version in the main menu ---------------------------------------------


def test_version_label_in_the_menu():
    controller = controller_on("menu")
    fonts = render.make_fonts()
    texts = layout.full_screen_texts(controller)
    ((text, pos, _, _),) = [entry for entry in texts if entry[2] == "version"]
    rect = fitted_rect(fonts, render.screen_font_size("version"), text,
                       layout.screen_text_width("version"))
    rect.bottomright = pos
    assert pygame.Rect((0, 0), layout.WINDOW_SIZE).contains(rect)
    assert rect.left > 260
    hint = next(centered_rect(fonts, role, t, p) for t, p, role, _ in texts if role == "hint")
    assert rect.top >= hint.bottom  # below the hint
    items = [centered_rect(fonts, role, t, p) for t, p, role, _ in texts if role == "item"]
    assert rect.collidelist(items) == -1
    surface = draw_game(controller.game, controller)
    colors = {tuple(surface.get_at((x, y)))[:3]
              for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom)}
    assert layout.VERSION_COLOR in colors  # drawn, in its muted color


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
    placed = []
    for text, pos, role, _ in layout.sound_check_texts(check, language, has_audio):
        rect = fitted_rect(fonts, render.screen_font_size(role), text,
                           layout.screen_text_width(role))
        if role in layout.TOP_LEFT_ROLES:
            rect.topleft = pos
        else:
            rect.center = pos
        placed.append((text, role, rect))
    return placed


@pytest.mark.parametrize("has_audio", [True, False])
@pytest.mark.parametrize("language", ["en", "ru"])
def test_sound_check_texts_fit_the_window(language, has_audio):
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    for index in range(len(ITEMS)):
        placed = check_rects(fonts, check_with(index, marked=True), language, has_audio)
        rects = [rect for _, _, rect in placed]
        for text, role, rect in placed:
            assert window.contains(rect), text
            assert rect.width <= layout.screen_text_width(role), text
            if role == "row":  # rows end before the column of marks starts
                assert rect.right < layout.CHECK_MARK_X, text
        for i, rect in enumerate(rects):  # lines do not run into each other
            assert rect.collidelist(rects[i + 1:]) == -1, placed[i][0]


@pytest.mark.parametrize("language", ["en", "ru"])
def test_sound_check_texts_keep_their_size(language):
    fonts = render.make_fonts()
    for text, pos, role, _ in layout.sound_check_texts(check_with(8, True), language, True):
        size = render.fitted_size(fonts, render.screen_font_size(role), text,
                                  layout.screen_text_width(role))
        assert size == render.screen_font_size(role), text  # nothing had to shrink


@pytest.mark.parametrize("language", ["en", "ru"])
def test_every_sound_check_character_is_in_the_font(language):
    fonts = render.make_fonts()
    chars: set[str] = set()
    for index in range(len(ITEMS)):
        for has_audio in (True, False):
            texts = layout.sound_check_texts(check_with(index, True), language, has_audio)
            chars |= set("".join(text for text, _, _, _ in texts))
    for size in {render.CHECK_FONT_SIZE, render.SMALL_FONT_SIZE, render.BIG_FONT_SIZE}:
        font = fonts.sized(size)
        missing = glyph(font, "")  # private use area: not in the font
        assert glyph(font, "←") == missing  # the check does see a missing glyph
        assert [char for char in sorted(chars - {" "}) if glyph(font, char) == missing] == []


def test_selected_sound_check_row_is_highlighted():
    check = check_with(4)  # item 5
    surface = pygame.Surface(layout.WINDOW_SIZE)
    render.draw_sound_check(surface, check, "en", True, render.make_fonts())
    placed = check_rects(render.make_fonts(), check, "en", True)
    rows = [rect for _, role, rect in placed if role == "row"]
    for i, rect in enumerate(rows):
        colors = {tuple(surface.get_at((x, y)))[:3]
                  for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom)}
        assert (layout.HIGHLIGHT in colors) == (i == 4), i
    assert layout.HIGHLIGHT == (240, 240, 0)  # the color of a selected menu item


@pytest.mark.parametrize("language", ["en", "ru"])
def test_sound_check_screen_renders(language):
    surface = pygame.Surface(layout.WINDOW_SIZE)
    check = check_with(12, marked=True)
    render.draw_sound_check(surface, check, language, False, render.make_fonts())
    mark = next(rect for _, role, rect in check_rects(render.make_fonts(), check, language, False)
                if role == "mark")
    colors = {tuple(surface.get_at((x, y)))[:3]
              for x in range(mark.left, mark.right) for y in range(mark.top, mark.bottom)}
    assert layout.MARK_COLOR in colors
    assert tuple(surface.get_at((5, 5)))[:3] == layout.WINDOW_BG


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
