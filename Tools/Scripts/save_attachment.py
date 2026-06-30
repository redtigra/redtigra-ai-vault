"""
Download a specific email attachment to a given directory.

Usage:
    python save_attachment.py --message-id <id> --dest <dir>
    python save_attachment.py --message-id <id> --dest <dir> --filename <name>
    python save_attachment.py --reauth ...
"""

import os
import sys
import base64
import argparse

# Reuse auth from fetch_mail.py in the same directory
sys.path.insert(0, os.path.dirname(__file__))
from fetch_mail import get_token

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GRAPH = "https://graph.microsoft.com/v1.0"


def download_attachments(access_token, message_id, dest_dir, filename_filter=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{GRAPH}/me/messages/{message_id}/attachments", headers=headers)
    resp.raise_for_status()

    os.makedirs(dest_dir, exist_ok=True)
    saved = []

    for att in resp.json().get("value", []):
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue
        content = att.get("contentBytes", "")
        if not content:
            continue
        name = att.get("name", "attachment")
        if filename_filter and filename_filter.lower() not in name.lower():
            continue

        path = os.path.join(dest_dir, name)
        base, ext = os.path.splitext(path)
        i = 1
        while os.path.exists(path):
            path = f"{base}_{i}{ext}"
            i += 1

        with open(path, "wb") as f:
            f.write(base64.b64decode(content))
        saved.append(path)
        print(f"Saved: {path}")

    if not saved:
        print("No matching attachments found.", file=sys.stderr)

    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message-id", required=True, help="Graph message ID")
    parser.add_argument("--dest", required=True, help="Destination directory")
    parser.add_argument("--filename", help="Filter: only save attachments whose name contains this string")
    parser.add_argument("--reauth", action="store_true", help="Force re-login")
    args = parser.parse_args()

    token = get_token(reauth=args.reauth)
    download_attachments(token, args.message_id, args.dest, filename_filter=args.filename)


if __name__ == "__main__":
    main()
