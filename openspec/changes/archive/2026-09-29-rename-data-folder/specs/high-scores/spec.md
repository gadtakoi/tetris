# Spec Delta

## MODIFIED Requirements

### Requirement: Хранение таблицы
Таблица SHALL храниться в файле `highscores.json` в папке `tetris_shmetris` внутри папки данных пользователя: `%APPDATA%` на Windows, `~/.local/share` на других ОС. Файл SHALL быть в кодировке UTF-8 и содержать JSON-объект `{"version": 1, "entries": [...]}`, где каждая запись — объект с полями `name` (строка), `score`, `lines`, `level` (неотрицательные целые). Таблица SHALL сохраняться сразу после добавления новой записи; запись файла SHALL быть атомарной (через временный файл), чтобы прерванное сохранение не портило прежнюю таблицу. Прежнюю папку `tetris` (`%APPDATA%\tetris`) игра SHALL NOT читать, изменять и удалять.

#### Scenario: Сохранение и загрузка
- **WHEN** в таблицу добавлен результат «Иван», 1200 очков, 13 линий, уровень 1, и игра запускается снова
- **THEN** загруженная таблица содержит эту запись с теми же значениями

#### Scenario: Первый запуск
- **WHEN** файла `highscores.json` нет
- **THEN** таблица пустая, и файл создаётся (вместе с папкой) при первом сохранении

#### Scenario: Папка данных
- **WHEN** `%APPDATA%` — это `C:\Users\Player\AppData\Roaming`, и сохраняется рекорд
- **THEN** таблица записана в `C:\Users\Player\AppData\Roaming\tetris_shmetris\highscores.json`

#### Scenario: Прежняя папка не читается
- **WHEN** в `%APPDATA%\tetris` лежит `highscores.json` с записями, в `%APPDATA%\tetris_shmetris` этого файла нет, и игра запускается
- **THEN** таблица пустая, а `%APPDATA%\tetris\highscores.json` не изменён
