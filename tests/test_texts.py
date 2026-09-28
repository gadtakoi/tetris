import subprocess
import sys
from pathlib import Path

import pytest

from tetris_ui.texts import (
    RU,
    check_volume_text,
    music_volume_text,
    name_line,
    page_line,
    sound_volume_text,
    tr,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The table "Русские надписи" from the localization spec, row by row.
SPEC_PAIRS = [
    ('NEXT', 'ДАЛЕЕ'),
    ('HOLD', 'ЗАПАС'),
    ('SCORE', 'ОЧКИ'),
    ('LINES', 'ЛИНИИ'),
    ('LEVEL', 'УРОВЕНЬ'),
    ('MUSIC ON', 'МУЗЫКА ВКЛ'),
    ('MUSIC OFF', 'МУЗЫКА ВЫКЛ'),
    ('MUSIC <n>%', 'МУЗЫКА <n>%'),
    ('SOUND ON', 'ЗВУК ВКЛ'),
    ('SOUND OFF', 'ЗВУК ВЫКЛ'),
    ('SOUND <n>%', 'ЗВУК <n>%'),
    ('PAUSE', 'ПАУЗА'),
    ('Continue', 'Продолжить'),
    ('Main menu', 'Главное меню'),
    ('GAME OVER', 'ИГРА ОКОНЧЕНА'),
    ('NEW RECORD', 'НОВЫЙ РЕКОРД'),
    ('Name: <имя>_', 'Имя: <имя>_'),
    ('HIGH SCORES', 'РЕКОРДЫ'),
    ('No records yet', 'Рекордов пока нет'),
    ('Enter - new game', 'Enter - новая игра'),
    ('Esc - main menu', 'Esc - главное меню'),
    ('New game', 'Новая игра'),
    ('High scores', 'Рекорды'),
    ('Settings', 'Настройки'),
    ('Controls', 'Управление'),
    ('Quit', 'Выход'),
    ('Guide', 'Инструкция'),
    ('Up / Down - choose, Enter - select', 'Вверх / Вниз - выбор, Enter - открыть'),
    ('Press Enter or Esc to return', 'Enter или Esc - назад'),
    ('Press F1 or Enter to return', 'F1 или Enter - назад'),
    ('Left / Right - change, Esc - back', 'Влево / Вправо - изменить, Esc - назад'),
    ('Menu and pause', 'Меню и пауза'),
    ('How to play', 'Как играть'),
    ('Tips', 'Приёмы'),
    ('Settings and sound', 'Настройки и звук'),
    ('Page <n> / <m>', 'Страница <n> / <m>'),
    ('Left / Right - page, Esc - close', 'Влево / Вправо - листать, Esc - закрыть'),
    ('Language', 'Язык'),
    ('Music', 'Музыка'),
    ('Music volume', 'Громкость музыки'),
    ('Sound', 'Звук'),
    ('Sound volume', 'Громкость звука'),
    ('Start level', 'Начальный уровень'),
    ('Ghost', 'Тень'),
    ('Autorepeat', 'Автоповтор'),
    ('Back', 'Назад'),
    ('On', 'Вкл'),
    ('Off', 'Выкл'),
    ('Slow', 'Медленно'),
    ('Normal', 'Обычно'),
    ('Fast', 'Быстро'),
    ('Left / Right', 'Влево / Вправо'),
    ('Down', 'Вниз'),
    ('Space', 'Пробел'),
    ('Up / X', 'Вверх / X'),
    ('Move', 'Сдвиг'),
    ('Soft drop', 'Мягкое падение'),
    ('Hard drop', 'Жёсткое падение'),
    ('Rotate right', 'Поворот вправо'),
    ('Rotate left', 'Поворот влево'),
    ('Hold', 'Отложить'),
    ('Pause', 'Пауза'),
    ('Help', 'Помощь'),
    ('Music on/off', 'Музыка вкл/выкл'),
    ('Sound on/off', 'Звук вкл/выкл'),
    ('Select / new game', 'Выбор / новая игра'),
    ('Sound check', 'Проверка звуков'),
    ('Rotate', 'Поворот'),
    ('Hold piece', 'Откладывание фигуры'),
    ('Lock', 'Закрепление'),
    ('Line clear', 'Уборка рядов'),
    ('Tetris', 'Тетрис'),
    ('Level up', 'Новый уровень'),
    ('Game over', 'Конец игры'),
    ('Move with autorepeat', 'Сдвиг с автоповтором'),
    ('Clear + level up', 'Уборка + новый уровень'),
    ('Tetris + level up', 'Тетрис + новый уровень'),
    ('Lock + game over', 'Закрепление + конец игры'),
    ('Piece moved left or right', 'Фигура сдвинулась влево или вправо'),
    ('Piece turned', 'Фигура повернулась'),
    ('Piece put on hold', 'Фигура отложена'),
    ('Piece locked, no lines cleared', 'Фигура закрепилась, ряды не убраны'),
    ('One to three lines cleared', 'Убрано от одного до трёх рядов'),
    ('Four lines cleared at once', 'Убраны четыре ряда сразу'),
    ('Level went up', 'Уровень повысился'),
    ('Game ended', 'Партия окончена'),
    ('Key held: 7 moves wall to wall', 'Клавиша удержана: 7 сдвигов от стены до стены'),
    ('Lines cleared, level went up', 'Ряды убраны, уровень повысился'),
    ('Tetris, level went up', 'Тетрис, уровень повысился'),
    ('Last piece locked, game over', 'Последняя фигура закрепилась, конец игры'),
    ('Background melody in a loop', 'Фоновая мелодия по кругу'),
    ('unpleasant', 'неприятно'),
    ('Volume: effects <n>%, music <m>%', 'Громкость: эффекты <n>%, музыка <m>%'),
    ('No sound device', 'Нет звукового устройства'),
    ('Marks are saved to sound-check.json', 'Отметки сохраняются в sound-check.json'),
    ('Up / Down - choose, Space - play again', 'Вверх / Вниз - выбор, Пробел - ещё раз'),
    ('X - unpleasant, Esc - exit', 'X - неприятно, Esc - выход'),
]
FIXED_PAIRS = [(en, ru) for en, ru in SPEC_PAIRS if "<" not in en]


@pytest.mark.parametrize(("en", "ru"), FIXED_PAIRS)
def test_russian_text(en, ru):
    assert tr(en, "ru") == ru


def test_table_has_exactly_the_spec_texts():
    assert RU == dict(FIXED_PAIRS)


@pytest.mark.parametrize("en", [en for en, _ in FIXED_PAIRS])
def test_english_is_unchanged(en):
    assert tr(en, "en") == en


@pytest.mark.parametrize("text", [
    "Tetris Shmetris", "Ann", "Иван", "340", "50%", "English", "Русский",
    "Z / Ctrl", "C / Shift", "P / Esc", "F1", "M", "N", "- / +", "9 / 0", "Enter",
])
def test_untranslated_texts(text):
    assert tr(text, "ru") == text
    assert tr(text, "en") == text


def test_volume_templates():
    assert music_volume_text(50, "en") == "MUSIC 50%"
    assert music_volume_text(50, "ru") == "МУЗЫКА 50%"
    assert sound_volume_text(100, "en") == "SOUND 100%"
    assert sound_volume_text(0, "ru") == "ЗВУК 0%"


def test_name_template():
    assert name_line("Ann", "en") == "Name: Ann_"
    assert name_line("Иван", "ru") == "Имя: Иван_"
    assert name_line("", "ru") == "Имя: _"


def test_page_template():
    assert page_line(2, 6, "en") == "Page 2 / 6"
    assert page_line(1, 6, "ru") == "Страница 1 / 6"
    template_pairs = [(en, ru) for en, ru in SPEC_PAIRS if en.startswith("Page ")]
    assert template_pairs == [("Page <n> / <m>", "Страница <n> / <m>")]


def test_check_volume_template():
    assert check_volume_text(100, 50, "en") == "Volume: effects 100%, music 50%"
    assert check_volume_text(100, 50, "ru") == "Громкость: эффекты 100%, музыка 50%"
    template_pairs = [(en, ru) for en, ru in SPEC_PAIRS if en.startswith("Volume: ")]
    assert template_pairs == [("Volume: effects <n>%, music <m>%",
                               "Громкость: эффекты <n>%, музыка <m>%")]


def test_texts_module_does_not_import_pygame():
    code = "import sys, tetris_ui.texts; assert 'pygame' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
