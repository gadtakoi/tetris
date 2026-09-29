# Сборка для Windows, macOS и Linux

Игру «Tetris Shmetris» можно собрать так, чтобы она запускалась без установленного Python:

| Система | Что получается | Где работает |
|---|---|---|
| Windows | один файл `dist\tetris_shmetris.exe` (около 15 МБ) | Windows 10/11 x64 |
| macOS | приложение `dist/tetris_shmetris.app` | macOS на Apple silicon (M1 и новее) |
| Linux | один файл `dist/tetris_shmetris` (около 17 МБ) | Linux x86_64 с glibc 2.35 и новее (Ubuntu 22.04 и новее) |

PyInstaller собирает только для той системы, на которой запущен, поэтому каждую сборку делают на своей системе. Все три делает GitHub Actions (см. «Релиз на GitHub»).

## Как собрать

Windows:

```bat
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-build.txt
.venv\Scripts\python build_exe.py
```

macOS и Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt -r requirements-build.txt
.venv/bin/python build_exe.py
```

`requirements-build.txt` содержит только PyInstaller: он нужен для сборки, но не для игры и тестов, поэтому отделён от `requirements.txt`.

Сборка занимает около 20–30 секунд. Промежуточные файлы попадают в `build/` и `tetris_shmetris.spec`; как и `dist/`, они игнорируются git. Файл `dist\tetris.exe` от самых первых сборок, когда у игры ещё не было своего названия, удаляется после успешной сборки (`STALE_EXES`); другие файлы под прежними именами сборка не трогает.

## Как устроена сборка

- `build_exe.py` запускает PyInstaller с параметрами `--name tetris_shmetris --clean --noconfirm` (каждый раз с чистого листа) и параметрами своей системы (`build_exe.pyinstaller_args()`):
  - **Windows** — `--onefile --windowed` и `--version-file` (см. «Версия»): один файл, без окна консоли;
  - **macOS** — `--onedir --windowed --osx-bundle-identifier io.github.gadtakoi.tetris-shmetris`: приложение `.app`. Однофайловое `.app` PyInstaller больше не поддерживает. Рядом с `.app` в `dist/` остаётся папка `tetris_shmetris/`, из которой оно сделано; она не нужна;
  - **Linux** — `--onefile`: один исполняемый файл. `--windowed` на Linux ничего не меняет, поэтому не передаётся.
- Скрипт возвращает 0 только если результат (`build_exe.built_path()`) действительно появился. Имя файла задаёт `build_exe.EXE_NAME`, а название игры в ресурсе версии и в `Info.plist` — `tetris_ui.GAME_TITLE`.
- **macOS: `Info.plist` и подпись.** PyInstaller пишет в `Info.plist` версию 0.0.0, поэтому после сборки `build_exe.finish_app()` записывает туда название «Tetris Shmetris» и версию из `__version__` (`build_exe.app_info()`) и заново подписывает приложение ad hoc (`codesign --force --sign -`), как это делает PyInstaller: подпись покрывает `Info.plist`, а на Apple silicon приложение с неверной подписью не запускается. Подписи разработчика Apple и нотаризации нет (см. «Известные ограничения»).
- Точка входа — `launcher.py`, который вызывает `tetris_ui.cli.run()`, как и `python -m tetris_ui`. Имя `tetris.py` для него не подходит: оно совпало бы с пакетом `tetris`.
- pygame-ce поставляет собственный хук PyInstaller, поэтому библиотеки SDL попадают в exe автоматически. Звуки синтезируются в коде.
- **Иконка.** Логотип игры лежит в `tetris_ui/icon.png` (1024 × 1024, углы прозрачные). Он сделан один раз из `shmetris.png` в корне проекта: белые углы за скруглённой плиткой стали прозрачными. `build_exe.py` при каждой сборке делает из него `.ico` с размерами 16, 24, 32, 48, 64, 128 и 256 px (`build_exe.icon_ico_bytes()`, через pygame, без Pillow) во временной папке и передаёт PyInstaller `--icon` — это иконка exe в Проводнике. На macOS так же делается `.icns` с размерами от 16 до 1024 px (`build_exe.icon_icns_bytes()`, `build_exe.ICNS_TYPES`) — иконка приложения в Finder и Dock. У исполняемого файла Linux своей иконки нет. Сам `icon.png` тоже попадает в сборку (`--add-data`, `build_exe.ICON_DATA`): `tetris_ui.app.create_window()` ставит его иконкой окна (заголовок и панель задач), уменьшив до 32 px, — так и при запуске из исходников.
- Кроме иконки, файлы-ресурсы — шрифты игры в `tetris_ui/fonts/`: Unbounded (SemiBold, ExtraBold) и Onest (Regular, SemiBold) и их лицензия `OFL.txt` (SIL Open Font License 1.1, её текст обязан распространяться вместе со шрифтами). `build_exe.py` передаёт PyInstaller `--add-data "<проект>/tetris_ui/fonts;tetris_ui/fonts"` (`build_exe.FONT_DATA`), поэтому внутри exe папка лежит по тому же пути относительно пакета, что и в исходниках, и `tetris_ui.render` находит шрифты рядом со своим модулем в обоих случаях. Рядом с exe ничего не появляется: при запуске onefile-сборка распаковывает всё во временную папку и удаляет её после выхода.
- Onest в Google Fonts есть только вариативным файлом (`Onest[wght].ttf`), а pygame-ce не умеет выбирать значение оси `wght`, поэтому в папке лежат статические начертания, сделанные из него один раз: `fonttools varLib.instancer Onest[wght].ttf wght=400 --update-name-table` (и `wght=600`). Unbounded взят готовыми статическими файлами из репозитория `googlefonts/unbounded`. fontTools для игры и сборки не нужен.
- В exe без консоли `sys.stderr` равен `None`, поэтому предупреждения выводятся через `cli.warn()`, который в этом случае молчит.
- Данные (рекорды, настройки) хранятся не рядом с игрой, а в `%APPDATA%\tetris_shmetris` на Windows и в `~/.local/share/tetris_shmetris` на macOS и Linux: файл или приложение можно переносить куда угодно, а рядом с ним ничего не создаётся.

## Версия

Номер версии задан в одном месте — `__version__` в `tetris_ui/__init__.py`, сейчас 3.2.0, в формате MAJOR.MINOR.PATCH. Его видно в трёх местах:
- **в игре** — надпись «v3.2.0» в правом нижнем углу главного меню;
- **в свойствах exe** — ресурс версии Windows из файла `version_info.txt` в корне проекта;
- **в свойствах приложения macOS** — `CFBundleShortVersionString` и `CFBundleVersion` в `Info.plist` (Finder → «Свойства»), их записывает `build_exe.finish_app()`.

У файла Linux свойств с версией нет.

Как устроен `version_info.txt`:
- Файл хранится в git, поэтому данные ресурса версии видны в репозитории и в его истории.
- Перед каждой сборкой `build_exe.py` заново составляет его текст из `__version__` (`version_info_text()`) и перезаписывает файл, только если текст изменился (`write_version_file()`).
- PyInstaller получает файл параметром `--version-file`.
- Обычный тест проверяет, что `version_info.txt` соответствует `__version__` и не исключён `.gitignore`.

Значения ресурса версии:
- версия файла — номер с четвёртой частью 0 (1.0.0.0);
- версия продукта — сам номер (1.0.0);
- название продукта и описание файла — «Tetris Shmetris» (`GAME_TITLE`);
- исходное имя файла — `tetris_shmetris.exe`, внутреннее имя — `tetris_shmetris`.

**Когда какую цифру менять:**
- **PATCH** (1.0.0 → 1.0.1) — только исправления ошибок;
- **MINOR** (1.0.0 → 1.1.0) — новые возможности, с которыми прежние рекорды и настройки читаются как раньше;
- **MAJOR** (1.0.0 → 2.0.0) — несовместимые изменения, например новый формат `highscores.json` или `settings.json`, который старые версии не прочитают.

Номер поднимают вручную перед сборкой версии, которую отдают игрокам; промежуточные сборки для проверки его не меняют. После нового номера сборка обновит `version_info.txt` (и напишет об этом) — закоммитьте его вместе с `tetris_ui/__init__.py`, иначе тест сообщит, что файл устарел. Проверить результат: правый щелчок по `dist\tetris_shmetris.exe` → «Свойства» → вкладка «Подробно».

## Как проверить

Автоматически — сборочный тест. Он долгий, поэтому обычный `pytest` его пропускает. Он собирает игру для той системы, на которой запущен:

```bat
set TETRIS_BUILD_TEST=1
.venv\Scripts\python -m pytest tests/test_build.py
```

```bash
TETRIS_BUILD_TEST=1 .venv/bin/python -m pytest tests/test_build.py
```

Тест собирает игру и на Windows проверяет удаление старого `tetris.exe`. Затем он копирует результат (exe, `.app` или файл Linux) в пустую временную папку, запускает его без экрана (`SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`, `--max-frames 30`) и проверяет код 0 и то, что рядом ничего не появилось. Так же он запускает сборку с `--sound-check --max-frames 30`: код 0, рядом пусто, а в папке данных только отчёт `sound-check.json`. Последний тест зависит от системы:
- **Windows** — читает свойства exe через PowerShell (`(Get-Item …).VersionInfo`) и сверяет версию файла и продукта, название и исходное имя с `tetris_ui.__version__` и надписью в главном меню;
- **macOS** — сверяет версию, название, идентификатор и исполняемый файл в `Info.plist` и проверяет подпись (`codesign --verify --strict`);
- **Linux** — пропускается.

Вручную — дважды щёлкнуть `dist\tetris_shmetris.exe` или `dist/tetris_shmetris.app`, на Linux — запустить `dist/tetris_shmetris`: открывается окно «Tetris Shmetris» с главным меню.

## Релиз на GitHub

Релизы собирает GitHub Actions — [.github/workflows/release.yml](../.github/workflows/release.yml), с Python 3.14 на трёх раннерах: `windows-latest`, `macos-latest` (Apple silicon) и `ubuntu-22.04`. Linux собирается на самой старой Ubuntu из доступных, потому что файл работает только с той версией glibc, на которой собран, или с более новой. Выпустить версию:

1. Поднять `__version__` и записать раздел `## [<версия>]` в `CHANGELOG.md` (скилл `version-changelog`), закоммитить вместе с `version_info.txt` и отправить в `master`.
2. Поставить и отправить тег `v<версия>`:
   ```bat
   git tag v3.0.0
   git push origin v3.0.0
   ```

Что делает workflow после тега:
- задача `build` идёт на каждой из трёх систем:
  - `release_notes.py` проверяет, что тег равен `v` + `__version__` и что в `CHANGELOG.md` есть раздел этой версии. Если нет, задача останавливается до сборки;
  - запускаются все тесты, затем сборочный тест (`TETRIS_BUILD_TEST=1`): он собирает игру и проверяет запуск без экрана и свойства сборки;
  - сборка упаковывается в файл релиза, рядом кладётся его контрольная сумма SHA-256 (`<файл>.sha256`), и оба сохраняются как артефакт запуска;
- задача `release` ждёт все три сборки: если хоть одна упала, релиза нет. Затем она берёт текст релиза из `CHANGELOG.md` и создаёт релиз «Tetris Shmetris <версия>» со всеми файлами.

Файлы релиза:

| Файл | Что внутри |
|---|---|
| `tetris_shmetris.exe` | игра для Windows |
| `tetris_shmetris-macos-arm64.zip` | `tetris_shmetris.app`, упакованный `ditto`: так сохраняются ссылки, права и подпись внутри приложения |
| `tetris_shmetris-linux-x86_64.tar.gz` | файл `tetris_shmetris`. Архив нужен, чтобы файл остался исполняемым: при скачивании голого файла право на запуск теряется |

Запуск вручную (Actions → Release → Run workflow) собирает и проверяет все три сборки так же, но релиз не создаёт: файлы остаются только артефактами запуска. Так можно проверить сборку перед тегом.

Проверить текст релиза локально: `.venv\Scripts\python release_notes.py v3.0.0`.

## Известные ограничения

- **Первый запуск медленнее.** Однофайловые exe и файл Linux каждый раз распаковываются во временную папку, а музыка синтезируется при запуске, поэтому окно появляется через несколько секунд.
- **Антивирусы.** Однофайловые сборки PyInstaller без цифровой подписи иногда вызывают ложные срабатывания антивирусов.
- **macOS не узнаёт разработчика.** Приложение подписано только ad hoc, без подписи разработчика Apple и нотаризации, поэтому при первом запуске скачанной игры macOS её блокирует. Как открыть — в [user-guide.md](user-guide.md).
- **Только 64-разрядные системы.** Windows x64, macOS на Apple silicon, Linux x86_64. Для Mac на Intel, Linux на ARM и 32-разрядных систем сборок нет.

Точные требования: [distribution](../openspec/specs/distribution/spec.md), [game-version](../openspec/specs/game-version/spec.md).
