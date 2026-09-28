# Spec Delta

## MODIFIED Requirements

### Requirement: Окно
Игра SHALL запускаться командой `python -m tetris_ui` и открывать окно клиентской области 520 × 640 пикселей с заголовком «Tetris Shmetris». Экран SHALL перерисовываться с частотой не выше 60 кадров в секунду. После запуска SHALL показываться заставка (см. «Экран клавиш»), а новая партия SHALL начинаться по Enter.

#### Scenario: Запуск
- **WHEN** выполняется `python -m tetris_ui`
- **THEN** открывается окно 520 × 640 пикселей с заголовком «Tetris Shmetris», на нём заставка, и после нажатия Enter начинается новая партия

## ADDED Requirements

### Requirement: Экран клавиш
На заставке и на экране клавиш, открытом по F1, SHALL показываться на всё окно: фон окна, заголовок «Tetris Shmetris», таблица горячих клавиш из 11 строк и нижняя подсказка. Каждая строка таблицы SHALL состоять из названия клавиш (левый столбец) и действия (правый столбец):

| Клавиши | Действие |
|---|---|
| Left / Right | Move |
| Down | Soft drop |
| Space | Hard drop |
| Up / X | Rotate right |
| Z / Ctrl | Rotate left |
| P / Esc | Pause |
| F1 | Help |
| M | Music on/off |
| - / + | Music volume |
| N | Sound on/off |
| Enter | Start / restart |

Нижняя подсказка SHALL быть «Press Enter to start» на заставке и «Press F1 or Enter to return» на экране клавиш. Все надписи экрана клавиш SHALL состоять только из символов ASCII. Поле, фигуры и боковая панель SHALL NOT рисоваться, пока показан экран клавиш; после его закрытия они SHALL рисоваться как прежде.

#### Scenario: Заставка
- **WHEN** игра только запущена
- **THEN** на экране показаны «Tetris Shmetris», все 11 строк таблицы (например, «Space» — «Hard drop» и «- / +» — «Music volume») и «Press Enter to start», а надписи «SCORE» и «NEXT» не показаны

#### Scenario: Экран клавиш по F1
- **WHEN** во время партии нажата F1
- **THEN** на экране показаны «Tetris Shmetris», таблица горячих клавиш и «Press F1 or Enter to return»

#### Scenario: Возврат к полю
- **WHEN** экран клавиш закрыт
- **THEN** снова показаны поле с фигурами и боковая панель с «SCORE» и «NEXT»
