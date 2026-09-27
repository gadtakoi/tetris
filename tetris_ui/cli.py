"""Command line entry point, shared by `python -m tetris_ui` and "SEVA Tetris.exe"."""

from __future__ import annotations

import argparse
import sys


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
    parser = argparse.ArgumentParser(prog="SEVA Tetris", description="SEVA Tetris: classic Tetris.")
    parser.add_argument(
        "--max-frames",
        type=_frame_count,
        default=None,
        metavar="N",
        help="draw N frames and exit (for automated checks)",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    """Parse the arguments before opening any window, then run the game."""
    args = parse_args(argv)
    from tetris_ui.app import main  # imports pygame, so only after the arguments are valid

    return main(max_frames=args.max_frames)


def warn(message: str) -> None:
    """Print a warning to stderr; a windowed exe has no stderr, so stay silent there."""
    if sys.stderr is not None:
        print(f"tetris: {message}", file=sys.stderr)
