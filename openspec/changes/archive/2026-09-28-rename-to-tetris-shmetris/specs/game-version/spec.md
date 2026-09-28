# Spec Delta

## MODIFIED Requirements

### Requirement: Номер версии
Игра SHALL иметь номер версии вида MAJOR.MINOR.PATCH — три целых неотрицательных числа через точку без ведущих нулей. Текущая версия — 1.0.0. Главное меню и свойства `tetris_shmetris.exe` SHALL показывать один и тот же номер, и при запуске из исходников (`python -m tetris_ui`) SHALL показываться тот же номер, что в собранном exe.

#### Scenario: Текущая версия
- **WHEN** игра запущена командой `python -m tetris_ui`
- **THEN** в главном меню показана надпись «v1.0.0»

#### Scenario: Один номер везде
- **WHEN** собран `tetris_shmetris.exe`
- **THEN** версия продукта в его свойствах совпадает с номером в надписи главного меню без буквы «v»

### Requirement: Версия в свойствах exe
`tetris_shmetris.exe` SHALL содержать ресурс версии Windows с такими значениями:

| Поле | Значение |
|---|---|
| Версия файла (FileVersion) | <номер версии>.0, сейчас 1.0.0.0 |
| Версия продукта (ProductVersion) | <номер версии>, сейчас 1.0.0 |
| Название продукта (ProductName) | Tetris Shmetris |
| Описание файла (FileDescription) | Tetris Shmetris |
| Исходное имя файла (OriginalFilename) | tetris_shmetris.exe |

Проводник Windows SHALL показывать эти значения на вкладке «Подробно» свойств файла.

Ресурс версии SHALL храниться в файле `version_info.txt` в корне проекта. Этот файл SHALL храниться в git (его не исключает `.gitignore`) и SHALL соответствовать текущему номеру версии; сборка берёт ресурс версии из него.

#### Scenario: Свойства собранного exe
- **WHEN** командой `python build_exe.py` собран `tetris_shmetris.exe`
- **THEN** версия файла 1.0.0.0, версия продукта 1.0.0, название продукта «Tetris Shmetris», исходное имя файла «tetris_shmetris.exe»

#### Scenario: Файл версии в репозитории
- **WHEN** номер версии — 1.0.0
- **THEN** в корне проекта есть `version_info.txt` с версией файла 1.0.0.0 и версией продукта 1.0.0, и git его не игнорирует
