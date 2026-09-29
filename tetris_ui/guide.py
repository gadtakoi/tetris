"""The in-game guide without pygame: page titles and the text of each page in English and Russian.

The titles are English keys of texts.RU, like every other fixed text. The paragraphs are
written for each language separately. The Controls page has no text here: layout builds
it from layout.HOTKEYS, so it always matches the key list. The built-in font has no arrow
glyphs, so keys are named in words.
"""

from __future__ import annotations

PAGE_TITLES = (
    "Menu and pause",
    "Controls",
    "How to play",
    "Tips",
    "Settings and sound",
    "High scores",
)
PAGE_COUNT = len(PAGE_TITLES)
CONTROLS_PAGE = PAGE_TITLES.index("Controls")

# Paragraphs of each page, in PAGE_TITLES order; the Controls page is built by layout.
_PARAGRAPHS: dict[str, tuple[tuple[str, ...], ...]] = {
    "en": (
        (
            "In the main menu, Up and Down choose an item and Enter opens it.",
            '"New game" starts a game. "High scores" shows the best results. "Settings" '
            'changes the language, sound, start level, ghost and autorepeat. "Controls" '
            'lists the keys. "Guide" opens this guide. "Quit" closes the game.',
            "Esc returns to the menu from the High scores, Settings and Controls screens; "
            "on High scores and Controls, Enter does too.",
            'During a game, P or Esc pauses it. In the pause menu, "Continue" goes back to '
            'the game and "Main menu" leaves it: a game left this way does not go into the '
            "high scores.",
            "During a game, F1 shows the list of keys. F2 opens this guide both in the menu "
            "and in a game; the game waits while the guide or the key list is open.",
        ),
        (),
        (
            "Pieces of four squares fall from the top. Move and rotate them to fill whole "
            "rows: a full row disappears and everything above it moves down. The game ends "
            "when a new piece has no room to appear.",
            "NEXT shows the next three pieces, top one first, and HOLD the piece put aside. "
            "BEST is the top score of the table, or this game's score once it is higher.",
            "Rows cleared by one piece score 40 for 1 row, 100 for 2, 300 for 3 and 1200 "
            "for 4, multiplied by (level + 1). Dropping pieces scores nothing.",
            "The level goes up by 1 every 10 rows and is never lower than the start level "
            "from the settings. The higher the level, the faster the pieces fall: 0.8 s "
            "per row on level 0, 0.1 s on level 9, and faster still after that.",
        ),
        (
            "Ghost: the dim outline under a falling piece shows where it will land.",
            "Down makes the piece fall faster but does not lock it at the bottom. Space "
            "drops it at once and locks it.",
            "C or Shift puts the piece aside into HOLD; if HOLD already has a piece, they "
            "swap. You can do this once per piece.",
            "If a turn is blocked by a wall, the floor or other pieces, the game tries to "
            "shift the piece a little so that it can still turn.",
            "A piece that has landed locks after 0.5 s. Each move or turn in that time "
            "gives it another 0.5 s, but only up to 15 times until it gets lower.",
            "Pieces come in bags of 7: each bag has every piece once in random order, so "
            "no piece stays away for long.",
        ),
        (
            "On the Settings screen, Up and Down choose a line and Left and Right change "
            "its value. Changes apply at once and are kept for the next launch.",
            "Language: English or Русский. Music and Sound: on or off. Music volume and "
            "Sound volume: from 0 to 100 %.",
            "Start level: from 0 to 19, the level the next games start at. Ghost: show "
            "where the piece will land or not. Autorepeat: Slow, Normal or Fast, how "
            "quickly the piece moves while Left or Right is held.",
            "Music plays during a game, and moves, turns, holds, locks, cleared rows and "
            "level-ups have their own sounds. The music pauses with the game and is silent "
            "in the menu.",
            "M and N switch the music and the sounds on and off, - and + change the music "
            "volume, 9 and 0 the sound volume.",
        ),
        (
            "The table keeps the 10 best results. If a finished game makes it into the "
            "table, NEW RECORD appears and you type a name: up to 10 letters, digits, "
            "spaces, hyphens or underscores. Backspace deletes a character and Enter saves "
            "the result; an empty name is saved as PLAYER.",
            "After a game the table is shown with your new record highlighted: Enter "
            "starts a new game and Esc opens the main menu. The table can also be opened "
            'from the main menu: "High scores".',
        ),
    ),
    "ru": (
        (
            "В главном меню клавиши Вверх и Вниз выбирают пункт, Enter открывает его.",
            "«Новая игра» начинает партию. «Рекорды» показывают лучшие результаты. "
            "«Настройки» меняют язык, звук, начальный уровень, тень и автоповтор. "
            "«Управление» — список клавиш. «Инструкция» открывает этот текст. «Выход» "
            "закрывает игру.",
            "Esc возвращает в меню с экранов рекордов, настроек и управления, а с рекордов "
            "и управления — ещё и Enter.",
            "Во время партии P или Esc ставят игру на паузу. В меню паузы «Продолжить» "
            "возвращает в партию, а «Главное меню» бросает её: такая партия в рекорды "
            "не попадает.",
            "Во время партии F1 показывает список клавиш. F2 открывает эту инструкцию и в "
            "меню, и в партии; пока открыты инструкция или список клавиш, игра стоит.",
        ),
        (),
        (
            "Сверху падают фигуры из четырёх квадратов. Сдвигайте и поворачивайте их, "
            "чтобы собирать сплошные ряды: заполненный ряд исчезает, а всё, что выше, "
            "опускается. Игра заканчивается, когда новой фигуре негде появиться.",
            "ДАЛЕЕ показывает три следующие фигуры, верхняя придёт первой, а ЗАПАС — "
            "отложенную. РЕКОРД — лучший результат таблицы или очки партии, если они больше.",
            "За ряды, убранные одной фигурой, дают 40 очков за 1 ряд, 100 за 2, 300 за 3 "
            "и 1200 за 4, умноженные на (уровень + 1). За падение фигур очков нет.",
            "Уровень растёт на 1 за каждые 10 рядов и не бывает ниже начального уровня "
            "из настроек. Чем выше уровень, тем быстрее падают фигуры: на уровне 0 — "
            "0,8 с на клетку, на уровне 9 — 0,1 с, дальше ещё быстрее.",
        ),
        (
            "Тень — тусклый контур под падающей фигурой — показывает, куда она упадёт.",
            "Вниз ускоряет падение, но у дна фигура не закрепляется сразу. Пробел бросает "
            "фигуру вниз и сразу закрепляет её.",
            "C или Shift убирают фигуру в ЗАПАС; если там уже есть фигура, они меняются "
            "местами. Откладывать можно один раз на каждую фигуру.",
            "Если повороту мешают стена, дно или другие фигуры, игра пробует чуть сдвинуть "
            "фигуру, чтобы поворот всё же получился.",
            "Упавшая фигура закрепляется через 0,5 с. Каждый сдвиг или поворот за это "
            "время даёт ещё 0,5 с, но не больше 15 раз, пока фигура не опустится ниже.",
            "Фигуры выпадают мешками по 7: в каждом мешке все семь фигур по разу в "
            "случайном порядке, поэтому нужная фигура не пропадает надолго.",
        ),
        (
            "На экране настроек Вверх и Вниз выбирают строку, Влево и Вправо меняют "
            "значение. Изменения действуют сразу и сохраняются до следующего запуска.",
            "Язык — English или Русский. Музыка и Звук — вкл или выкл. Громкость музыки "
            "и Громкость звука — от 0 до 100 %.",
            "Начальный уровень — от 0 до 19, с него начнутся следующие партии. Тень — "
            "показывать ли, куда упадёт фигура. Автоповтор — Медленно, Обычно или Быстро: "
            "как быстро едет фигура, если держать Влево или Вправо.",
            "Во время партии играет музыка, а сдвиги, повороты, откладывание, "
            "закрепление, убранные ряды и новый уровень сопровождаются звуками. На паузе "
            "музыка останавливается, в меню она не звучит.",
            "M и N включают и выключают музыку и звуки, - и + меняют громкость музыки, "
            "9 и 0 — громкость звука.",
        ),
        (
            "В таблице хранятся 10 лучших результатов. Если результат партии попал в "
            "таблицу, появляется НОВЫЙ РЕКОРД и поле для имени: до 10 символов — буквы, "
            "цифры, пробел, дефис и подчёркивание. Backspace стирает символ, Enter "
            "сохраняет результат; пустое имя сохраняется как PLAYER.",
            "После партии показывается таблица, ваш новый рекорд выделен: Enter начинает "
            "новую партию, Esc открывает главное меню. Таблицу можно открыть и из "
            "главного меню: «Рекорды».",
        ),
    ),
}


def paragraphs(page: int, language: str) -> tuple[str, ...]:
    """The paragraphs of a page (0-based) in the language, "en" or "ru"; empty for the
    Controls page, which layout builds from the key list."""
    return _PARAGRAPHS["ru" if language == "ru" else "en"][page]
