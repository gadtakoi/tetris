"""Build "dist/SEVA Tetris.exe": one windowed file that runs without Python installed.

The exe gets a Windows version resource (Properties -> Details) from version_info.txt, which
is kept in git; the build rewrites that file from tetris_ui.__version__ whenever it differs.

Usage (from the project's virtual environment):
    python -m pip install -r requirements.txt -r requirements-build.txt
    python build_exe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from tetris_ui import __version__  # no pygame: the package itself imports nothing

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "SEVA Tetris"
DIST_DIR = PROJECT_ROOT / "dist"
# The exe's version resource; kept in git, written from __version__ by write_version_file().
VERSION_FILE = PROJECT_ROOT / "version_info.txt"
# Left behind by builds made before the game was renamed.
STALE_EXES = (DIST_DIR / "tetris.exe",)

PYINSTALLER_ARGS = [
    str(PROJECT_ROOT / "launcher.py"),
    "--onefile",
    "--windowed",
    "--name", APP_NAME,
    "--clean",
    "--noconfirm",
    "--distpath", str(DIST_DIR),
    "--workpath", str(PROJECT_ROOT / "build"),
    "--specpath", str(PROJECT_ROOT),
    "--paths", str(PROJECT_ROOT),
    "--version-file", str(VERSION_FILE),
]


def version_info_text(version: str) -> str:
    """The exe's Windows version resource in the format of PyInstaller's --version-file.

    The file version is the MAJOR.MINOR.PATCH version with a fourth part 0 (1.0.0 gives
    1.0.0.0); the product version is the version itself.
    """
    numbers = (*(int(part) for part in version.split(".")), 0)
    strings = (
        ("FileDescription", APP_NAME),
        ("FileVersion", ".".join(map(str, numbers))),
        ("InternalName", APP_NAME),
        ("OriginalFilename", f"{APP_NAME}.exe"),
        ("ProductName", APP_NAME),
        ("ProductVersion", version),
    )
    string_structs = "".join(
        f"          StringStruct({key!r}, {value!r}),\n" for key, value in strings
    )
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
{string_structs}        ],
      ),
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""


def write_version_file(path: Path = VERSION_FILE) -> bool:
    """Write the version resource for __version__ to path unless it already holds exactly
    that text; return whether the file was written."""
    text = version_info_text(__version__)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    """Run PyInstaller and return 0 if the exe was built, non-zero otherwise."""
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is missing: pip install -r requirements-build.txt", file=sys.stderr)
        return 1
    if write_version_file():
        print(f"updated {VERSION_FILE.name} for version {__version__}: commit it")
    try:
        PyInstaller.__main__.run(PYINSTALLER_ARGS)
    except SystemExit as exit_:  # PyInstaller reports failures by exiting
        return exit_.code if isinstance(exit_.code, int) else 1
    except Exception as error:  # noqa: BLE001 - any build failure must give a non-zero code
        print(f"build failed: {error}", file=sys.stderr)
        return 1
    exe = DIST_DIR / f"{APP_NAME}.exe"
    if not exe.is_file():
        print(f"build finished but {exe} is missing", file=sys.stderr)
        return 1
    for stale in STALE_EXES:
        stale.unlink(missing_ok=True)
    print(f"built {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
