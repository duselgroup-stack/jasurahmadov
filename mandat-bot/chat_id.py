#!/usr/bin/env python3
"""Telegram chat_id ni aniqlab beradi.

Ishlatish:
  1. Telegram'da o'z botingizni oching va /start bosing.
  2. python mandat-bot/chat_id.py
"""

import os
import pathlib
import sys

import requests

HERE = pathlib.Path(__file__).resolve().parent


def load_dotenv() -> None:
    env_file = HERE / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        token = input("Bot tokenini kiriting: ").strip()
    if not token:
        print("Token kerak.", file=sys.stderr)
        return 1

    resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30)
    data = resp.json()
    if not data.get("ok"):
        print(f"Telegram xato javob berdi: {data}", file=sys.stderr)
        return 1

    found = {}
    for update in data.get("result", []):
        chat = (update.get("message") or update.get("channel_post") or {}).get("chat")
        if chat:
            found[chat["id"]] = chat.get("username") or chat.get("title") or chat.get("first_name", "")

    if not found:
        print("Hech narsa topilmadi. Botga Telegram'da /start yozing va qaytadan urinib ko'ring.")
        return 1

    print("Topilgan chat'lar:")
    for chat_id, label in found.items():
        print(f"  TELEGRAM_CHAT_ID = {chat_id}   ({label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
