"""
Fetch emails from Microsoft 365 via Graph API.

Usage:
    python fetch_mail.py                            # today
    python fetch_mail.py 2026-06-22                 # specific date
    python fetch_mail.py --search "Canonical PO"    # full-text search
    python fetch_mail.py --from canonical           # filter by sender name/email/domain
    python fetch_mail.py --since 2026-06-01         # with --search or --from: limit date range
    python fetch_mail.py --from brandon --thread    # full conversation (both directions)
    python fetch_mail.py --attachments              # download attachments to disk
    python fetch_mail.py --reauth                   # force re-login
"""

import os
import sys
import base64
import argparse
from datetime import datetime, timedelta, timezone

import msal
import requests

# Ensure UTF-8 output in Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph Explorer (public app)
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Mail.Read"]
CACHE_PATH = os.path.expanduser("~/.ms_graph_token_cache.json")
GRAPH = "https://graph.microsoft.com/v1.0"
ATTACHMENTS_DIR = os.path.expanduser("~/Downloads/mail-attachments")

SELECT_FIELDS = "id,subject,from,receivedDateTime,bodyPreview,isRead,importance,hasAttachments"


def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
        cache.deserialize(open(CACHE_PATH).read())
    return cache


def save_cache(cache):
    if cache.has_state_changed:
        open(CACHE_PATH, "w").write(cache.serialize())


def get_token(reauth=False):
    cache = load_cache()
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

    token = None
    if not reauth:
        accounts = app.get_accounts()
        if accounts:
            token = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not token:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to start device flow: {flow}")
        print(f"\n{flow['message']}\n", flush=True)
        token = app.acquire_token_by_device_flow(flow)

    save_cache(cache)

    if "access_token" not in token:
        raise RuntimeError(f"Auth failed: {token.get('error_description', token)}")

    return token["access_token"]


def _paginate(access_token, params, max_results=200, folder=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    base = f"{GRAPH}/me/mailFolders/{folder}/messages" if folder else f"{GRAPH}/me/messages"
    url = base
    messages = []
    while url and len(messages) < max_results:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
        params = None  # nextLink already includes params
    return messages


def fetch_by_date(access_token, date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dt_next = dt + timedelta(days=1)
    params = {
        "$filter": f"receivedDateTime ge {dt.strftime('%Y-%m-%dT00:00:00Z')} and receivedDateTime lt {dt_next.strftime('%Y-%m-%dT00:00:00Z')}",
        "$select": SELECT_FIELDS,
        "$orderby": "receivedDateTime asc",
        "$top": 100,
    }
    return _paginate(access_token, params)


def fetch_by_search(access_token, query, since=None, until=None, thread=False):
    # Graph $search uses KQL: supports "from:x", "subject:x", free text, AND/OR
    params = {
        "$search": f'"{query}"',
        "$select": SELECT_FIELDS,
        "$top": 50,
    }
    messages = _paginate(access_token, params)

    if thread:
        # Also search sent items for outgoing side of the conversation
        sent_params = {
            "$search": f'"{query}"',
            "$select": SELECT_FIELDS,
            "$top": 50,
        }
        sent = _paginate(access_token, sent_params, folder="SentItems")
        # Merge, deduplicate by id
        seen = {m["id"] for m in messages}
        for m in sent:
            if m["id"] not in seen:
                m["_sent"] = True
                messages.append(m)

    # Client-side date filtering (can't combine $search + $filter without ConsistencyLevel)
    if since or until:
        since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc) if since else None
        until_dt = (datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)) if until else None
        messages = [
            m for m in messages
            if (not since_dt or _parse_dt(m) >= since_dt)
            and (not until_dt or _parse_dt(m) < until_dt)
        ]

    messages.sort(key=_parse_dt)
    return messages


def _resolve_date(value):
    today = datetime.now().date()
    aliases = {"сегодня": 0, "today": 0, "вчера": -1, "yesterday": -1}
    if value.lower() in aliases:
        return (today + timedelta(days=aliases[value.lower()])).strftime("%Y-%m-%d")
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


def _parse_dt(msg):
    s = msg["receivedDateTime"]
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_attachments(access_token, message_id, save_dir):
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{GRAPH}/me/messages/{message_id}/attachments", headers=headers)
    resp.raise_for_status()

    saved = []
    os.makedirs(save_dir, exist_ok=True)

    for att in resp.json().get("value", []):
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue
        content = att.get("contentBytes", "")
        if not content:
            continue
        name = att.get("name", "attachment")
        path = os.path.join(save_dir, name)
        base, ext = os.path.splitext(path)
        i = 1
        while os.path.exists(path):
            path = f"{base}_{i}{ext}"
            i += 1
        with open(path, "wb") as f:
            f.write(base64.b64decode(content))
        saved.append(path)

    return saved


def format_messages(messages, label, att_map=None):
    if not messages:
        return f"# Mail — {label}\n\nНет писем.\n"

    lines = [f"# Mail — {label}\n", f"Всего писем: {len(messages)}\n"]
    for msg in messages:
        dt_str = msg["receivedDateTime"]
        time_str = dt_str[:10] + " " + dt_str[11:16]
        sender = msg["from"]["emailAddress"]
        name = sender.get("name", "")
        addr = sender.get("address", "")
        subject = msg.get("subject", "(без темы)")
        preview = msg.get("bodyPreview", "").replace("\r\n", " ").replace("\n", " ").strip()

        flags = []
        if msg.get("_sent"):
            flags.append("→ отправлено")
        if not msg.get("isRead"):
            flags.append("UNREAD")
        if msg.get("importance") == "high":
            flags.append("!")
        if msg.get("hasAttachments"):
            flags.append("📎")
        flag_str = f" [{', '.join(flags)}]" if flags else ""

        lines.append(f"## {time_str} — {subject}{flag_str}")
        lines.append(f"От: {name} <{addr}>")
        lines.append(preview)

        if att_map and msg.get("id") in att_map:
            for path in att_map[msg["id"]]:
                lines.append(f"  📎 Сохранено: {path}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("date", nargs="?", default=datetime.today().strftime("%Y-%m-%d"),
                        help="Дата YYYY-MM-DD (по умолчанию сегодня); игнорируется при --search/--from")
    parser.add_argument("--search", metavar="QUERY",
                        help='Полнотекстовый поиск (KQL: "from:x", "subject:x", свободный текст)')
    parser.add_argument("--from", dest="sender", metavar="NAME_OR_EMAIL",
                        help="Поиск по отправителю (имя, email или домен)")
    parser.add_argument("--since", metavar="YYYY-MM-DD", help="С этой даты (для --search / --from)")
    parser.add_argument("--until", metavar="YYYY-MM-DD", help="По эту дату (для --search / --from)")
    parser.add_argument("--thread", action="store_true", help="Переписка в обе стороны (входящие + исходящие)")
    parser.add_argument("--attachments", action="store_true", help="Скачать аттачменты на диск")
    parser.add_argument("--reauth", action="store_true", help="Принудительная повторная авторизация")
    args = parser.parse_args()

    access_token = get_token(reauth=args.reauth)

    if args.search or args.sender:
        query = args.search or f"from:{args.sender}"
        messages = fetch_by_search(access_token, query, since=args.since, until=args.until, thread=args.thread)
        label = query
        if args.since:
            label += f" (с {args.since})"
        if args.until:
            label += f" по {args.until}"
    else:
        date_str = _resolve_date(args.date)
        if date_str is None:
            print(f"Неверная дата: {args.date}. Нужен YYYY-MM-DD, 'сегодня' или 'вчера'.", file=sys.stderr)
            sys.exit(1)
        messages = fetch_by_date(access_token, date_str)
        label = date_str

    att_map = {}
    if args.attachments:
        safe_label = label.replace(" ", "_").replace(":", "-").replace("/", "-")
        save_dir = os.path.join(ATTACHMENTS_DIR, safe_label)
        for msg in messages:
            if msg.get("hasAttachments"):
                saved = fetch_attachments(access_token, msg["id"], save_dir)
                if saved:
                    att_map[msg["id"]] = saved

    print(format_messages(messages, label, att_map or None))


if __name__ == "__main__":
    main()
