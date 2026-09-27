# Архитектура

## Главный принцип

Программа разделена на два пакета:

- **`tetris/` — логика игры.** Поле, фигуры, команды, очки, уровни, гравитация, правила таблицы рекордов. Чистый Python: без pygame, без файлов и без системных часов. Время приходит только через `Game.tick(dt_ms)`, случайность — через передаваемый `random.Random`. Поэтому логика детерминирована и полностью проверяется тестами. Тест [tests/test_architecture.py](../tests/test_architecture.py) следит, чтобы pygame сюда не попал.
- **`tetris_ui/` — интерфейс.** Окно, клавиатура, отрисовка, звук, хранение рекордов и настроек. Он только читает состояние логики и передаёт ей команды; правил игры в нём нет.

Внутри `tetris_ui/` тоже есть граница: модули `input`, `menus`, `layout`, `settings`, `synth`, `music` не импортируют pygame и тестируются напрямую, а `app`, `render`, `audio` работают с pygame и проверяются дымовыми тестами с SDL-драйверами `dummy` (без окна и без звуковой карты).

## Зависимости модулей

```mermaid
flowchart TB
    subgraph ui["tetris_ui — интерфейс"]
        main["__main__ / launcher.py"] --> cli
        cli -.->|"после разбора аргументов"| app
        app --> input & render & audio & storage & layout
        render --> layout & input
        layout --> input & menus
        input --> menus
        menus --> settings
        audio --> synth & music & input
        music --> synth
        storage --> settings & cli
        input --> settings
    end
    subgraph logic["tetris — логика, без pygame"]
        game --> board & pieces & randomizer & scoring & gravity
        board --> pieces
        randomizer --> pieces
        highscores
    end
    app --> game
    input --> highscores
    storage --> highscores
    layout --> board & pieces
    render --> board & pieces
```

Стрелки идут только из `tetris_ui` в `tetris`, обратных нет.

## Модули

| Модуль | Ответственность |
|---|---|
| `tetris/board.py` | Поле 10 × 22 (строки 0–1 скрыты): занятость клеток, удаление заполненных строк |
| `tetris/pieces.py` | Семь фигур, их ориентации, размеры рамок и позиции появления |
| `tetris/randomizer.py` | Генератор 7-bag: мешки по семь фигур |
| `tetris/game.py` | Партия: активная и следующая фигуры, команды, тень, фиксация, очки, гравитация, конец игры |
| `tetris/scoring.py` | Таблица очков за линии и расчёт уровня с учётом стартового |
| `tetris/gravity.py` | Таблица скоростей: кадров на строку по уровню |
| `tetris/highscores.py` | Правила таблицы рекордов: порядок, попадание, имя, JSON |
| `tetris_ui/input.py` | `Controller`: фазы экрана, клавиши, главное меню и его экраны, автоповтор, меню паузы, экран клавиш, ввод имени, настройки, звуковые события кадра |
| `tetris_ui/menus.py` | Пункты главного меню и меню паузы, строки экрана настроек, правила изменения настроек, предустановки автоповтора (без pygame) |
| `tetris_ui/layout.py` | Размеры, координаты и цвета, все надписи экрана (без pygame) |
| `tetris_ui/render.py` | Рисование кадра на поверхности pygame |
| `tetris_ui/app.py` | Окно, игровой цикл, перевод клавиш pygame в `Key`, сборка контроллера |
| `tetris_ui/settings.py` | Настройки игрока (звук, язык, стартовый уровень, тень, автоповтор): значения по умолчанию, проверка, JSON |
| `tetris_ui/storage.py` | Папка данных, чтение и атомарная запись `highscores.json` и `settings.json` |
| `tetris_ui/synth.py` | Синтезатор PCM на чистом Python и семь звуковых эффектов |
| `tetris_ui/music.py` | Ноты фоновой мелодии и её синтез |
| `tetris_ui/audio.py` | Проигрывание эффектов и музыки через `pygame.mixer` или тишина без устройства |
| `tetris_ui/cli.py` | Разбор `--max-frames`, безопасный вывод предупреждений |

## Один кадр

Игровой цикл — `app.main()`. Он ограничен 60 кадрами в секунду; каждый кадр проходит так:

```mermaid
sequenceDiagram
    participant App as app.main
    participant C as Controller
    participant G as Game
    participant A as Audio
    participant R as render
    App->>App: frame_ms = clock.tick(60)
    loop события pygame
        App->>C: key_down / key_up / text_input
        C->>G: команды: move_left, rotate_cw, hard_drop...
    end
    App->>C: update(frame_ms)
    C->>G: автоповтор клавиш, затем tick(min(frame_ms, 100))
    App->>A: sync(controller)
    A->>C: drain_sounds(), music_state, music_volume
    App->>R: draw(screen, controller, fonts)
    R->>C: фаза, надписи, состояние игры
    App->>App: display.flip()
```

Порядок важен: команды игрока выполняются до гравитации того же кадра, а время одного кадра ограничено 100 мс, чтобы после подвисания окна фигура не проваливалась на много строк сразу. Закрытие окна (`QUIT`) и пункт «Quit» главного меню (`Controller.quit_requested`) сразу завершают цикл с кодом 0.

## Фазы экрана

`Controller` знает, в какой фазе находится экран, и по фазе решает, что делают клавиши и что рисуется.

```mermaid
stateDiagram-v2
    [*] --> MENU
    MENU --> PLAYING: New game
    MENU --> SCORES: High scores
    MENU --> SETTINGS: Settings
    MENU --> CONTROLS: Controls
    MENU --> [*]: Quit
    SCORES --> MENU: Enter / Esc
    CONTROLS --> MENU: Enter / Esc
    SETTINGS --> MENU: Back / Esc
    state PLAYING {
        state "Партия идёт" as Running
        state "Меню паузы" as Paused
        state "Экран клавиш" as Help
        [*] --> Running
        Running --> Paused: P / Esc
        Paused --> Running: P / Esc / Continue
        Running --> Help: F1
        Paused --> Help: F1
        Help --> Running: F1 / Esc / P / Enter
    }
    PLAYING --> MENU: Main menu на паузе
    PLAYING --> NAME_ENTRY: конец игры, результат в топ-10
    PLAYING --> TABLE: конец игры, результат не в топ-10
    NAME_ENTRY --> TABLE: Enter
    TABLE --> PLAYING: Enter (новая партия)
    TABLE --> MENU: Esc
```

- **`MENU`** — главное меню при запуске: New game, High scores, Settings, Controls, Quit. Выделенный пункт — `menu_index`.
- **`SCORES`, `SETTINGS`, `CONTROLS`** — экраны меню: таблица рекордов, настройки, список клавиш. В меню и на его экранах время не идёт, музыки нет, работают только клавиши экрана и клавиши звука.
- **`PLAYING`** — партия. Пауза (`paused`) и экран клавиш (`help_open`) — состояния внутри неё: время и команды стоят, музыка на паузе. На паузе работает меню паузы (`pause_index`): «Main menu» бросает партию без записи результата.
- **`NAME_ENTRY`** — ввод имени для таблицы рекордов.
- **`TABLE`** — таблица рекордов; Enter начинает новую партию сразу, Esc открывает главное меню.

Новая партия всегда начинается со стартового уровня из настроек: `game.new_game(settings.start_level)`.

Переход из `PLAYING` при конце игры происходит в свойстве `Controller.phase`, как только `game.is_over` стал истинным.

## Звуковые события

Логика не посылает событий. Контроллер сам выводит их: запоминает перед каждой командой и перед `update` снимок `(pieces_locked, lines, level, is_over)` и сравнивает со снимком после. Выросло число зафиксированных фигур — значит, была фиксация (звук `lock`, `clear` или `tetris` по числу удалённых линий); вырос уровень — `level_up`; партия закончилась — `game_over`. Успешные сдвиг и поворот дают `move` и `rotate`. `Audio.sync()` раз в кадр забирает накопленные события и проигрывает их. Подробнее — в [interface.md](interface.md).

## Данные на диске

Все данные лежат в папке данных пользователя (`storage.data_dir()`):

| Условие | Папка |
|---|---|
| задана переменная `TETRIS_DATA_DIR` (тесты, ручные проверки) | её значение |
| Windows | `%APPDATA%\tetris` |
| иначе | `~/.local/share/tetris` |

В ней два файла: `highscores.json` (таблица рекордов) и `settings.json` (настройки звука и игры). Оба пишутся атомарно — во временный файл и затем заменой — и при повреждении читаются как пустая таблица и настройки по умолчанию. Рядом с exe игра ничего не создаёт.

## Нормативные спецификации

Поведение, описанное здесь в общих чертах, точно задано в спецификациях: [game-screen](../openspec/specs/game-screen/spec.md), [controls](../openspec/specs/controls/spec.md), [audio](../openspec/specs/audio/spec.md), [high-scores](../openspec/specs/high-scores/spec.md), [distribution](../openspec/specs/distribution/spec.md), [main-menu](../openspec/specs/main-menu/spec.md), [settings](../openspec/specs/settings/spec.md).
