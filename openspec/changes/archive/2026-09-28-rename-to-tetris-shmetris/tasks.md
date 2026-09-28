# Tasks

## 1. Название в игре (`tetris_ui`)

- [x] 1.1 Добавить `GAME_TITLE = "Tetris Shmetris"` в `tetris_ui/__init__.py`, а `layout.TITLE`, `prog` и описание справки в `cli.parse_args()` брать из него, по design.md.

  Перевести на новое название тесты надписей и окна: `test_input.py`, `test_texts.py`, `test_ui_smoke.py`.

  Добавить тесты:
  - `layout.TITLE` равен «Tetris Shmetris»;
  - `--help` начинается с названия игры (`test_cli.py`);
  - сценарии «Запуск», «Меню при запуске», «Экран управления», «Экран клавиш по F1» и «Язык после перезапуска» проходят с новым названием.

  Убедиться, что тесты проходят.
- [x] 1.2 В `docs/interface.md` и `docs/user-guide.md` написать новое название игры в заголовках и тексте. Проверить: `tests/test_docs.py` проходит.

## 2. Сборка `tetris_shmetris.exe` (`build_exe.py`)

- [x] 2.1 Изменения в `build_exe.py` по design.md:
  - `EXE_NAME = "tetris_shmetris"` и `--name EXE_NAME`;
  - ресурс версии: `ProductName` и `FileDescription` из `GAME_TITLE`, `OriginalFilename` «tetris_shmetris.exe», `InternalName` «tetris_shmetris»;
  - `STALE_EXES` — только `dist\tetris.exe`, файлы под прежним названием не удаляются.

  Пересоздать `version_info.txt` (`write_version_file()`). Обновить ожидания в `tests/test_version.py`. Убедиться, что тесты без сборки проходят, в том числе `test_committed_version_file_is_up_to_date`.
- [x] 2.2 Обновить `tests/test_build.py`:
  - `EXE_NAME` = «tetris_shmetris.exe»;
  - перед сборкой создать `dist\tetris.exe`; после сборки его нет, а из exe в `dist\` остаётся только `tetris_shmetris.exe` (сценарий «Сборка после переименования»);
  - свойства exe: название «Tetris Shmetris» и исходное имя «tetris_shmetris.exe».

  Запустить с `TETRIS_BUILD_TEST=1`, убедиться, что тесты проходят.
- [x] 2.3 Обновить документацию:
  - `docs/build.md`: заголовок, имя файла, параметры сборки, значения ресурса версии, проверка;
  - `docs/README.md`: описание, команда сборки, таблица документов;
  - `docs/user-guide.md`: имя файла в запуске, частых вопросах и свойствах.

  Проверить: `tests/test_docs.py` проходит.

## 3. Контекст проекта, спецификации и архив

- [x] 3.1 Написать новое название и имя файла в `openspec/config.yaml` и в разделе Purpose основной спецификации `openspec/specs/game-version/spec.md` (дельта его не меняет). Проверить: `openspec validate --all --strict` без ошибок.
- [x] 3.2 Убрать прежнее название из всего проекта:
  - в основных спецификациях `openspec/specs/` и в архиве `openspec/changes/archive/` заменить его новым названием, именем exe `tetris_shmetris.exe` и файлом сборки `tetris_shmetris.spec` (design.md);
  - удалить сгенерированные файлы прежних сборок и кэши (`build\` прежней сборки, `.pytest_cache`, `__pycache__` проекта).

  Проверить:
  - поиск прежнего названия без учёта регистра по всему проекту, кроме `.git` и `.venv`, ничего не находит — ни в тексте, ни в сгенерированных и двоичных файлах, ни в именах файлов и папок;
  - `openspec validate --all --strict` без ошибок.

## 4. Проверки

- [x] 4.1 Запустить `python -m pytest` целиком, сборочный тест с `TETRIS_BUILD_TEST=1` и `openspec validate rename-to-tetris-shmetris --strict`, всё без ошибок. После прогона снова выполнить поиск из 3.2: он ничего не находит.
- [x] 4.2 Вручную:
  - заголовок окна, главного меню и списка клавиш (Controls и F1) — «Tetris Shmetris» на обоих языках;
  - после сборки в `dist\` только `tetris_shmetris.exe`, он запускается двойным щелчком;
  - в «Свойства → Подробно» название продукта «Tetris Shmetris» и исходное имя «tetris_shmetris.exe»;
  - рекорды и настройки прежние;
  - поиск прежнего названия в PyCharm по всему проекту ничего не находит.
