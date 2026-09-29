# Tasks

## 1. Папка `tetris_shmetris`

- [x] 1.1 В `tetris_ui/storage.py` поставить `APP_DIR_NAME = "tetris_shmetris"` и назвать новую папку в docstring `data_dir()`, по design.md.

  В `tests/test_storage.py`:
  - перевести `test_data_dir_uses_appdata` и `test_data_dir_without_appdata` на `tetris_shmetris`;
  - добавить тест «Папка данных»: при `APPDATA` во временной папке и без `TETRIS_DATA_DIR` рекорды, настройки и отчёт проверки звуков лежат в `<APPDATA>\tetris_shmetris`;
  - добавить тест «Прежняя папка не читается»: в `<APPDATA>\tetris` лежат `highscores.json` с записью и `settings.json` с `"language": "ru"`. Загрузка даёт пустую таблицу и настройки по умолчанию, а после сохранения таблицы и настроек прежние файлы побайтно не изменились.

  Убедиться, что `tests/test_storage.py` и `tests/test_docstrings.py` проходят.
- [x] 1.2 Написать новую папку в документации:
  - `docs/architecture.md` — таблица «Данные на диске»;
  - `docs/interface.md` — «Хранение данных»;
  - `docs/build.md` — папка данных exe;
  - `docs/user-guide.md` — «Где хранятся данные»: папка и команда для Win + R;
  - `openspec/config.yaml` — раздел «Архитектура».

  Проверить:
  - `tests/test_docs.py` проходит;
  - поиск `%APPDATA%\tetris` и `.local/share/tetris` без продолжения `_shmetris` в `docs/`, `tetris_ui/` и `openspec/config.yaml` ничего не находит.

## 2. Проверки

- [x] 2.1 Запустить без ошибок:
  - `python -m pytest` целиком;
  - сборочный тест с `TETRIS_BUILD_TEST=1`;
  - `openspec validate rename-data-folder --strict`.
- [x] 2.2 Вручную:
  - после запуска `python -m tetris_ui` и изменения настройки появляется `%APPDATA%\tetris_shmetris\settings.json`;
  - файлы в `%APPDATA%\tetris` не изменились: время изменения и `Get-FileHash` прежние;
  - `dist\tetris_shmetris.exe` пишет в ту же папку `%APPDATA%\tetris_shmetris`.

  Итог 2026-09-29. Игра, запущенная вне приложения Claude, записала `settings.json` в `%APPDATA%\tetris_shmetris`, а файлы в `%APPDATA%\tetris` не изменились. Запись exe подтверждена косвенно: при запуске из приложения Claude exe пишет по тому же пути, но Windows перенаправляет эту запись (MSIX). Игрок принял такую проверку.
