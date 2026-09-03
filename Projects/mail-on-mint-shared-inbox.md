# План: запуск `/mail` на Mint со складыванием вложений в общую Windows-папку

**Дата:** 2026-08-06
**Статус:** 🟡 СПЛАНИРОВАНО, НЕ НАЧАТО — план утверждён к записи, реализация отложена до возвращения.
**Связано:** [[linux-migration-plan]] (это первый конкретный шаг «Слоя 2», §4), [[ms-graph-setup]] (исходный сетап Graph; **устарел**, см. §9), [[mail-permission-prompt-handover]], [[agentic-skill-hardening-plan]].

---

## 1. Цель

Запускать скилл `/mail` на `redtigra-mint`, а вложения складывать в **ту же самую**
папку `finance-docs-to-sort`, что и на Windows — через SMB-шару, поднятую с Windows-машины.
Тогда `/process-finance` на Windows подхватывает их как обычно, ничего не зная про Mint.

**Явно вне объёма:** финансовый пайплайн (`process-finance`, `generate-invoice`,
`docx-render-check`) остаётся на Windows и не трогается. Решено пользователем 06.08.2026.

## 2. Почему это меньше, чем кажется

Две находки в разведке радикально сократили объём:

1. **Механизм конфигурируемых путей уже существует и уже заполнен.**
   `~/.claude/skills/_common/agentcfg.py` создан ровно для этой проблемы — его докстринг
   прямо говорит: *«no skill hardcodes a machine path; each host carries its own
   `~/.claude/agent-config.json` and this module is the only code that reads it»*.
   На Windows `paths.finance_inbox` **уже** содержит нужный путь; на Mint для него есть
   слот `finance_inbox: null`. То есть `fetch_mail.py` — единственный скрипт, который
   нарушает уже принятое в доме правило. Чинится не изобретением механизма, а
   подключением к существующему.
2. **Скилл `mail` уже лежит в репозитории** `redtigra-claude/skills/mail` — просто не
   установлен в `/home/claude/.claude/skills/`.

## 3. Разведка (проверено 2026-08-06)

| Что | Значение |
|---|---|
| Windows LAN IP | `10.0.1.21` (Wi-Fi, **DHCP**) |
| Mint LAN IP | `10.0.1.14` — та же подсеть |
| VPN на Windows | адаптер NordLynx `10.5.0.2` — активен |
| Агентская учётка на Mint | `claude` (алиас `mint-claude`), sudo `NOPASSWD: ALL` |
| Python на Mint | венв `/home/claude/rh247/venv/bin/python` |
| `msal` / `requests` в венве | **обоих нет** — ставить |
| `_common/agentcfg.py` на Mint | есть |
| Скиллы на Mint | 10 шт., `mail` среди них **нет** |
| `mail` в репозитории `redtigra-claude` | **есть** |
| `paths.finance_inbox` на Windows | заполнен нужным путём |
| `paths.finance_inbox` на Mint | `null` |
| Шары на Windows | только админские `C$` / `ADMIN$` — выделенной нет |
| Монтирования на Mint | нет |

> ⚠️ Ловушка при повторной разведке: алиас `mint` — это пользователь `redtigra`, а агент
> живёт под `claude` (`mint-claude`). Под `redtigra` нет ни `~/.claude/skills`, ни `~/repos`,
> и картина выглядит «пустой». Проверять надо под `mint-claude`.

## 4. Правки кода

### 4.1 `~/.claude/skills/mail/fetch_mail.py`

Подключить существующий хелпер по образцу usage-блока в `_common/agentcfg.py:24-30`:

```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_common"))
import agentcfg
```

- Константу `ATTACHMENTS_DIR` (строка 48) **удалить**, путь брать из
  `agentcfg.path("finance_inbox")`.
- Резолвить **лениво** — внутри функции скачивания, не на импорте. Иначе прогон с
  `--no-attachments` упадёт на хосте, где папка не настроена, хотя ему она не нужна.
- Фолбэк на старую константу **не делать**. На Windows ключ уже заполнен, а молчаливый
  фолбэк вернёт ровно тот баг, который чиним.
- `CACHE_PATH` и `STATE_PATH` оставить на `~` — состояние сознательно по-хостовое (§7).

### 4.2 Убрать создание мусорного каталога

В `fetch_attachments` (`fetch_mail.py:211-238`) заменить `os.makedirs(save_dir, exist_ok=True)`
(строка 217) на проверку `os.path.isdir(save_dir)` с внятной ошибкой.

**Почему это баг, а не перестраховка:** на Linux в строке
`C:\Users\RHL49\OneDrive - ...\finance-docs-to-sort` нет ни одного `/`. POSIX читает её
как **одно** имя каталога, и `os.makedirs` молча создаёт в текущей рабочей папке каталог
с обратными слэшами в имени и складывает вложения туда. Без этой правки первый же прогон
на Mint «сработает успешно» и потеряет файлы в мусорном каталоге.

Папка-приёмник всегда существует заранее — и на Windows, и на смонтированной шаре —
так что создавать её скрипт не должен никогда.

### 4.3 `~/.claude/skills/mail/SKILL.md`

Добавить Linux-вариант вызова рядом с Windows-овым, как уже сделано в
`save-skill/SKILL.md:19-26`:

```
/home/claude/rh247/venv/bin/python "/home/claude/.claude/skills/mail/fetch_mail.py" [options]
```

Плюс абзац: на Mint вложения уезжают в ту же папку через шару; вотермарк по-хостовый.

## 5. Настройка Mint (делаю я — sudo есть)

1. **Зависимости в венв** (венв изолирован, PEP 668 не мешает):
   `/home/claude/rh247/venv/bin/pip install msal requests`
2. **Точка монтирования:** `/mnt/rh247-finance-inbox`
3. **Учётные данные:** `/etc/samba/creds/rh247`, root, `chmod 600`
4. **`/etc/fstab`:**
   ```
   //10.0.1.21/finance-inbox /mnt/rh247-finance-inbox cifs \
     credentials=/etc/samba/creds/rh247,uid=claude,gid=claude,\
     file_mode=0664,dir_mode=0775,iocharset=utf8,vers=3.0,nofail,_netdev 0 0
   ```
   `nofail` обязателен — иначе выключенная Windows-машина ломает загрузку Mint.
5. **`agent-config.json` на Mint:** `paths.finance_inbox` → `/mnt/rh247-finance-inbox`
6. **Установить скилл:** скопировать `redtigra-claude/skills/mail` →
   `/home/claude/.claude/skills/mail` (обычным каталогом — так лежат остальные;
   симлинком там только `host-check`)
7. **Allow-rules** в `settings.json` на Mint — две штуки:
   ```
   "Bash(/home/claude/rh247/venv/bin/python \"/home/claude/.claude/skills/mail/fetch_mail.py\" *)"
   "Bash(/home/claude/rh247/venv/bin/python \"/home/claude/.claude/skills/mail/fetch_mail.py\")"
   ```
   Вторая — точная, без аргументов: инкрементальный прогон вызывается без параметров.
   На Linux правил вдвое меньше, чем на Windows — нет инструмента PowerShell и
   комбинаторики слэшей (ровно то, о чём [[linux-migration-plan]] §2).
8. **Авторизация:** один раз `fetch_mail.py --reauth` под `claude` (device flow,
   scope `Mail.Read`) → создаст `/home/claude/.ms_graph_token_cache.json`.

**Токен-кэш между машинами не синхронизируем.** Это OAuth refresh-токен, то есть учётка,
а не настройка; device flow на втором хосте проходится один раз.

## 6. Что нужно на Windows (нужен админ — помогает пользователь)

1. **Создать шару** (PowerShell от администратора):
   ```powershell
   New-SmbShare -Name finance-inbox -Path "C:\Users\RHL49\OneDrive - Remotehands 247 B.V\Documents\finance-docs-to-sort" -FullAccess RHL49
   ```
2. **Открыть SMB в брандмауэре** для профиля Private:
   ```powershell
   Enable-NetFirewallRule -DisplayGroup "File and Printer Sharing"
   ```
3. **NordVPN.** Активен адаптер NordLynx. Если в клиенте не включён доступ к локальной
   сети, SMB с Mint не достучится — **самая вероятная причина**, если монтирование не
   заработает с первого раза.
4. **DHCP.** `10.0.1.21` выдан по DHCP и может смениться. Либо резервация на роутере,
   либо запись в `/etc/hosts` на Mint — иначе шара однажды отвалится молча.

## 7. Принятый компромисс: вотермарк остаётся по-хостовым

Решение пользователя 06.08.2026: состояние пока не трогаем. С работающей шарой это
безопаснее, чем звучит:

- **Почта не теряется.** Каждый хост запрашивает `receivedDateTime ge last_received` от
  **своего** вотермарка (`fetch_mail.py:146-152`), поэтому отставший хост видит всё,
  включая уже забранное другим. Пропусков не бывает — только повторы.
- **Цена — дубликаты.** Повторно скачанные вложения приедут в ту же папку с суффиксами
  `_1`, `_2` (`fetch_mail.py:229-233`). Дедуп в `/process-finance` ловит их по имени и
  размеру и удаляет.

Где живёт состояние сейчас: `~/.ms_graph_mail_state.json` (`last_received` + `last_ids` —
письма ровно на граничной секунде). Двигается только на инкрементальном прогоне, который
реально качал вложения (`fetch_mail.py:331`).

**Если дубликаты начнут раздражать** — два пути, оба отдельной задачей:
- перенести файл состояния в общее место (тот же `agent-config.json` или шара);
- держать состояние **в самой почте** — категория Outlook `RH247-processed` вместо файла.
  Синхронизация не нужна вообще, гонок между хостами нет. Цена: скоуп `Mail.ReadWrite`
  вместо `Mail.Read` и запись в ящик.

## 8. Проверка

1. **Монтирование:** `ssh mint-claude "ls /mnt/rh247-finance-inbox"` — должен показать
   `processing-log.html` и остальное содержимое инбокса.
2. **Запись:** создать на Mint пробный файл в точке монтирования, убедиться, что он виден
   на Windows, удалить. Проверяет `uid=claude` и права, а не только чтение.
3. **Резолв пути:** на Mint `fetch_mail.py --no-attachments` — вывод штатный, вотермарк не
   двигается, мусорный каталог с обратными слэшами в рабочей папке **не** появляется.
4. **Скачивание:** `fetch_mail.py <дата с известным вложением>` (прогон с явной датой не
   двигает вотермарк). Файл должен появиться в OneDrive-папке на Windows. Дубликат, если
   получится, убрать через `cleanup.py`.
5. **Отсутствие промптов:** `match_rule.py` для обеих форм вызова, затем проверить, что в
   логе разрешений нет `PERMISSION_REQUEST` от этого прогона.
6. **Windows не сломан:** прогнать `/mail` на Windows — путь должен резолвиться из
   `agent-config.json` в тот же самый OneDrive-каталог.

**Порядок:** сначала правки кода и проверка на Windows (там всё настроено — это ловит
регрессию до того, как в игру войдёт Mint), затем шара, затем Mint.

## 9. Открытые вопросы и долги

- **[[ms-graph-setup]] устарел** и вводит в заблуждение: там сказано, что скрипт лежит в
  `redtigra-ai-vault\Tools\Scripts\fetch_mail.py`, а вложения падают в
  `~/Downloads/mail-attachments/`. Фактически скрипт живёт в `~/.claude/skills/mail/`, а
  вложения — в OneDrive-папке `finance-docs-to-sort`. Ту заметку я намеренно не переписывал.
- **`_common` нет в репозитории** `redtigra-claude/skills` (там 13 скиллов, `_common` среди
  них отсутствует), хотя на Mint он присутствует. То есть попал туда не через обычный
  деплой. Импорт `agentcfg` на Mint работать будет, но канал доставки `_common` стоит
  прояснить, прежде чем от него начнёт зависеть ещё один скилл.
- **`ops_root` на Mint тоже `null`** — если когда-нибудь поедет `process-finance`,
  это следующий ключ к заполнению.

## Ссылки на артефакты

- Черновик плана этой сессии: `~/.claude/plans/sunny-weaving-unicorn.md`
- Скилл: `~/.claude/skills/mail/` (`fetch_mail.py`, `SKILL.md`)
- Хелпер путей: `~/.claude/skills/_common/agentcfg.py`
- Бэкап-репозиторий: `redtigra-claude`
