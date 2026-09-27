# Tasks

## 1. Инструменты сборки

- [ ] 1.1 Создать `requirements-build.txt` с `pyinstaller>=6.16` и установить в `.venv`. Проверить: `.venv\Scripts\python -m PyInstaller --version` печатает версию. Если PyInstaller не ставится или не поддерживает Python 3.14, остановиться и согласовать сборку из `.venv` на Python 3.13

## 2. Точка входа (`tetris_ui/cli.py`, `launcher.py`)

- [ ] 2.1 Реализовать `cli.run(argv)` с `--max-frames` (целое ≥ 1) и `cli.warn(message)`, безопасную при `sys.stderr is None`; перевести `tetris_ui/__main__.py` на `run()`; создать `launcher.py`. Если в проекте есть вывод предупреждений в stderr (например, `storage.save`), перевести его на `warn`
- [ ] 2.2 Написать `tests/test_cli.py`: `run(["--max-frames", "3"])` под драйвером `dummy` возвращает 0; `--max-frames 0` и `--max-frames abc` дают `SystemExit` с ненулевым кодом до создания окна (проверить, что `pygame.display.get_init()` ложно); `warn` не падает при подменённом `sys.stderr = None`; `python -m tetris_ui --max-frames 3` в подпроцессе с `SDL_VIDEODRIVER=dummy` завершается с кодом 0. Убедиться, что тесты проходят

## 3. Сборка (`build_exe.py`)

- [ ] 3.1 Реализовать `build_exe.py` по design.md (`--onefile --windowed --name tetris --clean --noconfirm`, `launcher.py`, возврат кода PyInstaller). Выполнить сборку и проверить, что появился `dist\tetris.exe`, а `build/`, `dist/` и `tetris.spec` не видны в `git status`
- [ ] 3.2 Написать `tests/test_build.py` (пропускается без `TETRIS_BUILD_TEST=1`) по design.md: сборка, копия exe в пустую папку, запуск с `--max-frames 30` и драйверами `dummy`, код 0 не дольше 30 с, рядом с exe ничего не создано. Запустить с `TETRIS_BUILD_TEST=1` и убедиться, что тест проходит

## 4. Интеграционные проверки

- [ ] 4.1 Запустить `python -m pytest` целиком (сборка пропускается) и `openspec validate add-exe-build --strict`, оба без ошибок
- [ ] 4.2 Вручную: дважды щёлкнуть `dist\tetris.exe` — открывается окно без консоли, игра работает целиком (включая звук и рекорды, если реализованы), рекорд сохраняется в `%APPDATA%\tetris\`; по возможности проверить на компьютере без Python
