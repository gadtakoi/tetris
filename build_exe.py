"""Build dist/tetris.exe: one windowed file that runs without Python installed.

Usage (from the project's virtual environment):
    python -m pip install -r requirements.txt -r requirements-build.txt
    python build_exe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

PYINSTALLER_ARGS = [
    str(PROJECT_ROOT / "launcher.py"),
    "--onefile",
    "--windowed",
    "--name", "tetris",
    "--clean",
    "--noconfirm",
    "--distpath", str(PROJECT_ROOT / "dist"),
    "--workpath", str(PROJECT_ROOT / "build"),
    "--specpath", str(PROJECT_ROOT),
    "--paths", str(PROJECT_ROOT),
]


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is missing: pip install -r requirements-build.txt", file=sys.stderr)
        return 1
    try:
        PyInstaller.__main__.run(PYINSTALLER_ARGS)
    except SystemExit as exit_:  # PyInstaller reports failures by exiting
        return exit_.code if isinstance(exit_.code, int) else 1
    except Exception as error:  # noqa: BLE001 - any build failure must give a non-zero code
        print(f"build failed: {error}", file=sys.stderr)
        return 1
    exe = PROJECT_ROOT / "dist" / "tetris.exe"
    if not exe.is_file():
        print(f"build finished but {exe} is missing", file=sys.stderr)
        return 1
    print(f"built {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
