# Tasks

## 1. Порядок изменений и спецификация

- [ ] 1.1 Проверить, что `rename-data-folder` архивирован: `openspec list` его не показывает, а в `openspec/specs/high-scores/spec.md` требование «Хранение таблицы» называет папку `tetris_shmetris`. Если он ещё активен, остановиться и сказать об этом игроку, ничего не меняя (см. design.md, «Риски»).
- [ ] 1.2 Добавить в `specs/high-scores/spec.md` раздел MODIFIED «Хранение таблицы». Для этого скопировать требование целиком из основной спецификации и заменить `{"version": 1, "entries": [...]}` описанием формата со ссылкой на требование «Подпись таблицы». Проверить: `openspec validate add-signed-highscores --strict` проходит.

## 2. Записи таблицы без обёртки файла (`tetris/highscores.py`)

- [ ] 2.1 Заменить `to_json()`, `from_json()` и `FORMAT_VERSION` на `HighScores.to_records()` и `HighScores.from_records(raw)` по design.md (с docstring). Правила разбора остаются прежними: пропуск некорректных записей, устойчивая сортировка, не более 10 записей. В `tests/test_highscores.py` перевести тесты JSON на записи: круговое преобразование, некорректная запись пропускается, не список даёт пустую таблицу, записи сверх 10 отбрасываются. Проверить: `pytest tests/test_highscores.py tests/test_architecture.py tests/test_docstrings.py` проходит.
- [ ] 2.2 В `docs/game-logic.md` написать, что логика отдаёт и принимает список записей, а формат файла и подпись — забота `tetris_ui/storage.py`. Проверить: `pytest tests/test_docs.py` проходит.

## 3. Подпись (`tetris_ui/signing.py`)

- [ ] 3.1 Создать `tetris_ui/signing.py` с `KEY`, `signature()` и `is_valid()` по design.md. Ключ сгенерировать один раз через `secrets.token_bytes(32).hex()`. В docstring написать, что смена ключа или канонического вида требует нового номера формата. Тесты в новом `tests/test_signing.py`:
  - подпись — 64 символа `0-9a-f`;
  - зафиксированная подпись для ID `0123456789abcdef0123456789abcdef` и одной записи «A», 100, 1, 0;
  - другой ID, изменённое поле любой записи, переставленные записи, лишняя запись — подпись другая;
  - порядок ключей в записи не влияет на подпись;
  - `is_valid` ложна для `None`, числа и подписи в верхнем регистре.

  Проверить: `pytest tests/test_signing.py tests/test_docstrings.py` проходит.

## 4. Файлы `install-id` и `highscores.json` version 2 (`tetris_ui/storage.py`, `tetris_ui/app.py`)

- [ ] 4.1 Добавить `INSTALL_ID_FILE`, `install_id_path()` и `load_install_id(path)` по design.md. Тесты в `tests/test_storage.py`:
  - нет файла → создан файл с 32 символами `0-9a-f`;
  - верный ID с переводом строки → возвращён без изменений, файл не переписан;
  - «hello» → файл заменён новым ID;
  - запись не удалась (путь внутри файла вместо папки) → ID всё равно возвращён, исключения нет.

  Проверить: `pytest tests/test_storage.py` проходит.
- [ ] 4.2 Перевести `storage.load(path, install_id)` и `storage.save(scores, path, install_id)` на формат `version: 2` с `sig` и предупреждением по design.md. Тесты в `tests/test_storage.py` по сценариям «Подпись таблицы» и «Неподтверждённая таблица»:
  - сохранение и загрузка;
  - формат файла;
  - переформатирование (`json.dumps` с `indent=4` и `sort_keys=True`);
  - правка очков;
  - другой ID;
  - файл `version: 1`;
  - удалённый `sig`;
  - новый рекорд после подделки;
  - файл не меняется при загрузке;
  - предупреждение попадает в stderr (`capsys`).

  Прежние тесты (`test_save_and_load`, повреждённый и недекодируемый файл) обновить под новые сигнатуры. Проверить: `pytest tests/test_storage.py` проходит.
- [ ] 4.3 В `app.create_controller()` получить ID через `storage.load_install_id(storage.install_id_path())` и передать его в `storage.load()` и `on_save`. Убедиться, что `run_sound_check()` не создаёт `install-id`. Тест в `tests/test_cli.py` или `tests/test_ui_smoke.py`: после запуска игры с `--max-frames` в `TETRIS_DATA_DIR` есть `install-id`, после `--sound-check` его нет. Проверить: `pytest tests/test_cli.py tests/test_ui_smoke.py` проходит.
- [ ] 4.4 Обновить документацию:
  - `docs/architecture.md`: модуль `tetris_ui/signing.py` в таблице модулей, файл `install-id` и подпись в разделе «Данные на диске»;
  - `docs/interface.md`, «Хранение данных»: формат `{"version": 2, "entries": [...], "sig": ...}`, файл `install-id`, пустая таблица с предупреждением при неверной подписи;
  - `docs/user-guide.md`, «Где хранятся данные»: строка `install-id` в таблице файлов; правка `highscores.json` вручную сбрасывает таблицу; для переноса рекордов копировать оба файла; удаление `install-id` тоже сбрасывает рекорды; после обновления до этой версии таблица начинается пустой;
  - `openspec/config.yaml`: раздел «Архитектура» (файл `install-id`, подпись таблицы).

  Проверить: `pytest tests/test_docs.py` проходит.

## 5. Проверка целиком

- [ ] 5.1 Прогнать `pytest` полностью, а при установленных зависимостях сборки — ещё и `TETRIS_BUILD_TEST=1 pytest tests/test_build.py`. Вручную с `TETRIS_DATA_DIR` во временной папке:
  1. сыграть партию и записать рекорд;
  2. перезапустить игру и увидеть его в таблице;
  3. поменять очки в `highscores.json` блокнотом;
  4. перезапустить и увидеть пустую таблицу и предупреждение в консоли.
