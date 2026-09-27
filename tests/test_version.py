import re
import shutil
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
    assert __version__ == "1.0.0"


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
        "StringStruct('ProductName', 'SEVA Tetris')",
        "StringStruct('FileDescription', 'SEVA Tetris')",
        "StringStruct('OriginalFilename', 'SEVA Tetris.exe')",
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
        "FileDescription": "SEVA Tetris",
        "FileVersion": "2.13.4.0",
        "InternalName": "SEVA Tetris",
        "OriginalFilename": "SEVA Tetris.exe",
        "ProductName": "SEVA Tetris",
        "ProductVersion": "2.13.4",
    }


def test_build_passes_the_version_file():
    args = build_exe.PYINSTALLER_ARGS
    assert args[args.index("--version-file") + 1] == str(build_exe.VERSION_FILE)
    assert build_exe.VERSION_FILE == PROJECT_ROOT / "version_info.txt"


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
