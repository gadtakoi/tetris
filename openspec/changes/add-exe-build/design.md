# Design

## Context

Игра запускается через `tetris_ui/__main__.py`, который вызывает `app.main()`. `main(max_frames=None)` уже умеет останавливаться после N кадров: сейчас этим пользуются только тесты. Все ресурсы встроены: шрифт — `pygame.font.Font(None, ...)`, то есть `freesansbold.ttf` из пакета pygame-ce, а звук по плану `add-sound` синтезируется в коде. Окружение: Python 3.14.3, pygame-ce 2.5.8, на PyPI есть PyInstaller 6.22.3. Мотивация описана в proposal.md, требования — в `specs/distribution`.

## Goals / Non-Goals

**Goals:**
- Воспроизводимая сборка одной командой, без ручного редактирования `.spec`.
- Автоматическая проверка, что собранный exe действительно запускается, а не только собирается.

**Non-Goals:**
- Минимизация размера exe (UPX и т. п.).
- Сборка в CI: проверка запускается локально по переменной окружения.

## Decisions

### PyInstaller `--onefile --windowed`
`build_exe.py` вызывает `PyInstaller.__main__.run([...])` с параметрами `launcher.py --onefile --windowed --name tetris --clean --noconfirm --distpath dist --workpath build`. Файл `.spec` генерируется при каждой сборке и игнорируется git.

Альтернативы:
- Nuitka: компиляция в C, быстрее запуск, но нужен компилятор C и дольше сборка.
- cx_Freeze: нет удобного однофайлового режима.

У PyInstaller есть готовый хук для pygame-ce: пакет сам поставляет `pygame/__pyinstaller`, который добавляет DLL SDL и `freesansbold.ttf`.

### Точка входа `launcher.py` в корне
PyInstaller принимает путь к скрипту. `tetris_ui/__main__.py` как скрипт запускается без контекста пакета, а относительных импортов у нас нет, но отдельный `launcher.py` делает точку входа явной. Назвать его `tetris.py` нельзя: имя совпало бы с пакетом `tetris`. Содержимое:
```python
from tetris_ui.cli import run
raise SystemExit(run())
```

### `tetris_ui/cli.py`
`run(argv: list[str] | None = None) -> int` разбирает `--max-frames` через `argparse` с типом «целое ≥ 1»: при ошибке `argparse` завершает процесс с кодом 2. Затем возвращает `app.main(max_frames=...)`. `__main__.py` вызывает то же самое. В оконном exe у `argparse` нет консоли для сообщения об ошибке, но код возврата всё равно ненулевой, и этого достаточно для автоматической проверки.

### Безопасный stderr
В `--windowed` exe `sys.stderr` равен `None`, и `print(..., file=sys.stderr)` бросает исключение. Поэтому добавляется функция `tetris_ui.cli.warn(message)`, которая ничего не делает при `sys.stderr is None`. Все предупреждения интерфейса идут через неё (например, неудачное сохранение рекордов в `storage.save`, если `add-high-scores` уже реализован).

### Проверка собранного exe
`tests/test_build.py` помечен `pytest.mark.skipif(os.environ.get("TETRIS_BUILD_TEST") != "1")`:
1. запускает `python build_exe.py` (таймаут 10 минут);
2. копирует `dist\tetris.exe` в пустую временную папку;
3. запускает его с `--max-frames 30`, `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy` и `TETRIS_DATA_DIR` во второй временной папке (таймаут 30 с);
4. проверяет код 0 и что в папке с exe остался только `tetris.exe`.

Обычный `pytest` сборку не запускает, потому что она занимает минуты.

## Risks / Trade-offs

- [PyInstaller может не поддерживать Python 3.14 или хук pygame-ce может не подойти к нему] → задача 1.1 первой проверяет сборку минимального варианта. При неудаче фиксируем рабочие версии в `requirements-build.txt` или собираем из отдельного `.venv` на Python 3.13.
- [Однофайловый exe распаковывается во временную папку при каждом запуске: старт на 1–3 с медленнее] → принятая цена за один файл (выбор пользователя).
- [Антивирусы иногда помечают однофайловые PyInstaller-сборки] → для личного использования достаточно. Для распространения потом рассматриваются подпись и `--onedir` (вне рамок).
- [Сообщение `argparse` об ошибке не видно в оконном exe] → параметр служебный, для игрока он не нужен.

## Migration Plan

Не требуется: добавляются новые файлы. Для отката удаляются `build_exe.py`, `launcher.py`, `requirements-build.txt` и `tetris_ui/cli.py`, а `__main__.py` возвращается к прямому вызову `main()`.
