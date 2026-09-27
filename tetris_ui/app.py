"""Window and main loop: pygame events in, frames out."""

from __future__ import annotations

import pygame

from tetris.game import Game
from tetris_ui import layout, render, storage
from tetris_ui.audio import Audio
from tetris_ui.input import Controller, Key

KEY_MAP: dict[int, Key] = {
    pygame.K_LEFT: Key.LEFT,
    pygame.K_RIGHT: Key.RIGHT,
    pygame.K_DOWN: Key.DOWN,
    pygame.K_SPACE: Key.HARD_DROP,
    pygame.K_c: Key.HOLD,
    pygame.K_LSHIFT: Key.HOLD,
    pygame.K_RSHIFT: Key.HOLD,
    pygame.K_UP: Key.ROTATE_CW,
    pygame.K_x: Key.ROTATE_CW,
    pygame.K_z: Key.ROTATE_CCW,
    pygame.K_LCTRL: Key.ROTATE_CCW,
    pygame.K_p: Key.PAUSE,
    pygame.K_ESCAPE: Key.PAUSE,
    pygame.K_RETURN: Key.RESTART,
    pygame.K_KP_ENTER: Key.RESTART,
    pygame.K_BACKSPACE: Key.BACKSPACE,
    pygame.K_m: Key.TOGGLE_MUSIC,
    pygame.K_n: Key.TOGGLE_SOUND,
    pygame.K_MINUS: Key.VOLUME_DOWN,
    pygame.K_KP_MINUS: Key.VOLUME_DOWN,
    pygame.K_EQUALS: Key.VOLUME_UP,  # the "+" key without Shift
    pygame.K_PLUS: Key.VOLUME_UP,
    pygame.K_KP_PLUS: Key.VOLUME_UP,
    pygame.K_F1: Key.HELP,
}


def create_window() -> pygame.Surface:
    """Open the game window at WINDOW_SIZE with the game title."""
    screen = pygame.display.set_mode(layout.WINDOW_SIZE)
    pygame.display.set_caption(layout.TITLE)
    return screen


def create_controller() -> Controller:
    """A controller that starts on the splash screen, with the saved high scores and
    sound settings; every change to them is written back to the data folder.
    """
    scores_path = storage.high_scores_path()
    settings_path = storage.settings_path()
    return Controller(
        Game(),
        storage.load(scores_path),
        on_save=lambda scores: storage.save(scores, scores_path),
        settings=storage.load_settings(settings_path),
        on_settings_change=lambda settings: storage.save_settings(settings, settings_path),
        splash=True,
    )


def handle_event(event: pygame.event.Event, controller: Controller) -> bool:
    """Route one event to the controller; return False when the window is closed."""
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.TEXTINPUT:
        controller.text_input(event.text)
        return True
    key = KEY_MAP.get(getattr(event, "key", None))
    if key is not None:
        if event.type == pygame.KEYDOWN:
            controller.key_down(key)
        elif event.type == pygame.KEYUP:
            controller.key_up(key)
    return True


def main(max_frames: int | None = None) -> int:
    """Run the game until the window is closed; max_frames is for tests only."""
    pygame.init()
    try:
        screen = create_window()
        fonts = render.make_fonts()
        clock = pygame.time.Clock()
        controller = create_controller()
        pygame.key.start_text_input()
        audio = Audio.create()
        frames = 0
        while max_frames is None or frames < max_frames:
            frame_ms = clock.tick(layout.FPS)
            for event in pygame.event.get():
                if not handle_event(event, controller):
                    return 0
            controller.update(frame_ms)
            audio.sync(controller)
            render.draw(screen, controller, fonts)
            pygame.display.flip()
            frames += 1
        return 0
    finally:
        pygame.quit()
