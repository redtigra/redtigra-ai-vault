# Управление сессиями Claude Code

## Читать транскрипт другой сессии

Все сессии сохраняются как JSONL в `~/.claude/projects/`. Имя папки = рабочая директория сессии (слэши → дефисы).

Найти сегодняшние сессии:

```bash
# bash
find ~/.claude/projects -name "*.jsonl" -not -name "agent-*" -newer ~/.claude/projects \
  -printf "%T@ %k KB  %p\n" | sort -rn | head -20
```

```powershell
# PowerShell
Get-ChildItem "$env:USERPROFILE\.claude\projects\**\*.jsonl" -Recurse |
  Where-Object { $_.LastWriteTime -gt (Get-Date).Date -and $_.Name -notmatch 'agent-' } |
  Sort-Object LastWriteTime -Descending |
  Select-Object FullName, LastWriteTime, @{N='KB';E={[math]::Round($_.Length/1KB)}}
```

Прочитать последние сообщения из конкретного файла:
```bash
tail -20 ~/.claude/projects/<папка>/<uuid>.jsonl | \
  python3 -c "
import sys, json
for line in sys.stdin:
    try:
        m = json.loads(line).get('message', {})
        role = m.get('role', '')
        c = m.get('content', '')
        text = c if isinstance(c, str) else ' '.join(b.get('text','') for b in c if b.get('type')=='text')
        if role and text: print(f'{role}: {text[:200]}')
    except: pass
"
```

Это работает даже если сессия зависла (API error) — транскрипт уже на диске.

## Handover между сессиями

Лучший способ — project note в волте. Создать файл `Projects/<название>.md` с:
- Цель
- Ключевые решения (с причинами)
- Статус (чекбоксы)
- Следующий шаг (конкретная команда)

В новой сессии:
> "продолжи работу по `C:\Users\RHL49\repos\redtigra-ai-vault\Projects\<название>.md`"

Альтернатива — `/handoff` skill: генерирует более детальный документ (открытые файлы, незавершённые команды).

## Откуда запускать сессию

Запускать из папки, где лежат файлы проекта — Claude подхватит `CLAUDE.md` и сессия запишется в правильное место.

| Задача | Директория |
|--------|-----------|
| Общие скрипты, дневники, MS Graph | `C:\Users\RHL49\` |
| Конкретный клиентский проект | `C:\Users\RHL49\<клиент>\` |
| Репозиторий | `C:\Users\RHL49\repos\<repo>\` |

Если сессия случайно открыта не в той папке — закрыть, открыть заново из правильной, передать контекст через project note.
