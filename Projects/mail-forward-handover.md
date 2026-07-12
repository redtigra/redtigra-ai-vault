# Handover — Forward/Send из Outlook в скилле `/mail`

> Связано с [[ms-graph-setup]]. Это задача-продолжение: научить скилл `/mail` **пересылать/отправлять** письма из рабочего Outlook (Remotehands), а не только читать.

## Зачем

Сейчас `/mail` умеет только читать почту. Возникла потребность: переслать конкретное письмо (напр. CBRE PO) на заданный адрес **с рабочего Remotehands-ящика**, с сохранением оригинального содержимого/вложений. Пользователь пока делает это вручную в Outlook.

Через доступные в Claude Code инструменты это невозможно:
- MCP-коннектор Microsoft 365 — только чтение/поиск (нет send/forward), scope не в нашем управлении.
- Gmail-коннектор — только `create_draft` (не отправка) и завязан на личный gmail, не на Outlook.

Единственный путь, который **в нашей власти** — расширить собственный скрипт `fetch_mail.py`.

## Что сделать (суть)

Добавить в `fetch_mail.py` возможность forward конкретного письма через Microsoft Graph.

### Файлы
- Скрипт: `C:\Users\RHL49\.claude\skills\mail\fetch_mail.py` (актуальная рабочая копия, используется скиллом `/mail`)
- Есть более старая копия в vault: `C:\Users\RHL49\repos\redtigra-ai-vault\Tools\Scripts\fetch_mail.py` — **не редактировать вслепую**, канонична та, что в `.claude/skills/mail/`. Свериться, синхронизировать при необходимости.
- Дока скилла: `C:\Users\RHL49\.claude\skills\mail\SKILL.md` — обновить таблицу опций.

### Ключевое техническое изменение

1. **Scope.** Сейчас в `fetch_mail.py`:
   ```python
   SCOPES = ["Mail.Read"]
   ```
   Для пересылки нужен `Mail.Send`:
   ```python
   SCOPES = ["Mail.Read", "Mail.Send"]
   ```
   ⚠ Добавление scope требует **повторного consent** — после правки первый запуск с `--forward` должен пройти через `--reauth` (device flow заново), иначе тихо будет старый токен без `Mail.Send`. Токен-кеш общий (`~/.ms_graph_token_cache.json`, шарится с `/save-attachments`) — переавторизация не сломает чтение.

2. **Endpoint.** Graph отдаёт два варианта:
   - `POST /me/messages/{id}/forward` — отправляет forward **сразу** (тело: `comment`, `toRecipients`).
   - `POST /me/messages/{id}/createForward` → возвращает черновик → потом `POST /me/messages/{draftId}/send`. Позволяет предпросмотр/правку перед отправкой.

   **Рекомендация:** по умолчанию делать `createForward` (черновик) и печатать сводку, а реальный `send` — только с явным подтверждающим флагом (напр. `--send`). Отправка письма — необратимое внешнее действие, guard обязателен (см. риски).

   Пример прямого forward:
   ```python
   def forward_message(access_token, message_id, to_addr, comment=""):
       headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
       body = {
           "comment": comment,
           "toRecipients": [{"emailAddress": {"address": to_addr}}],
       }
       r = requests.post(f"{GRAPH}/me/messages/{message_id}/forward", headers=headers, json=body)
       r.raise_for_status()   # 202 Accepted, без тела
   ```

3. **Как выбрать письмо.** `forward` требует `message.id`. `fetch_mail.py` уже тянет `id` в `SELECT_FIELDS`. Варианты CLI:
   - `--forward <email>` в связке с `--search "..."`/`--from ...`, но **строго при одном совпадении** — иначе отказ с просьбой уточнить (нельзя вслепую переслать не то письмо).
   - либо явный `--id <messageId>` + `--forward <email>`.

   **Рекомендация:** реализовать оба; по умолчанию требовать ровно одно совпадение и печатать subject/from/date того письма, что будет переслано, до отправки.

### Предлагаемый UX
```
/mail --search "CBRE PO 95NLP7494808" --forward buyer@example.com
   → находит письмо, показывает subject/from/date, создаёт ЧЕРНОВИК forward, печатает подтверждение
/mail --search "..." --forward buyer@example.com --send
   → то же + реально отправляет
/mail --id AAMk... --forward buyer@example.com --comment "FYI, PO attached" --send
```

## Риски и guard-рейлы
- **Отправка необратима и уходит наружу.** Дефолт — черновик; реальная отправка только по явному `--send`. Перед `--send` печатать кому/что уходит.
- **Множественные совпадения поиска** → НЕ пересылать; выйти с ошибкой и списком кандидатов.
- **Mail.Send у Graph Explorer app.** Публичное приложение Microsoft (`14d82eec-...`) поддерживает делегированный `Mail.Send`, но арендатор Remotehands теоретически может ограничивать. Проверить на первом `--reauth`: если consent не даёт `Mail.Send` — фиксировать в статусе, возможно понадобится отдельная регистрация приложения (это меняет модель, см. [[ms-graph-setup]] «Ключевые решения»).
- **Вложения при forward.** Graph forward сохраняет оригинальные вложения на стороне сервера автоматически — руками контент прикладывать не нужно. Проверить, что так и происходит (особенно для inline).

## Критерии готовности (Definition of Done)
- [ ] `SCOPES` включает `Mail.Send`, `--reauth` проходит и выдаёт токен с этим scope.
- [ ] `--forward <email>` создаёт черновик forward выбранного письма; при неоднозначности — понятный отказ.
- [ ] `--send` реально отправляет; без него — только черновик.
- [ ] Перед отправкой печатается subject/from/date/to.
- [ ] Оригинальные вложения уходят в forward (проверено на письме с PDF, напр. CBRE PO).
- [ ] `SKILL.md`: обновлена таблица опций (`--forward`, `--send`, `--id`, `--comment`).
- [ ] Vault-копия `Tools/Scripts/fetch_mail.py` синхронизирована или помечена как устаревшая.
- [ ] Этот файл обновлён: статус → done, зафиксировано, дал ли арендатор `Mail.Send`.

## Заметки по окружению
- Реальный python: `C:\Users\RHL49\AppData\Local\Python\bin\python.exe` (в PATH первой стоит заглушка Microsoft Store, которая падает «Python was not found» — вызывать по полному пути).
- Зависимости: `msal`, `requests` (уже стоят).
- Токен-кеш: `~/.ms_graph_token_cache.json`.

## Ссылки
- [[ms-graph-setup]] — базовая настройка Graph, история решений (device flow, Graph Explorer app).
- Скрипт (канон): `C:\Users\RHL49\.claude\skills\mail\fetch_mail.py`
- Graph forward: `POST /me/messages/{id}/forward` · createForward → send
