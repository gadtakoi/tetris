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
from tetris_ui.input import Controller, Key  # noqa: E402

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


def test_next_piece_preview():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.I]))
    surface = draw_game(game)
    cyan = layout.PIECE_COLORS[PieceType.I]
    for row in range(layout.PREVIEW_CELLS):
        colors = [
            center_color(
                surface,
                (layout.PREVIEW_X + col * layout.CELL, layout.PREVIEW_Y + row * layout.CELL,
                 layout.CELL, layout.CELL),
            )
            for col in range(layout.PREVIEW_CELLS)
        ]
        # I in orientation 0 fills box row 1 only.
        assert (colors == [cyan] * 4) == (row == 1)


def test_ghost_of_t_piece():
    game = Game(rng=ScriptedRng([PieceType.T, PieceType.S]))
    surface = draw_game(game)
    assert layout.ghost_color(PieceType.T) == (40, 0, 60)
    for cell in [(4, 20), (3, 21), (4, 21), (5, 21)]:
        assert center_color(surface, layout.cell_rect(*cell)) == (40, 0, 60)


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
    assert pygame.display.get_caption()[0] == "Tetris"


def test_main_runs_frames():
    assert app.main(max_frames=3) == 0


def test_quit_event_ends_main_early():
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
        (pygame.K_UP, Key.ROTATE_CW),
        (pygame.K_x, Key.ROTATE_CW),
        (pygame.K_z, Key.ROTATE_CCW),
        (pygame.K_LCTRL, Key.ROTATE_CCW),
        (pygame.K_p, Key.PAUSE),
        (pygame.K_ESCAPE, Key.PAUSE),
        (pygame.K_RETURN, Key.RESTART),
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


def test_quit_event_stops_loop():
    controller = Controller(Game(seed=1))
    assert not app.handle_event(pygame.event.Event(pygame.QUIT), controller)
