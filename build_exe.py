"""Build the game for the system the script runs on, so that it runs without Python:

- Windows: "dist/tetris_shmetris.exe", one windowed file;
- macOS: "dist/tetris_shmetris.app", an application bundle;
- Linux: "dist/tetris_shmetris", one executable file.

PyInstaller cannot build for another system, so each one is built on its own (the GitHub
release workflow uses a runner of each). The exe gets a Windows version resource
(Properties -> Details) from version_info.txt, which is kept in git; the build rewrites that
file from tetris_ui.__version__ whenever it differs. The app gets the version in its
Info.plist. Their icons are made from tetris_ui/icon.png at every build and are not kept.

Usage (from the project's virtual environment):
    python -m pip install -r requirements.txt -r requirements-build.txt
    python build_exe.py
"""

from __future__ import annotations

import io
import os
import plistlib
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from tetris_ui import GAME_TITLE, __version__  # no pygame: the package imports nothing

PROJECT_ROOT = Path(__file__).resolve().parent
EXE_NAME = "tetris_shmetris"  # the exe's file name; the game's name is GAME_TITLE
DIST_DIR = PROJECT_ROOT / "dist"
# The exe's version resource; kept in git, written from __version__ by write_version_file().
VERSION_FILE = PROJECT_ROOT / "version_info.txt"
# Left behind by builds made before the game got its own name.
STALE_EXES = (DIST_DIR / "tetris.exe",)
# The game's fonts go inside the exe, at the same path relative to the package as in the
# sources, so tetris_ui.render finds them next to its module in both cases.
FONT_DIR = PROJECT_ROOT / "tetris_ui" / "fonts"
FONT_DATA = f"{FONT_DIR}{os.pathsep}tetris_ui/fonts"
# The game's icon: inside the build for the window (tetris_ui.app loads it), and as the
# exe's and the app's own icon, made by icon_ico_bytes() and icon_icns_bytes().
ICON_FILE = PROJECT_ROOT / "tetris_ui" / "icon.png"
ICON_DATA = f"{ICON_FILE}{os.pathsep}tetris_ui"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)  # every size Windows asks an .ico for
# The .icns entries macOS uses, each a PNG of the given size ("ic11" is 16 px at 2x, etc.).
ICNS_TYPES = (("icp4", 16), ("ic11", 32), ("icp5", 32), ("ic12", 64), ("ic07", 128),
              ("ic13", 256), ("ic08", 256), ("ic14", 512), ("ic09", 512), ("ic10", 1024))
BUNDLE_ID = "io.github.gadtakoi.tetris-shmetris"  # the macOS app's identifier

COMMON_ARGS = [
    str(PROJECT_ROOT / "launcher.py"),
    "--name", EXE_NAME,
    "--clean",
    "--noconfirm",
    "--distpath", str(DIST_DIR),
    "--workpath", str(PROJECT_ROOT / "build"),
    "--specpath", str(PROJECT_ROOT),
    "--paths", str(PROJECT_ROOT),
    "--add-data", FONT_DATA,
    "--add-data", ICON_DATA,
]


def pyinstaller_args(platform: str = sys.platform) -> list[str]:
    """PyInstaller's arguments for a sys.platform, without the icon (main() adds it).

    Windows gets one windowed file with the version resource. macOS gets an app bundle,
    which PyInstaller builds from a folder, not from one file. Linux gets one file: it has
    no console window to hide.
    """
    if platform == "win32":
        return [*COMMON_ARGS, "--onefile", "--windowed", "--version-file", str(VERSION_FILE)]
    if platform == "darwin":
        return [*COMMON_ARGS, "--onedir", "--windowed", "--osx-bundle-identifier", BUNDLE_ID]
    return [*COMMON_ARGS, "--onefile"]


def built_path(platform: str = sys.platform) -> Path:
    """What the build makes for a sys.platform: the exe, the app bundle or the file."""
    if platform == "win32":
        return DIST_DIR / f"{EXE_NAME}.exe"
    if platform == "darwin":
        return DIST_DIR / f"{EXE_NAME}.app"
    return DIST_DIR / EXE_NAME


def version_info_text(version: str) -> str:
    """The exe's Windows version resource in the format of PyInstaller's --version-file.

    The file version is the MAJOR.MINOR.PATCH version with a fourth part 0 (1.0.0 gives
    1.0.0.0); the product version is the version itself.
    """
    numbers = (*(int(part) for part in version.split(".")), 0)
    strings = (
        ("FileDescription", GAME_TITLE),
        ("FileVersion", ".".join(map(str, numbers))),
        ("InternalName", EXE_NAME),
        ("OriginalFilename", f"{EXE_NAME}.exe"),
        ("ProductName", GAME_TITLE),
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


def _shrunk(pygame, image, size: int):
    """The square image scaled to size x size. smoothscale shrinks exactly only by 2, and
    loses a little alpha inside the tile for other factors (1024 -> 24), so the image is
    first scaled to size times a power of 2 and then halved step by step."""
    step = size
    while step < image.get_width():
        step *= 2
    image = pygame.transform.smoothscale(image, (step, step))
    while step > size:
        step //= 2
        image = pygame.transform.smoothscale(image, (step, step))
    return image


def _png_bytes(pygame, image, size: int) -> bytes:
    """The square image scaled to size x size, as a PNG file."""
    buffer = io.BytesIO()
    pygame.image.save(_shrunk(pygame, image, size), buffer, "png")
    return buffer.getvalue()


def icon_ico_bytes(png: Path = ICON_FILE, sizes: tuple[int, ...] = ICON_SIZES) -> bytes:
    """A Windows .ico with png scaled to each of sizes, every image stored as PNG."""
    import pygame  # only here: the rest of the build script works without it

    image = pygame.image.load(png)
    images = [_png_bytes(pygame, image, size) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))  # reserved, type 1 = icon, count
    offset = len(header) + 16 * len(images)
    entries = []
    for size, data in zip(sizes, images):
        # width, height (0 means 256), colors, reserved, planes, bits per pixel, size, offset
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32,
                                   len(data), offset))
        offset += len(data)
    return header + b"".join(entries) + b"".join(images)


def icon_icns_bytes(png: Path = ICON_FILE,
                    types: tuple[tuple[str, int], ...] = ICNS_TYPES) -> bytes:
    """A macOS .icns with png scaled for each of types, every image stored as PNG."""
    import pygame  # only here: the rest of the build script works without it

    image = pygame.image.load(png)
    chunks = []
    for kind, size in types:
        data = _png_bytes(pygame, image, size)
        # the type, then the length of the whole entry with its 8-byte head
        chunks.append(kind.encode("ascii") + struct.pack(">I", 8 + len(data)) + data)
    body = b"".join(chunks)
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def write_icon(folder: Path, platform: str = sys.platform) -> Path | None:
    """Write the build's icon for a sys.platform into folder and return it; None on Linux,
    where an executable file has no icon (the window still gets it from icon.png)."""
    if platform == "win32":
        icon = folder / f"{EXE_NAME}.ico"
        icon.write_bytes(icon_ico_bytes())
    elif platform == "darwin":
        icon = folder / f"{EXE_NAME}.icns"
        icon.write_bytes(icon_icns_bytes())
    else:
        return None
    return icon


def app_info(version: str = __version__) -> dict[str, str]:
    """What the build sets in the app's Info.plist over PyInstaller's values: the name
    Finder and the menu bar show, and the version (PyInstaller writes 0.0.0)."""
    return {
        "CFBundleName": GAME_TITLE,
        "CFBundleDisplayName": GAME_TITLE,
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
    }


def finish_app(app: Path) -> None:
    """Write app_info() into the app's Info.plist and sign the app again, ad hoc as
    PyInstaller did: the signature covers Info.plist, and Apple silicon does not run an
    app whose signature does not match."""
    plist = app / "Contents" / "Info.plist"
    info = plistlib.loads(plist.read_bytes())
    info.update(app_info())
    plist.write_bytes(plistlib.dumps(info))
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)


def main() -> int:
    """Run PyInstaller and return 0 if the build was made, non-zero otherwise."""
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is missing: pip install -r requirements-build.txt", file=sys.stderr)
        return 1
    if write_version_file():
        print(f"updated {VERSION_FILE.name} for version {__version__}: commit it")
    built = built_path()
    try:
        with tempfile.TemporaryDirectory() as temp:
            icon = write_icon(Path(temp))
            icon_args = [] if icon is None else ["--icon", str(icon)]
            PyInstaller.__main__.run([*pyinstaller_args(), *icon_args])
        if sys.platform == "darwin" and built.is_dir():
            finish_app(built)
    except SystemExit as exit_:  # PyInstaller reports failures by exiting
        return exit_.code if isinstance(exit_.code, int) else 1
    except Exception as error:  # noqa: BLE001 - any build failure must give a non-zero code
        print(f"build failed: {error}", file=sys.stderr)
        return 1
    if not built.exists():
        print(f"build finished but {built} is missing", file=sys.stderr)
        return 1
    for stale in STALE_EXES:
        stale.unlink(missing_ok=True)
    print(f"built {built}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
