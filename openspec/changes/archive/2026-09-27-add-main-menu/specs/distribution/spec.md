# Spec Delta

## MODIFIED Requirements

### Requirement: Запуск без Python
`tetris_shmetris.exe` SHALL запускаться двойным щелчком на Windows 10/11 x64, на которой не установлен Python, SHALL открывать окно игры без окна консоли и SHALL давать то же поведение, что `python -m tetris_ui`, включая шрифты, звук и сохранение рекордов, если они реализованы к моменту сборки.

#### Scenario: Двойной щелчок
- **WHEN** пользователь дважды щёлкает `tetris_shmetris.exe`
- **THEN** открывается окно «Tetris Shmetris» с главным меню, окно консоли не появляется
