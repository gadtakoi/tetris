# Spec Delta

## MODIFIED Requirements

### Requirement: Запуск без Python
`SEVA Tetris.exe` SHALL запускаться двойным щелчком на Windows 10/11 x64, на которой не установлен Python, SHALL открывать окно игры без окна консоли и SHALL давать то же поведение, что `python -m tetris_ui`, включая шрифты, звук и сохранение рекордов, если они реализованы к моменту сборки.

#### Scenario: Двойной щелчок
- **WHEN** пользователь дважды щёлкает `SEVA Tetris.exe`
- **THEN** открывается окно «SEVA Tetris» с главным меню, окно консоли не появляется
