"""Entry script for the PyInstaller build (named so it does not shadow the tetris package)."""

from tetris_ui.cli import run

raise SystemExit(run())
