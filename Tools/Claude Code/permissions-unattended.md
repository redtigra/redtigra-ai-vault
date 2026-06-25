---
tags: [claude-code, permissions, skills, powershell]
---

# Пермишены и unattended-исполнение скилов

Как сделать так, чтобы скил проходил **без единого запроса пермишена** (важно для автономного запуска).

## Главное открытие: матчер PowerShell бьёт команду на сегменты

Матчер пермишенов PowerShell в Claude Code **разбивает пайплайны и многострочные команды на сегменты и проверяет каждый отдельно**. Префиксное правило вроде `PowerShell(Get-ChildItem *)` НЕ покрывает пайплайн целиком.

Пример, который упорно требовал пермишен:

```powershell
Get-ChildItem ... | Where-Object {...} | ForEach-Object { try {...} catch {} }
```

Здесь матчер видит ≥3 сегмента — `Get-ChildItem`, `Where-Object`, `ForEach-Object` — и каждому нужно своё allow-правило. Плюс `{ }` скрипт-блоки, `try/catch` и ведущее присваивание `$var = ...` тоже считаются отдельными командами → запрос пермишена.

Ещё одна ловушка: правило `PowerShell($*)` **не** матчит `$x = ...`, потому что `$` трактуется как regex-якорь конца строки.

## Правило: в скилах — простые одиночные команды

Чтобы скил работал unattended:

- ❌ НЕ использовать пайплайны (`|`), `Where-Object`, `ForEach-Object`, многострочные скрипт-блоки в shell-командах.
- ✅ Логику с циклами/фильтрами выносить в **закоммиченный `.py` скрипт** и звать одной командой `python "<путь>"` — она матчится правилом `PowerShell(python *)`.
- ✅ Файловые операции — плоскими одиночными командами:
  - `Move-Item -LiteralPath "<src>" -Destination "<dst>"`
  - `New-Item -ItemType Directory -Path "<dir>" -Force`
  - `Test-Path "<path>"`, `Get-ChildItem "<dir>" -Directory -Name` (без пайпов)
- ✅ Чтение/запись текстовых файлов — через инструменты Read/Edit/Write, а не PowerShell.

## Кейс: `/process-finance`

Скил трижды спотыкался о пермишен на OneDrive-preflight, пока preflight был PowerShell-пайплайном. Исправление:

- `preflight.py` — гидрирует OneDrive-плейсхолдеры (читает по байту) и печатает список файлов.
- `read_pdf.py` — извлекает текст PDF (или рендерит в PNG для сканов) одним `python ...`.
- `skill.md` — явный запрет пайплайнов; все шаги через одиночные команды.
- В `~/.claude/settings.json` добавлены Write/Edit-правила на папку назначения `Company Documents - Operations/*`.

Файлы: `C:\Users\RHL49\.claude\skills\process-finance\`

После этого полный прогон — без единого промпта.

См. также [[Скилы]], [[session-management]].
