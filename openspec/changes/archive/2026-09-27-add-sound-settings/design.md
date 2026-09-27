# Design

## Context

Состояние звука сейчас живёт в `Controller`: атрибуты `music_on` и `sound_on` меняет `_toggle()`, счётчик `music_generation` растёт при включении музыки. `Audio.sync()` каждый кадр читает эти поля и `music_state`. Громкость канала музыки задана константой `MUSIC_VOLUME = 0.5` в `audio.py`. Файлы данных пишет `tetris_ui/storage.py`: таблица рекордов лежит в `data_dir()` (`TETRIS_DATA_DIR`, иначе `%APPDATA%\tetris`), запись атомарная через временный файл. Проверено на pygame-ce 2.5.8: `Channel.play()` не сбрасывает громкость канала, но SDL хранит громкость с шагом 1/128 (0,7 → 0,695). Мотивация описана в proposal.md, требования — в дельтах `audio`, `controls` и `game-screen`.

## Goals / Non-Goals

**Goals:**
- Правила настроек (значения по умолчанию, проверка полей, шаг громкости, JSON) — чистые функции без pygame и без файлов.
- Одна точка правды для звука в `Controller`: панель, аудиослой и сохранение читают одно и то же значение.

**Non-Goals:**
- Общий механизм настроек для будущих опций. Добавим, когда появится вторая группа настроек.

## Decisions

### `tetris_ui/settings.py`
```python
VOLUME_STEP = 10
MAX_VOLUME = 100
DEFAULT_VOLUME = 50
FORMAT_VERSION = 1

@dataclass(frozen=True)
class Settings:
    music_on: bool = True
    sound_on: bool = True
    music_volume: int = DEFAULT_VOLUME

    def with_volume_step(self, steps: int) -> Settings  # ±1 шаг, с ограничением 0..100
    def to_json(self) -> str
    @classmethod
    def from_json(cls, text: str) -> Settings        # не бросает
```
`from_json`: некорректный JSON, не объект или `version != 1` дают `Settings()`. Иначе поле берётся, если оно корректно: `type(x) is bool` для флагов, `type(x) is int` и `0 <= x <= 100` и `x % 10 == 0` для громкости. Некорректное поле заменяется значением по умолчанию. Модуль лежит в `tetris_ui/`: это настройки интерфейса, а не правила игры, поэтому пакет `tetris/` они не трогают.

### Хранение (`tetris_ui/storage.py`)
Код атомарной записи из `save()` выносится в `_write_atomic(path, text) -> bool`: временный файл в той же папке, затем `os.replace`, при `OSError` — `warn()` и `False`. На нём держатся `save()` (рекорды) и новая `save_settings()`. Добавляются `settings_path() = data_dir() / "settings.json"` и `load_settings(path) -> Settings` (`OSError` или `UnicodeDecodeError` дают `Settings()`).

### `Controller` владеет настройками
- Новые параметры конструктора: `settings: Settings | None = None` и `on_settings_change: Callable[[Settings], object] | None = None`.
- `music_on`, `sound_on` и `music_volume` становятся свойствами только для чтения поверх `self.settings`, поэтому `layout` и `audio` продолжают работать без изменений в месте чтения.
- `_toggle()` и новые `Key.VOLUME_DOWN` / `Key.VOLUME_UP` заменяют `self.settings` новым неизменяемым объектом через `dataclasses.replace` / `with_volume_step` и вызывают `on_settings_change(self.settings)`, если значение действительно изменилось. Нажатие `+` на 100 % ничего не пишет.
- Клавиши громкости обрабатываются в той же ветке, что и M/N: во всех фазах, кроме `NAME_ENTRY`. Символ `-` при вводе имени приходит отдельным событием `TEXTINPUT` и добавляется к имени, как сейчас.
- Если музыка выключена в сохранённых настройках, `music_state` сразу `"stopped"`. `music_generation` меняется, как раньше, только при включении музыки и новой партии.

Альтернатива — отдельный объект «менеджер настроек», который сам пишет файл. Тогда `Controller` зависел бы от файловой системы, а сейчас сохранение — внешний обратный вызов, как `on_save` для рекордов, и в тестах его легко заменить списком.

### Громкость в аудиослое
`Audio.sync()` вычисляет `volume = controller.music_volume / 100` и вызывает `channel.set_volume(volume)`, только когда значение отличается от последнего выставленного. Первый `sync` выставляет его всегда. Константа `MUSIC_VOLUME` удаляется: 50 % по умолчанию дают ту же громкость 0,5, что и раньше. Мелодия не перезапускается, потому что `music_generation` от громкости не зависит.

### Приложение и экран
- `app.create_controller() -> Controller` собирает `Game`, таблицу и настройки из `storage` и подключает оба обратных вызова. `main()` вызывает её, а тесты проверяют загрузку и сохранение через `TETRIS_DATA_DIR`, не открывая окна.
- `KEY_MAP`: `K_MINUS`, `K_KP_MINUS` → `VOLUME_DOWN`; `K_EQUALS`, `K_PLUS`, `K_KP_PLUS` → `VOLUME_UP`.
- `layout.panel_texts`: строки `MUSIC ON/OFF` (y = 470), `VOLUME n%` (y = 500), `SOUND ON/OFF` (y = 530). Всё помещается над нижней границей окна 640 при шрифте 32 px.

## Risks / Trade-offs

- [Шаг громкости SDL 1/128 не даёт точно 0,7] → спецификация допускает отклонение в один шаг микшера, тест сравнивает с допуском `1/128`.
- [Частые нажатия пишут файл при каждом изменении] → файл меньше 100 байт, запись атомарная. Нажатий единицы в минуту, так что накопление записей не нужно.
- [Два экземпляра игры перезаписывают настройки друг друга] → последняя запись побеждает, как и у рекордов.

## Migration Plan

У существующих игроков файла `settings.json` ещё нет, поэтому при первом запуске действуют значения по умолчанию, как и сейчас. Для отката достаточно удалить модуль и строки подключения. Оставшийся `settings.json` ничему не мешает.
