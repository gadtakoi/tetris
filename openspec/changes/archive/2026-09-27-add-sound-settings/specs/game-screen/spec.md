# Spec Delta

## MODIFIED Requirements

### Requirement: Индикаторы звука
На боковой панели ниже счётчиков (при y ≥ 460) SHALL показываться три строки: «MUSIC ON» или «MUSIC OFF», «VOLUME <уровень>%» (например, «VOLUME 50%») и «SOUND ON» или «SOUND OFF» — по текущим настройкам звука, во всех режимах игры.

#### Scenario: После запуска
- **WHEN** игра запущена впервые (сохранённых настроек нет)
- **THEN** на панели показаны «MUSIC ON», «VOLUME 50%» и «SOUND ON»

#### Scenario: Музыка выключена
- **WHEN** нажата M
- **THEN** на панели показаны «MUSIC OFF» и «SOUND ON»

#### Scenario: Громкость на панели
- **WHEN** при уровне 50 % дважды нажата `+`
- **THEN** на панели показано «VOLUME 70%»
