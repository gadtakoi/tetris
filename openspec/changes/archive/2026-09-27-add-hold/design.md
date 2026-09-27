# Design

## Context

`Game._spawn(piece_type)` сейчас обнуляет таймер гравитации, ставит фигуру в позицию появления, при занятых клетках объявляет конец игры и выбирает новую следующую фигуру. После `add-lock-delay` он же обнуляет задержку фиксации. Панель: «NEXT» при y = 20, превью 4 × 4 клетки с (340, 60), счётчики при y = 220/300/380, индикаторы звука с y = 470. `Controller` определяет звуки по результатам команд (`_sound_if`). Мотивация описана в proposal.md, требования — в дельтах.

## Goals / Non-Goals

**Goals:**
- Hold по правилам современных тетрисов: один раз на фигуру, обмен, исходная ориентация.
- Окно и поле не меняются: всё помещается в правую панель.

**Non-Goals:**
- Анимация обмена.

## Decisions

### Логика
```python
held_type: PieceType | None   # None в начале партии
can_hold: bool                 # True в начале партии и после каждой фиксации

def hold(self) -> bool:
    if self.is_over or not self.can_hold:
        return False
    current = self.active.type
    if self.held_type is None:
        self.held_type = current
        self._spawn(self.next_type)       # как после фиксации: новая следующая
    else:
        self.held_type, incoming = current, self.held_type
        self._bring_in(incoming)          # следующая не меняется
    self.can_hold = False
    return True
```
`_spawn` разделяется: `_bring_in(piece_type)` обнуляет таймеры, проверяет block out и ставит фигуру, а `_spawn` = `_bring_in` + выбор новой следующей. `_lock()` возвращает `can_hold = True` перед появлением следующей фигуры. `new_game()` очищает ячейку.

### Интерфейс
- `Key.HOLD`, `KEY_MAP`: `K_c`, `K_LSHIFT`, `K_RSHIFT`. В `Controller.key_down` во время партии: `self._sound_if(self.game.hold(), Sound.HOLD)`. `GameLike` дополняется `hold()`, `held_type`, `can_hold`.
- Панель (`layout.py`):

  | Элемент | y |
  |---|---|
  | «NEXT» | 20 |
  | превью NEXT, 4 × 2 клетки | 50–110 |
  | «HOLD» | 125 |
  | превью HOLD | 155–215 |
  | SCORE / значение | 235 / 265 |
  | LINES / значение | 300 / 330 |
  | LEVEL / значение | 365 / 395 |

  Индикаторы звука остаются с y = 470. Превью рисует строки 0–1 рамки: в ориентации 0 все фигуры, включая I (строка 1) и O, занимают только их.
- Приглушённый цвет — `layout.dimmed_color()`, (r // 2, g // 2, b // 2).
- Звук: `Sound.HOLD = "hold"`, `synth.effect_hold()` — две короткие ноты вниз, около 120 мс. Эффект автоматически попадает в `Audio.create()` через `EFFECTS`.

### Список клавиш
`layout.HOTKEYS` и требование «Экран клавиш» здесь не меняются, чтобы не пересекаться с `add-main-menu`, который переписывает этот экран целиком и добавляет туда строку «C / Shift — Hold».

## Risks / Trade-offs

- [Панель становится плотной] → превью уменьшены до 2 строк, счётчики сдвинуты. Все элементы проверяются тестом на то, что счётчики заканчиваются выше y = 460, а превью не пересекаются.
- [Shift одновременно модификатор] → игра не использует комбинаций с Shift, поэтому конфликтов нет.

## Migration Plan

Не требуется.
