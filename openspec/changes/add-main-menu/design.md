# Design

## Context

`Controller` сейчас знает фазы `SPLASH`, `PLAYING` (с флагами `paused` и `help_open`), `NAME_ENTRY`, `TABLE`. Клавиши приходят как `Key` из `app.KEY_MAP`, где ↑ и X дают `ROTATE_CW`, а P и Esc — `PAUSE`. Настройки звука хранятся в неизменяемом `Settings`, и любое их изменение уходит в `on_settings_change`. `layout` строит надписи (`screen_texts`, `key_screen_texts`), `render` их рисует, а экран клавиш занимает всё окно. `Game.new_game()` всегда ставит уровень 0, `scoring.level_for(lines)` возвращает `lines // 10`. Мотивация описана в proposal.md, требования — в дельтах.

## Goals / Non-Goals

**Goals:**
- Меню и настройки без pygame: правила переходов, выделения и изменения значений проверяются тестами контроллера.
- Один источник для пунктов меню и строк настроек: его используют и контроллер, и раскладка.
- Стартовый уровень — правило логики (`tetris/`), а не интерфейса.

**Non-Goals:**
- Анимации и мышь.
- Перевод надписей (`add-russian-ui`): здесь все надписи английские, а язык только хранится.

## Decisions

### Фазы и клавиши
- `Phase`: `MENU`, `SCORES`, `SETTINGS`, `CONTROLS`, `PLAYING`, `NAME_ENTRY`, `TABLE`. `SPLASH` удаляется, а `Controller(..., splash=...)` заменяется на `start_in_menu: bool = False`. Существующие тесты по-прежнему начинают сразу с партии.
- Новые `Key.UP` (↑) и `Key.ESCAPE` (Esc). `KEY_MAP`:
  - `K_UP` → `UP`, а X остаётся `ROTATE_CW`;
  - `K_ESCAPE` → `ESCAPE`, а P остаётся `PAUSE`.
  - Во время партии `UP` работает как `ROTATE_CW`, а `ESCAPE` — как `PAUSE`, поэтому игровое поведение не меняется.
  - В меню ↑ и ↓ — навигация, Esc — «назад», и X с P там ничего не делают.
- Клавиши настроек звука (`SETTINGS_KEYS`) по-прежнему обрабатываются первыми во всех фазах, кроме ввода имени.

### Модуль `tetris_ui/menus.py` (без pygame)
```python
MAIN_ITEMS = ("New game", "High scores", "Settings", "Controls", "Quit")
PAUSE_ITEMS = ("Continue", "Main menu")
AUTOREPEAT = {"slow": (220, 70), "normal": (170, 50), "fast": (120, 30)}
SETTING_ROWS = ("language", "music_on", "music_volume", "sound_on", "sfx_volume",
                "start_level", "ghost", "autorepeat")          # затем «Back»

def setting_label(row) -> str                 # "Music volume"
def setting_value(settings, row) -> str       # "50%"
def step_setting(settings, row, steps) -> Settings   # по правилам: диапазон или по кругу
```
Контроллер хранит только индексы выделения (`menu_index`, `pause_index`, `settings_index`) и вызывает `step_setting`. Затем он применяет новые настройки тем же путём, что и клавиши звука, через `_apply_settings(new)`: при реальном изменении вызывается `on_settings_change`, при включении музыки растёт `music_generation`, при смене автоповтора пересоздаётся повторитель сдвига.

### Переходы
- Запуск: `MENU`, выделен «New game».
- `MENU` + Enter:
  - «New game» → `game.new_game(start_level)`, `PLAYING`, растёт `music_generation`;
  - «High scores» → `SCORES`; «Settings» → `SETTINGS` (выделена первая строка); «Controls» → `CONTROLS`;
  - «Quit» → `quit_requested = True`.
- `SCORES` и `CONTROLS`: Enter или Esc → `MENU`.
- `SETTINGS`:
  - ← и → меняют значение выделенной строки;
  - Enter на строке настройки действует как →, Enter на «Back» или Esc → `MENU`.
- Пауза (`paused` без `help_open`):
  - ↑ и ↓ меняют `pause_index`; Enter на «Continue» снимает паузу;
  - Enter на «Main menu» → `MENU`, без записи результата: фаза просто меняется, `_check_game_over` не срабатывает, потому что партия не окончена.
  - P и Esc снимают паузу, как раньше.
- `TABLE`: Enter → новая партия со стартовым уровнем, Esc → `MENU`.
- При каждом переходе в `MENU` выделение сбрасывается на «New game». Удерживаемые клавиши и флаги паузы и экрана клавиш сбрасываются.

### Стартовый уровень в логике
`Game.new_game(start_level: int = 0)` запоминает `self.start_level` и ставит `level = start_level`. `scoring.level_for(total_lines, start_level=0)` возвращает `max(start_level, total_lines // 10)`, и `_lock()` передаёт стартовый уровень. Для стартовых уровней 0–9 это совпадает с правилом NES (первое повышение после (L + 1) × 10 линий).

### Настройки
`Settings` дополняется полями `language: str = "en"`, `start_level: int = 0`, `ghost: bool = True`, `autorepeat: str = "normal"` с той же поштучной проверкой при чтении. Поля хранятся в одном объекте, поэтому сохранение любой настройки пишет весь файл и ничего не теряет.

### Экраны (`layout.py`, `render.py`)

| Экран | Заголовок | Строки | Подсказка |
|---|---|---|---|
| Главное меню | «SEVA Tetris», шрифт `big`, по центру при y = 120 | пункты шрифтом `small` по центру с y = 240, шаг 50 | y = 590 |
| Рекорды | «HIGH SCORES» при y = 60 | строки таблицы с y = 130, шаг 34 | y = 590 |
| Настройки | «Settings» при y = 60 | строки «Название: значение» и «Back» с y = 130, шаг 45 | y = 590 |
| Список клавиш | «SEVA Tetris» при y = 60 | 13 строк с y = 120, шаг 34; клавиши при x = 70, действия при x = 270 | y = 600 |

- Выделение — цветом `HIGHLIGHT`.
- Пауза на поле: «PAUSE» и под ним «Continue» / «Main menu» через существующее `overlay_lines` с цветами.
- Таблица после конца игры: вместо «Press Enter» две строки — «Enter - new game» и «Esc - main menu».
- Экраны меню, как раньше экран клавиш, занимают всё окно: `render.draw` рисует их вместо поля и панели.
- Тень рисуется, только если `settings.ghost`.

### Приложение
- `app.create_controller()` создаёт контроллер с `start_in_menu=True`.
- `main()` после обработки событий проверяет `controller.quit_requested` и выходит с кодом 0, как при `QUIT`.

## Risks / Trade-offs

- [Перевод Esc и ↑ на новые `Key` затрагивает тесты таблицы клавиш] → поведение в партии прежнее (Esc = пауза, ↑ = поворот). Меняются только тесты `KEY_MAP` и заставки, которой больше нет.
- [«Main menu» с паузы теряет партию без подтверждения] → в меню паузы для этого нужно выбрать пункт стрелкой и нажать Enter, случайно это сделать трудно. Подтверждение — вне рамок.
- [Настройка языка без перевода] → до `add-russian-ui`, который реализуется следом, выбор «Русский» только сохраняется. Это зафиксировано в proposal.

## Migration Plan

В существующем `settings.json` новых полей нет, поэтому берутся значения по умолчанию, а поля звука читаются как раньше. Тесты заставки заменяются тестами меню.
