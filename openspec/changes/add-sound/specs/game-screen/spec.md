# Spec Delta

## ADDED Requirements

### Requirement: Индикаторы звука
На боковой панели ниже счётчиков (при y ≥ 460) SHALL показываться две строки: «MUSIC ON» или «MUSIC OFF» и «SOUND ON» или «SOUND OFF» — по текущему состоянию переключателей, во всех режимах игры.

#### Scenario: После запуска
- **WHEN** игра только запущена
- **THEN** на панели показаны «MUSIC ON» и «SOUND ON»

#### Scenario: Музыка выключена
- **WHEN** нажата M
- **THEN** на панели показаны «MUSIC OFF» и «SOUND ON»
