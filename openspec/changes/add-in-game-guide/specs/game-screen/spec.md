# Spec Delta

## MODIFIED Requirements

### Requirement: Список клавиш
На экране «Controls» главного меню и на экране клавиш, открытом по F1, SHALL показываться на всё окно: фон окна, заголовок «SEVA Tetris», таблица горячих клавиш из 14 строк и нижняя подсказка. Каждая строка таблицы SHALL состоять из названия клавиш (левый столбец) и действия (правый столбец):

| Клавиши | Действие |
|---|---|
| Left / Right | Move |
| Down | Soft drop |
| Space | Hard drop |
| Up / X | Rotate right |
| Z / Ctrl | Rotate left |
| C / Shift | Hold |
| P / Esc | Pause |
| F1 | Help |
| F2 | Guide |
| M | Music on/off |
| - / + | Music volume |
| N | Sound on/off |
| 9 / 0 | Sound volume |
| Enter | Select / new game |

Нижняя подсказка SHALL быть «Press Enter or Esc to return» на экране «Controls» и «Press F1 or Enter to return» на экране клавиш по F1. Надписи SHALL NOT содержать символов стрелок: во встроенном шрифте их нет. Поле, фигуры и боковая панель SHALL NOT рисоваться, пока показан список клавиш; после его закрытия по F1 они SHALL рисоваться как прежде. Все надписи SHALL помещаться в окно, а столбцы таблицы SHALL NOT перекрываться.

#### Scenario: Экран управления
- **WHEN** в главном меню выбран пункт «Controls»
- **THEN** на экране «SEVA Tetris», все 14 строк таблицы (например, «C / Shift» — «Hold», «9 / 0» — «Sound volume» и «F2» — «Guide») и «Press Enter or Esc to return», а надписей «SCORE» и «NEXT» нет

#### Scenario: Экран клавиш по F1
- **WHEN** во время партии нажата F1
- **THEN** на экране показаны «SEVA Tetris», таблица горячих клавиш и «Press F1 or Enter to return»

#### Scenario: Возврат к полю
- **WHEN** экран клавиш, открытый по F1, закрыт
- **THEN** снова показаны поле с фигурами и боковая панель с «SCORE» и «NEXT»
