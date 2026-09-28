"""Command line entry point, shared by `python -m tetris_ui` and tetris_shmetris.exe."""

from __future__ import annotations

import argparse
import sys

from tetris_ui import GAME_TITLE  # no pygame: the package itself imports nothing


def _frame_count(text: str) -> int:
    """argparse type for --max-frames: an integer of at least 1."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line; invalid arguments exit with code 2."""
    parser = argparse.ArgumentParser(prog=GAME_TITLE, description=f"{GAME_TITLE}: classic Tetris.")
    parser.add_argument(
        "--max-frames",
        type=_frame_count,
        default=None,
        metavar="N",
        help="draw N frames and exit (for automated checks)",
    )
    parser.add_argument(
        "--sound-check",
        action="store_true",
        help="play every sound of the game one by one and mark the unpleasant ones",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    """Parse the arguments before opening any window, then run the game or, with
    --sound-check, the sound check."""
    args = parse_args(argv)
    from tetris_ui import app  # imports pygame, so only after the arguments are valid

    if args.sound_check:
        return app.run_sound_check(max_frames=args.max_frames)
    return app.main(max_frames=args.max_frames)


def warn(message: str) -> None:
    """Print a warning to stderr; a windowed exe has no stderr, so stay silent there."""
    if sys.stderr is not None:
        print(f"tetris: {message}", file=sys.stderr)
