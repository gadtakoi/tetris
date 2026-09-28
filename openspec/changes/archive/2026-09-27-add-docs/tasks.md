# Tasks

## 1. Описания функций (docstring)

- [x] 1.1 Написать `tests/test_docstrings.py` по design.md (модули, классы, функции и методы в `tetris/`, `tetris_ui/`, `build_exe.py`, `launcher.py`; кроме `__init__`; при падении — список `файл:строка имя`). Убедиться, что тест падает и перечисляет текущие пропуски
- [x] 1.2 Добавить docstring во все модули пакета `tetris/` по стилю design.md. Проверить: `python -m pytest` зелёный, кроме ещё не закрытых мест `tetris_ui/`
- [x] 1.3 Добавить docstring во все модули `tetris_ui/`, `build_exe.py` и `launcher.py`. Убедиться, что `tests/test_docstrings.py` и весь `python -m pytest` зелёные, а `git diff` в коде затрагивает только docstring

## 2. Документация (`docs/`)

- [x] 2.1 Написать `docs/README.md` и `docs/architecture.md` (схемы Mermaid: зависимости пакетов, кадр игрового цикла, фазы экрана; таблица модулей). Сверить имена модулей, функций и фаз с текущим кодом
- [x] 2.2 Написать `docs/game-logic.md`, сверив числа (размеры поля, позиции появления, таблицы очков и скоростей) с `openspec/specs/` и кодом
- [x] 2.3 Написать `docs/interface.md` и `docs/build.md`, сверив клавиши, фазы, пути к файлам данных и команду сборки с кодом
- [x] 2.4 Написать `tests/test_docs.py` (относительные ссылки в `docs/*.md` ведут на существующие файлы). Убедиться, что тест проходит

## 3. Контекст проекта

- [x] 3.1 Обновить `openspec/config.yaml`: название «Tetris Shmetris», заставка и экран клавиш, `settings.json`, раздел «Документация: docs/» и правило «изменения, меняющие устройство программы, обновляют docs/». Проверить: `openspec context --json` читает контекст, `openspec validate --all --strict` без ошибок

## 4. Интеграционные проверки

- [x] 4.1 Запустить `python -m pytest` целиком и `openspec validate add-docs --strict`, оба без ошибок
- [x] 4.2 Вручную прочитать `docs/`: описание соответствует игре, схемы Mermaid отображаются (например, в PyCharm или на GitHub)
