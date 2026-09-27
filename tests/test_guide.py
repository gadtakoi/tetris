import re
import subprocess
import sys
from pathlib import Path

import pytest

from tetris_ui import guide

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("en", "ru")
TEXT_PAGES = [page for page in range(guide.PAGE_COUNT) if page != guide.CONTROLS_PAGE]
CYRILLIC = re.compile("[а-яёА-ЯЁ]")


def page_text(page: int, language: str) -> str:
    return " ".join(guide.paragraphs(page, language))


def test_six_pages_in_spec_order():
    assert guide.PAGE_TITLES == (
        "Menu and pause", "Controls", "How to play", "Tips", "Settings and sound", "High scores",
    )
    assert guide.PAGE_COUNT == 6
    assert guide.CONTROLS_PAGE == 1


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_text_page_has_paragraphs(language):
    for page in TEXT_PAGES:
        paragraphs = guide.paragraphs(page, language)
        assert paragraphs, page
        assert all(p.strip() == p and p for p in paragraphs), page
    assert guide.paragraphs(guide.CONTROLS_PAGE, language) == ()  # built by layout


def test_languages_are_not_mixed():
    for page in TEXT_PAGES:
        for paragraph in guide.paragraphs(page, "ru"):
            assert CYRILLIC.search(paragraph), paragraph
        for paragraph in guide.paragraphs(page, "en"):
            assert not CYRILLIC.search(paragraph.replace("Русский", "")), paragraph


def test_unknown_language_gives_english():
    assert guide.paragraphs(0, "de") == guide.paragraphs(0, "en")


@pytest.mark.parametrize("language", LANGUAGES)
def test_scores_on_how_to_play(language):
    text = page_text(2, language)
    for number in ("40", "100", "300", "1200", "10"):
        assert re.search(rf"\b{number}\b", text), number


@pytest.mark.parametrize(("language", "delay"), [("en", "0.5 s"), ("ru", "0,5 с")])
def test_lock_delay_on_tips(language, delay):
    text = page_text(3, language)
    assert "Shift" in text and re.search(r"\b15\b", text) and delay in text
    assert ("Space" if language == "en" else "Пробел") in text


@pytest.mark.parametrize("language", LANGUAGES)
def test_high_scores_page(language):
    text = page_text(5, language)
    assert re.search(r"\b10\b", text) and "PLAYER" in text
    assert "Backspace" in text and "Enter" in text and "Esc" in text


@pytest.mark.parametrize(("language", "items"), [
    ("en", ["New game", "High scores", "Settings", "Controls", "Guide", "Quit",
            "Continue", "Main menu"]),
    ("ru", ["Новая игра", "Рекорды", "Настройки", "Управление", "Инструкция", "Выход",
            "Продолжить", "Главное меню"]),
])
def test_menu_items_on_the_first_page(language, items):
    text = page_text(0, language)
    for item in items:
        assert item in text, item
    for key in ("P", "Esc", "Enter", "F1", "F2"):
        assert re.search(rf"\b{key}\b", text), key


@pytest.mark.parametrize(("language", "values"), [
    ("en", ["English", "Русский", "Slow", "Normal", "Fast"]),
    ("ru", ["English", "Русский", "Медленно", "Обычно", "Быстро"]),
])
def test_settings_page(language, values):
    text = page_text(4, language)
    for value in values:
        assert value in text, value
    assert re.search(r"\b19\b", text)
    for key in ("M", "N", "9", "0"):
        assert re.search(rf"\b{key}\b", text), key


def test_no_arrow_symbols():
    for language in LANGUAGES:
        for page in range(guide.PAGE_COUNT):
            assert not set(page_text(page, language)) & set("←↑→↓№")
    assert not set("".join(guide.PAGE_TITLES)) & set("←↑→↓№")


def test_guide_module_does_not_import_pygame():
    code = "import sys, tetris_ui.guide; assert 'pygame' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
