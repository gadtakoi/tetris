import io
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

import build_exe
from tetris_ui import __version__

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def test_version_is_major_minor_patch():
    assert SEMVER.fullmatch(__version__)


def test_current_version():
    assert __version__ == "3.2.0"


def test_package_import_does_not_load_pygame():
    code = "import sys, tetris_ui; assert 'pygame' not in sys.modules; print(tetris_ui.__version__)"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == __version__


# --- Version resource of the exe -----------------------------------------------


def test_version_info_for_1_0_0():
    text = build_exe.version_info_text("1.0.0")
    for part in (
        "filevers=(1, 0, 0, 0)",
        "prodvers=(1, 0, 0, 0)",
        "StringStruct('FileVersion', '1.0.0.0')",
        "StringStruct('ProductVersion', '1.0.0')",
        "StringStruct('ProductName', 'Tetris Shmetris')",
        "StringStruct('FileDescription', 'Tetris Shmetris')",
        "StringStruct('OriginalFilename', 'tetris_shmetris.exe')",
        "StringStruct('InternalName', 'tetris_shmetris')",
    ):
        assert part in text, part


def test_version_info_follows_the_version():
    text = build_exe.version_info_text("2.13.4")
    assert "filevers=(2, 13, 4, 0)" in text and "prodvers=(2, 13, 4, 0)" in text
    assert "StringStruct('FileVersion', '2.13.4.0')" in text
    assert "StringStruct('ProductVersion', '2.13.4')" in text


def test_pyinstaller_reads_the_version_info(tmp_path):
    versioninfo = pytest.importorskip("PyInstaller.utils.win32.versioninfo")
    path = tmp_path / "version_info.txt"
    path.write_text(build_exe.version_info_text("2.13.4"), encoding="utf-8")
    info = versioninfo.load_version_info_from_text_file(str(path))
    assert (info.ffi.fileVersionMS, info.ffi.fileVersionLS) == (2 << 16 | 13, 4 << 16)
    assert (info.ffi.productVersionMS, info.ffi.productVersionLS) == (2 << 16 | 13, 4 << 16)
    strings = {s.name: s.val for s in info.kids[0].kids[0].kids}
    assert strings == {
        "FileDescription": "Tetris Shmetris",
        "FileVersion": "2.13.4.0",
        "InternalName": "tetris_shmetris",
        "OriginalFilename": "tetris_shmetris.exe",
        "ProductName": "Tetris Shmetris",
        "ProductVersion": "2.13.4",
    }


PLATFORMS = ("win32", "darwin", "linux")


@pytest.mark.parametrize("platform", PLATFORMS)
def test_exe_name(platform):
    args = build_exe.pyinstaller_args(platform)
    assert args[args.index("--name") + 1] == build_exe.EXE_NAME == "tetris_shmetris"


def test_what_each_system_builds():
    dist = PROJECT_ROOT / "dist"
    assert build_exe.built_path("win32") == dist / "tetris_shmetris.exe"
    assert build_exe.built_path("darwin") == dist / "tetris_shmetris.app"
    assert build_exe.built_path("linux") == dist / "tetris_shmetris"


def test_windows_and_linux_build_one_file_and_macos_an_app():
    windows, macos, linux = (build_exe.pyinstaller_args(p) for p in PLATFORMS)
    assert {"--onefile", "--windowed"} <= set(windows)
    assert {"--onedir", "--windowed"} <= set(macos) and "--onefile" not in macos
    assert macos[macos.index("--osx-bundle-identifier") + 1] == build_exe.BUNDLE_ID
    assert "--onefile" in linux and "--windowed" not in linux


def test_only_the_first_builds_exe_is_removed():
    assert build_exe.STALE_EXES == (PROJECT_ROOT / "dist" / "tetris.exe",)


def test_only_the_windows_build_gets_the_version_file():
    args = build_exe.pyinstaller_args("win32")
    assert args[args.index("--version-file") + 1] == str(build_exe.VERSION_FILE)
    assert build_exe.VERSION_FILE == PROJECT_ROOT / "version_info.txt"
    assert "--version-file" not in build_exe.pyinstaller_args("darwin")
    assert "--version-file" not in build_exe.pyinstaller_args("linux")


@pytest.mark.parametrize("platform", PLATFORMS)
def test_build_puts_the_fonts_inside(platform):
    args = build_exe.pyinstaller_args(platform)
    source, target = args[args.index("--add-data") + 1].split(os.pathsep)
    assert Path(source) == PROJECT_ROOT / "tetris_ui" / "fonts"
    assert target == "tetris_ui/fonts"
    assert (Path(source) / "OFL.txt").is_file()


@pytest.mark.parametrize("platform", PLATFORMS)
def test_build_puts_the_icon_inside(platform):
    args = build_exe.pyinstaller_args(platform)
    data = [args[i + 1] for i, arg in enumerate(args) if arg == "--add-data"]
    assert data[1].split(os.pathsep) == [str(PROJECT_ROOT / "tetris_ui" / "icon.png"), "tetris_ui"]
    assert build_exe.ICON_FILE.is_file()


def test_icon_file_for_each_system(tmp_path):
    pytest.importorskip("pygame")
    assert build_exe.write_icon(tmp_path, "win32") == tmp_path / "tetris_shmetris.ico"
    assert build_exe.write_icon(tmp_path, "darwin") == tmp_path / "tetris_shmetris.icns"
    assert build_exe.write_icon(tmp_path, "linux") is None
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "tetris_shmetris.icns", "tetris_shmetris.ico"]


def test_app_icon_has_every_size_macos_asks_for():
    pygame = pytest.importorskip("pygame")
    icns = build_exe.icon_icns_bytes()
    assert icns[:4] == b"icns" and struct.unpack_from(">I", icns, 4)[0] == len(icns)
    offset = 8
    for kind, size in build_exe.ICNS_TYPES:
        assert icns[offset:offset + 4] == kind.encode("ascii")
        length = struct.unpack_from(">I", icns, offset + 4)[0]
        image = pygame.image.load(io.BytesIO(icns[offset + 8:offset + length]), "icon.png")
        assert image.get_size() == (size, size)
        assert image.get_at((0, 0)).a == 0  # the rounded tile leaves the corners clear
        offset += length
    assert offset == len(icns)


def test_app_info_names_the_game_and_its_version():
    assert build_exe.app_info("2.13.4") == {
        "CFBundleName": "Tetris Shmetris",
        "CFBundleDisplayName": "Tetris Shmetris",
        "CFBundleShortVersionString": "2.13.4",
        "CFBundleVersion": "2.13.4",
    }
    assert build_exe.app_info()["CFBundleShortVersionString"] == __version__


def test_exe_icon_has_every_size_windows_asks_for():
    pygame = pytest.importorskip("pygame")
    ico = build_exe.icon_ico_bytes()
    assert struct.unpack_from("<HHH", ico) == (0, 1, len(build_exe.ICON_SIZES))
    for i, size in enumerate(build_exe.ICON_SIZES):
        width, height, _, _, planes, bits, length, offset = struct.unpack_from(
            "<BBBBHHII", ico, 6 + 16 * i)
        assert (width, height, planes, bits) == (size % 256, size % 256, 1, 32)
        image = pygame.image.load(io.BytesIO(ico[offset:offset + length]), "icon.png")
        assert image.get_size() == (size, size)
        assert image.get_at((0, 0)).a == 0  # the rounded tile leaves the corners clear
        assert image.get_at((size // 2, size // 2)).a == 255
    assert offset + length == len(ico)


def test_committed_version_file_is_up_to_date():
    text = (PROJECT_ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert text == build_exe.version_info_text(__version__), (
        "version_info.txt does not match tetris_ui.__version__: "
        "run python build_exe.py and commit version_info.txt"
    )


def test_version_file_is_not_ignored_by_git():
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    result = subprocess.run(
        ["git", "check-ignore", "-q", "version_info.txt"], cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode == 128:
        pytest.skip("not a git checkout")
    assert result.returncode == 1, "version_info.txt must not be ignored: it belongs in git"


def test_version_file_is_written_only_when_it_changes(tmp_path):
    path = tmp_path / "version_info.txt"
    assert build_exe.write_version_file(path)
    assert path.read_text(encoding="utf-8") == build_exe.version_info_text(__version__)
    assert b"\r\n" not in path.read_bytes()  # the same line ends on every system
    assert not build_exe.write_version_file(path)
    path.write_text("stale", encoding="utf-8")
    assert build_exe.write_version_file(path)
