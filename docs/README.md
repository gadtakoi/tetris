# Tetris Shmetris — документация

Tetris Shmetris — классический тетрис для Windows, macOS и Linux на Python 3.14 и pygame-ce: поле 10 × 20, семь фигур, очки и уровни по правилам NES, тень и жёсткое падение, таблица рекордов, синтезированные звуки и музыка, главное меню с настройками (стартовый уровень, тень, скорость автоповтора, звук). Игру можно запускать из исходников или готовой сборкой: `tetris_shmetris.exe` для Windows, `tetris_shmetris.app` для macOS или файлом `tetris_shmetris` для Linux.

## Быстрый старт

Все команды выполняются из корня проекта, в виртуальном окружении `.venv`.

| Что сделать | Команда |
|---|---|
| Установить зависимости игры и тестов | `.venv\Scripts\python -m pip install -r requirements.txt` |
| Запустить игру | `.venv\Scripts\python -m tetris_ui` |
| Проверить звуки: прослушать по очереди и отметить неприятные | `.venv\Scripts\python -m tetris_ui --sound-check` |
| Запустить тесты | `.venv\Scripts\python -m pytest` |
| Собрать игру для своей системы (`dist\tetris_shmetris.exe`, `.app` или файл Linux) | `.venv\Scripts\python -m pip install -r requirements-build.txt`, затем `.venv\Scripts\python build_exe.py` |
| Проверить сборку автотестом (долго) | `set TETRIS_BUILD_TEST=1` и `.venv\Scripts\python -m pytest tests/test_build.py` |
| Выпустить релиз на GitHub | `git tag v<версия>` и `git push origin v<версия>`, подробнее — [build.md](build.md#релиз-на-github) |

## Документы

| Документ | О чём |
|---|---|
| [user-guide.md](user-guide.md) | Инструкция для игрока: запуск, меню, управление, правила, настройки, рекорды, частые вопросы |
| [architecture.md](architecture.md) | Пакеты и модули, их зависимости, что происходит за один кадр, фазы экрана, где хранятся данные |
| [game-logic.md](game-logic.md) | Правила игры по коду: поле, фигуры, вращение, команды, фиксация, линии, очки, уровни, гравитация, конец игры, рекорды |
| [interface.md](interface.md) | Управление и автоповтор, главное меню и экран настроек, список клавиш, меню паузы, экран конца игры, раскладка экрана, звук, проверка звуков, хранение настроек |
| [build.md](build.md) | Сборка для Windows, macOS и Linux, её проверка, релизы на GitHub и известные ограничения |

## Структура проекта

```
tetris/          логика игры: чистый Python, без pygame и без файлов
tetris_ui/       интерфейс: окно, ввод, отрисовка, звук, хранение данных
tests/           автотесты pytest
docs/            эта документация
openspec/        спецификации (specs/) и история изменений (changes/archive/)
build_exe.py     сборка через PyInstaller для своей системы
launcher.py      точка входа сборки
release_notes.py текст релиза GitHub из CHANGELOG.md
.github/         workflow релиза: сборки для трёх систем по тегу v<версия>
version_info.txt ресурс версии exe (обновляет build_exe.py из tetris_ui.__version__)
```

## Документация и спецификации

Эти документы объясняют, как устроена программа и почему она устроена именно так. Точное нормативное поведение — с числами и сценариями — описано в спецификациях OpenSpec в [openspec/specs](../openspec/specs); при расхождении правы спецификации и тесты.

Изменения в проекте делаются через OpenSpec: предложение (`/opsx:propose`), реализация (`/opsx:apply`), архивирование (`/opsx:archive`). Если изменение меняет устройство программы, оно обновляет и эти документы.
