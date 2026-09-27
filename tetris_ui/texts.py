"""Interface languages without pygame: the Russian translation of every fixed text.

English texts are the keys, the same strings the specifications use, so English needs
no table: tr() gives an English text back unchanged. Texts with numbers or names in them
are built by the template functions below; only fixed strings are in RU.
"""

from __future__ import annotations

RU: dict[str, str] = {
    # side panel
    "NEXT": "ДАЛЕЕ",
    "HOLD": "ЗАПАС",
    "SCORE": "ОЧКИ",
    "LINES": "ЛИНИИ",
    "LEVEL": "УРОВЕНЬ",
    "MUSIC ON": "МУЗЫКА ВКЛ",
    "MUSIC OFF": "МУЗЫКА ВЫКЛ",
    "SOUND ON": "ЗВУК ВКЛ",
    "SOUND OFF": "ЗВУК ВЫКЛ",
    # over the field
    "PAUSE": "ПАУЗА",
    "Continue": "Продолжить",
    "Main menu": "Главное меню",
    "GAME OVER": "ИГРА ОКОНЧЕНА",
    "NEW RECORD": "НОВЫЙ РЕКОРД",
    "HIGH SCORES": "РЕКОРДЫ",
    "No records yet": "Рекордов пока нет",
    "Enter - new game": "Enter - новая игра",
    "Esc - main menu": "Esc - главное меню",
    # main menu and its screens
    "New game": "Новая игра",
    "High scores": "Рекорды",
    "Settings": "Настройки",
    "Controls": "Управление",
    "Quit": "Выход",
    "Guide": "Инструкция",
    "Up / Down - choose, Enter - select": "Вверх / Вниз - выбор, Enter - открыть",
    "Press Enter or Esc to return": "Enter или Esc - назад",
    "Press F1 or Enter to return": "F1 или Enter - назад",
    "Left / Right - change, Esc - back": "Влево / Вправо - изменить, Esc - назад",
    # the guide (F2): page titles and the hint
    "Menu and pause": "Меню и пауза",
    "How to play": "Как играть",
    "Tips": "Приёмы",
    "Settings and sound": "Настройки и звук",
    "Left / Right - page, Esc - close": "Влево / Вправо - листать, Esc - закрыть",
    # settings rows and values
    "Language": "Язык",
    "Music": "Музыка",
    "Music volume": "Громкость музыки",
    "Sound": "Звук",
    "Sound volume": "Громкость звука",
    "Start level": "Начальный уровень",
    "Ghost": "Тень",
    "Autorepeat": "Автоповтор",
    "Back": "Назад",
    "On": "Вкл",
    "Off": "Выкл",
    "Slow": "Медленно",
    "Normal": "Обычно",
    "Fast": "Быстро",
    # key list: keys
    "Left / Right": "Влево / Вправо",
    "Down": "Вниз",
    "Space": "Пробел",
    "Up / X": "Вверх / X",
    # key list: actions
    "Move": "Сдвиг",
    "Soft drop": "Мягкое падение",
    "Hard drop": "Жёсткое падение",
    "Rotate right": "Поворот вправо",
    "Rotate left": "Поворот влево",
    "Hold": "Отложить",
    "Pause": "Пауза",
    "Help": "Помощь",
    "Music on/off": "Музыка вкл/выкл",
    "Sound on/off": "Звук вкл/выкл",
    "Select / new game": "Выбор / новая игра",
}


def tr(text: str, language: str) -> str:
    """The text in the given language ("en" or "ru"); texts without a translation (names,
    numbers, the game title) come back unchanged."""
    if language == "ru":
        return RU.get(text, text)
    return text


def music_volume_text(volume: int, language: str) -> str:
    """The panel line with the music volume: "MUSIC 50%" or "МУЗЫКА 50%"."""
    return f"{'МУЗЫКА' if language == 'ru' else 'MUSIC'} {volume}%"


def sound_volume_text(volume: int, language: str) -> str:
    """The panel line with the effects volume: "SOUND 100%" or "ЗВУК 100%"."""
    return f"{'ЗВУК' if language == 'ru' else 'SOUND'} {volume}%"


def name_line(name: str, language: str) -> str:
    """The name being typed with a cursor: "Name: Ann_" or "Имя: Ann_"."""
    return f"{'Имя' if language == 'ru' else 'Name'}: {name}_"


def page_line(page: int, total: int, language: str) -> str:
    """The guide's page number: "Page 2 / 6" or "Страница 2 / 6"."""
    return f"{'Страница' if language == 'ru' else 'Page'} {page} / {total}"
