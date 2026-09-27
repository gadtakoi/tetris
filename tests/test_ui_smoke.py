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
from tetris.pieces import PieceType  # noqa: E402
from tetris_ui import app, layout, render  # noqa: E402
from tetris_ui.input import Controller, Key, Phase  # noqa: E402
from tetris_ui.settings import Settings  # noqa: E402

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
    assert pygame.display.get_caption()[0] == "SEVA Tetris"


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
        (pygame.K_UP, Key.ROTATE_CW),
        (pygame.K_x, Key.ROTATE_CW),
        (pygame.K_z, Key.ROTATE_CCW),
        (pygame.K_LCTRL, Key.ROTATE_CCW),
        (pygame.K_p, Key.PAUSE),
        (pygame.K_ESCAPE, Key.PAUSE),
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
    controller.key_down(Key.RESTART)  # leave the splash so the side panel is shown
    assert "MUSIC OFF" in layout.screen_texts(controller)


def test_settings_change_is_saved(data_dir):
    controller = app.create_controller()
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n), controller)
    saved = json.loads((data_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["sound_on"] is False
    assert app.create_controller().sound_on is False  # the next launch picks it up


# --- Splash and help screens -----------------------------------------------


def test_splash_covers_the_field():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    controller = Controller(game, splash=True)
    surface = draw_game(game, controller)
    assert center_color(surface, layout.cell_rect(4, 21)) == layout.WINDOW_BG
    assert center_color(surface, layout.cell_rect(4, 2)) != layout.PIECE_COLORS[PieceType.T]


@pytest.mark.parametrize("screen", ["splash", "help"])
def test_key_screen_texts_fit_the_window(screen):
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    controller = Controller(game, splash=screen == "splash")
    if screen == "help":
        controller.key_down(Key.HELP)
    fonts = render.make_fonts()
    window = pygame.Rect((0, 0), layout.WINDOW_SIZE)
    for text, pos, role in layout.key_screen_texts(controller):
        font = fonts.big if role == "title" else fonts.small
        rect = pygame.Rect((0, 0), font.size(text))
        if role in ("title", "hint"):
            rect.center = pos
        else:
            rect.topleft = pos
        assert window.contains(rect), text
    draw_game(game, controller)  # renders without errors


def test_key_columns_do_not_overlap():
    fonts = render.make_fonts()
    widest_key = max(fonts.small.size(keys)[0] for keys, _ in layout.HOTKEYS)
    assert layout.KEY_COLUMN_X + widest_key < layout.ACTION_COLUMN_X


def test_app_starts_on_the_splash(data_dir):
    controller = app.create_controller()
    assert controller.phase is Phase.SPLASH
    assert layout.screen_texts(controller)[0] == "SEVA Tetris"


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
