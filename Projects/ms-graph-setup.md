# MS Graph Setup

## Цель
Тянуть письма из M365 Exchange Online в Claude Code CLI — чтобы включать их в ежедневные сводки вместе с дневниковыми заметками из Obsidian.

## Стек
- Язык: **Python** (msal + requests)
- ~~PowerShell~~ (Microsoft.Graph.Mail) — отказались, см. решения

## Ключевые решения
| Дата | Решение | Причина |
|------|---------|---------|
| 2026-06-23 | Перешли с PowerShell на Python | PowerShell требует смены execution policy (admin consent) + WAM не работает в non-interactive режиме. Python — портируемо на Linux (конечная цель) |
| 2026-06-23 | Device code flow вместо браузерного OAuth | Non-interactive окружение CLI; device code: показываем код, вводим в браузере сами. Токен кешируется на несколько недель |
| 2026-06-23 | Используем Microsoft Graph Explorer app ID | Публичное приложение от Microsoft, не нужен client secret — проще для начала |

## Статус
- [x] Модуль Microsoft.Graph.Mail установлен (v2.38.0) — не используется, но установлен
- [x] MS Graph MCP (claude.ai Microsoft 365) авторизован — работает только в веб, не в CLI
- [x] Python 3.14 подтверждён на машине
- [x] Установлены `msal` и `requests`
- [x] Скрипт написан: `C:\Users\RHL49\repos\redtigra-ai-vault\Tools\Scripts\fetch_mail.py`
- [x] Запустить `python fetch_mail.py` в терминале для первичной авторизации (device code)
- [x] Проверить что письма за последнюю неделю читаются
- [x] Интегрировать в дневниковый пайплайн — вручную: запускать перед составлением сводки

## Интеграция в пайплайн дневника

Почта — один из источников для **итоговой дневной заметки** (`diaries/2026/YYYYMMDD_Day.md`).

**Когда запускать:** перед составлением вечерней/дневной сводки, наряду с worklog, клиентскими заметками, Teams.

**Claude Code команда `/mail`** (`~/.claude/commands/mail.md`):
```
/mail                                           # сегодня
/mail вчера                                     # вчера
/mail 2026-06-22                                # конкретная дата
/mail --search "Canonical PO"                   # полнотекстовый поиск (KQL)
/mail --from canonical                          # по отправителю (имя / email / домен)
/mail --from brandon --since 2026-06-01         # отправитель + диапазон дат
/mail --from brandon --thread                   # переписка в обе стороны
/mail 2026-06-22 --attachments                  # скачать аттачменты
/mail --help                                    # справка
```
Аттачменты сохраняются в `~/Downloads/mail-attachments/`.  
Скрипт: `C:\Users\RHL49\repos\redtigra-ai-vault\Tools\Scripts\fetch_mail.py`

**Что искать в выводе:**
- письма по каждому активному клиенту и workstream;
- ключевые слова: PO, invoice, quote, approval, access, schedule, technician;
- имена партнёров, поставщиков, техников.

Каждый thread связывается с нужным клиентом и кейсом в структуре `## [[Customer]] → ### #case/...`.

## Будущее
- Переехать на Linux-машину: Python/MSAL работает нативно, тот же Graph API

## Ссылки
- Скрипт: `C:\Users\RHL49\repos\redtigra-ai-vault\Tools\Scripts\fetch_mail.py`
- Daily notes (vault): `C:\Users\RHL49\repos\redtigra-ai-vault\Daily\YYYY-MM-DD.md`
- Воркфлоу: Codex собирает сводки → планируется перенести в Claude Code Cowork
