# Design

## Context

После конца игры `Controller` сейчас знает только два состояния: партия и «окончено, ждём Enter». Надписи экрана формирует `layout.overlay_texts()` (список строк), `render` выводит их по центру поля. Ввод идёт через `Key` из `KEY_MAP`. Текстового ввода нет. Пакет `tetris/` не должен импортировать pygame, а ввод-вывод в нём до сих пор не использовался. Мотивация описана в proposal.md, требования — в `specs/high-scores` и дельтах `controls` и `game-screen`.

## Goals / Non-Goals

**Goals:**
- Правила таблицы (порядок, попадание, имя, разбор JSON) — чистые функции без pygame и без файлов, тестируются напрямую.
- Работа с файлом отделена и тестируется на временной папке, без записи в настоящий `%APPDATA%`.
- Порча или отсутствие файла никогда не мешает играть.

**Non-Goals:**
- Защита от одновременного запуска двух копий игры: последняя сохранившая копия побеждает.
- Миграции формата: `version` пишется ради будущего, сейчас читается только 1.

## Decisions

### `tetris/highscores.py` (логика, без ввода-вывода)
```python
MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10
DEFAULT_NAME = "PLAYER"

@dataclass(frozen=True)
class Entry: name: str; score: int; lines: int; level: int

class HighScores:
    entries: tuple[Entry, ...]
    def qualifies(self, score: int) -> bool
    def add(self, entry: Entry) -> int          # место 1..10; ValueError, если не проходит
    def to_json(self) -> str
    @classmethod
    def from_json(cls, text: str) -> HighScores  # не бросает: мусор → пустая таблица

def is_name_char(ch: str) -> bool               # ch.isalpha() or ch.isdigit() or ch in " -_"
def append_to_name(name: str, text: str) -> str # фильтр и обрезка до 10
def final_name(name: str) -> str                # strip(); пусто → PLAYER
```
Модуль лежит в `tetris/`: это правила игры (кто попадает в таблицу), а тест архитектуры сам проверит, что pygame сюда не попал. Вставка идёт после всех записей с очками ≥ новых, так что при равенстве более ранняя запись остаётся выше.

Альтернатива — держать всё в `tetris_ui/`. Тогда правила смешиваются с pygame-слоем, и их проверка требует импорта интерфейса.

### `tetris_ui/storage.py` (файл)
- `data_dir()`: переменная окружения `TETRIS_DATA_DIR`, если задана (для тестов и ручной проверки), иначе `%APPDATA%\tetris` (при наличии `APPDATA`), иначе `~/.local/share/tetris`.
- `load(path) -> HighScores`: `OSError` или `UnicodeDecodeError` → пустая таблица, иначе `HighScores.from_json`.
- `save(scores, path) -> bool`: создать папку, записать во временный файл в той же папке, затем `os.replace`. При `OSError` вернуть `False` и вывести предупреждение в stderr, но не падать: невозможность записать рекорд не должна ронять игру.

### Фазы `Controller`
```python
class Phase(Enum): PLAYING, NAME_ENTRY, TABLE
```
Пауза остаётся флагом внутри `PLAYING`. `Controller(game, scores=HighScores(), on_save=lambda s: None)`.
- После каждой команды и `update` вызывается `_check_game_over()`: при переходе `game.is_over` в `PLAYING` фаза становится `NAME_ENTRY`, если `scores.qualifies(game.score)`, иначе `TABLE`.
- `text_input(text)` в `NAME_ENTRY` делает `name = append_to_name(name, text)`. `Key.BACKSPACE` отрезает последний символ.
- `Key.RESTART`: в `NAME_ENTRY` вызывает `scores.add(...)`, запоминает `highlight` (место), вызывает `on_save(scores)` и переходит в `TABLE`; в `TABLE` вызывает `game.new_game()`, сбрасывает `highlight` и переходит в `PLAYING`.
- В `NAME_ENTRY` и `TABLE` все остальные `Key` игнорируются, поэтому P/Z/X, которые как `KEYDOWN` превращаются в `PAUSE`/`ROTATE_*`, ничего не делают, а их символы приходят отдельным событием `TEXTINPUT`.

Один Enter не может и подтвердить имя, и перезапустить: обработка идёт по фазе на момент нажатия.

### pygame-слой
- `app.main` загружает таблицу из `storage.data_dir() / "highscores.json"`, передаёт `on_save=lambda s: storage.save(s, path)`, вызывает `pygame.key.start_text_input()`.
- `handle_event`: `TEXTINPUT` → `controller.text_input(event.text)`, `K_BACKSPACE` → `Key.BACKSPACE`.
- `layout.overlay_lines(controller) -> list[tuple[str, Color]]` заменяет `overlay_texts`, а `screen_texts` берёт из неё строки. Строки таблицы — `f"{place}. {name} {score}"`, цвет выделения `HIGHLIGHT = (240, 240, 0)`.
- `render`: «GAME OVER» крупным шрифтом, остальные строки шрифтом 26 px с шагом 28 px, начиная от верхней трети поля. Так 10 строк таблицы и подсказка помещаются в поле 300 × 600, а имя из 10 широких символов и 7-значные очки укладываются в ширину.

## Risks / Trade-offs

- [`TEXTINPUT` может не приходить при некоторых раскладках или IME] → `start_text_input()` вызывается явно. Буквы в `KEY_MAP` не используются для ввода, поэтому раскладка определяет символы правильно (кириллица работает).
- [Имя из 10 символов «Ш» шире строки] → шрифт таблицы 26 px, в дымовом тесте проверяется, что строка «10. ШШШШШШШШШШ 9999999» помещается в ширину поля.
- [Два экземпляра игры перезаписывают таблицу друг друга] → принято (см. Non-Goals).

## Migration Plan

Файла таблицы у пользователей ещё нет, первый запуск создаёт его при первом рекорде. Для отката достаточно удалить модули. Оставшийся `highscores.json` ничему не мешает.
