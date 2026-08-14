#!/usr/bin/env python3
"""my.uzbmb.uz mandat kuzatuvchi bot.

Ikki qatlamda ishlaydi:
  1) Ochiq sahifalar - login talab qilmaydi, saytdagi o'zgarishlarni kuzatadi.
  2) Shaxsiy kabinet   - PHPSESSID cookie berilgan bo'lsa, ukangizning
     shaxsiy sahifalarini tekshiradi.

Har ishga tushganda oldingi holat bilan solishtiradi va faqat o'zgarish
bo'lgandagina Telegram'ga xabar yuboradi.
"""

import difflib
import html
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

BASE = "https://my.uzbmb.uz"
HERE = pathlib.Path(__file__).resolve().parent
STATE_PATH = HERE / "state.json"

TASHKENT = timezone(timedelta(hours=5))

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Login talab qilmaydigan sahifalar.
PUBLIC_PAGES = [
    ("Asosiy sahifa", f"{BASE}/"),
    ("Qabul xizmati (2026-2027)", f"{BASE}/service/42"),
    ("Natijani ko'rish", f"{BASE}/allow/bachelor-answer"),
]

# Faqat cookie bo'lganda tekshiriladigan shaxsiy sahifalar.
PRIVATE_PAGES = [
    ("Profil", f"{BASE}/person"),
    ("Arizalarim", f"{BASE}/my-task"),
]

# Shaxsiy sahifada shu so'zlar chiqsa - mandat javobi bor deb hisoblanadi.
MANDAT_WORDS = [
    "mandat",
    "мандат",
    "talabalikka tavsiya",
    "tavsiya etildi",
    "qabul qilindi",
    "рекомендован",
    "зачислен",
]

# Ochiq sahifalarda faqat shu so'zlar "mandat chiqdi" signali sifatida
# qabul qilinadi (qolgani doim sahifada turadigan matn, yolg'on signal beradi).
PUBLIC_MANDAT_WORDS = ["mandat", "мандат"]

MAX_TG_LEN = 3800


# --------------------------------------------------------------------------
# Yordamchi funksiyalar
# --------------------------------------------------------------------------

def load_dotenv() -> None:
    """Yonidagi .env faylini o'qiydi (lokal ishga tushirish uchun)."""
    env_file = HERE / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


SCRIPT_RE = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")
BLOCK_RE = re.compile(r"(?i)<(?:br\s*/?|/(?:p|div|li|tr|td|h[1-6]|section|article))>")
TAG_RE = re.compile(r"<[^>]+>")

# Har safar o'zgarib turadigan qiymatlar - ularni tashlab yuboramiz,
# aks holda har tekshiruvda "o'zgarish bor" deb yolg'on signal chiqadi.
NOISE_RES = [
    re.compile(r"\?v=[0-9a-zA-Z.]+"),
    re.compile(r"[A-Za-z0-9_\-]{24,}={0,2}"),
]


def page_lines(raw_html: str) -> list[str]:
    """HTML'dan tozalangan matn qatorlarini ajratib oladi."""
    text = SCRIPT_RE.sub(" ", raw_html)
    text = BLOCK_RE.sub("\n", text)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    for noise in NOISE_RES:
        text = noise.sub("", text)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and line not in lines:
            lines.append(line)
    return lines


def find_words(lines: list[str], words: list[str]) -> list[str]:
    """Berilgan so'zlar uchraydigan qatorlarni qaytaradi."""
    hits = []
    for line in lines:
        low = line.lower()
        if any(word in low for word in words):
            hits.append(line)
    return hits


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# Telegram
# --------------------------------------------------------------------------

class Telegram:
    def __init__(self, token: str, chat_id: str):
        self.api = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        for chunk in self._split(text):
            resp = requests.post(
                f"{self.api}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if not resp.ok:
                print(f"[telegram] xato {resp.status_code}: {resp.text}", file=sys.stderr)

    @staticmethod
    def _split(text: str) -> list[str]:
        if len(text) <= MAX_TG_LEN:
            return [text]
        parts, current = [], ""
        for line in text.splitlines(keepends=True):
            if len(current) + len(line) > MAX_TG_LEN:
                parts.append(current)
                current = ""
            current += line
        if current:
            parts.append(current)
        return parts


def esc(text: str) -> str:
    return html.escape(text, quote=False)


# --------------------------------------------------------------------------
# Sahifani tekshirish
# --------------------------------------------------------------------------

def fetch(session: requests.Session, url: str, follow: bool) -> requests.Response:
    return session.get(url, allow_redirects=follow, timeout=30)


def diff_lines(old: list[str], new: list[str], limit: int = 12) -> list[str]:
    """Yangi paydo bo'lgan qatorlar."""
    known = set(old)
    added = [line for line in new if line not in known]
    return added[:limit]


def main() -> int:
    load_dotenv()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    cookie = os.environ.get("UZBMB_PHPSESSID", "").strip()
    heartbeat_on = os.environ.get("SEND_HEARTBEAT", "1").strip() != "0"
    heartbeat_hour = int(os.environ.get("HEARTBEAT_HOUR", "8"))
    # Har tekshiruvda "chiqdi/chiqmadi" hisoboti yuborilsinmi.
    report_every_run = os.environ.get("REPORT_EVERY_RUN", "0").strip() == "1"

    if not token or not chat_id:
        print(
            "TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID kerak. "
            "chat_id ni bilish uchun: python mandat-bot/chat_id.py",
            file=sys.stderr,
        )
        return 1

    tg = Telegram(token, chat_id)
    state = load_state()
    pages = state.setdefault("pages", {})
    flags = state.setdefault("flags", {})
    first_run = not pages

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "uz,ru;q=0.8"})
    if cookie:
        session.cookies.set("PHPSESSID", cookie, domain="my.uzbmb.uz")

    messages: list[str] = []
    mandat_hits: list[str] = []
    errors: list[str] = []
    checked = 0

    targets = [(name, url, False) for name, url in PUBLIC_PAGES]
    if cookie:
        targets += [(name, url, True) for name, url in PRIVATE_PAGES]

    for name, url, private in targets:
        try:
            resp = fetch(session, url, follow=not private)
        except requests.RequestException as exc:
            errors.append(f"{name}: {exc.__class__.__name__}")
            continue

        # Shaxsiy sahifa login'ga qaytarsa - sessiya tugagan.
        if private and resp.status_code in (301, 302, 303, 307, 308):
            if not flags.get("cookie_expired"):
                flags["cookie_expired"] = True
                messages.append(
                    "🔑 <b>Cookie eskirdi</b>\n"
                    "Shaxsiy kabinet tekshirilmayapti. Saytga qaytadan kiring va "
                    "yangi <code>PHPSESSID</code> ni GitHub Secrets'ga qo'ying "
                    "(<code>UZBMB_PHPSESSID</code>)."
                )
            continue

        if resp.status_code != 200:
            errors.append(f"{name}: HTTP {resp.status_code}")
            continue

        if private:
            flags["cookie_expired"] = False

        checked += 1
        lines = page_lines(resp.text)
        entry = pages.get(url, {})
        old_lines = entry.get("lines", [])

        words = MANDAT_WORDS if private else PUBLIC_MANDAT_WORDS
        hits = find_words(lines, words)
        if hits:
            mandat_hits.extend(f"<b>{esc(name)}</b>: {esc(h)}" for h in hits[:5])

        if old_lines:
            added = diff_lines(old_lines, lines)
            if added:
                body = "\n".join(f"• {esc(line)}" for line in added)
                messages.append(
                    f"📄 <b>{esc(name)}</b> sahifasida o'zgarish:\n{body}\n\n{esc(url)}"
                )

        pages[url] = {"name": name, "lines": lines}

    # --- xabarlarni yig'ish -------------------------------------------------
    now = datetime.now(TASHKENT)
    stamp = now.strftime("%d.%m.%Y %H:%M")

    if mandat_hits and not flags.get("mandat_notified"):
        flags["mandat_notified"] = True
        messages.insert(
            0,
            "🎉 <b>MANDAT CHIQDI!</b>\n\n"
            + "\n".join(mandat_hits)
            + f"\n\n👉 {BASE}/person\n<i>{stamp}</i>",
        )
    elif not mandat_hits:
        flags["mandat_notified"] = False

    if not cookie:
        scope_note = "faqat ochiq sahifalar"
    elif flags.get("cookie_expired"):
        scope_note = "🔑 cookie eskirgan"
    else:
        scope_note = "shaxsiy kabinet ham tekshirildi"

    # Har tekshiruvda holat hisoboti (mandat topilmagan holatda).
    if report_every_run and not mandat_hits and checked:
        messages.append(
            f"🔍 Mandat hali chiqmadi.\n"
            f"<i>{stamp}</i> · {checked} ta sahifa · {scope_note}"
        )

    if first_run:
        scope = "ochiq sahifalar + shaxsiy kabinet" if cookie else "faqat ochiq sahifalar"
        messages.append(
            f"✅ <b>Bot ishga tushdi</b>\nKuzatilmoqda: {scope}.\n"
            f"Mandat chiqishi bilan shu yerga xabar keladi.\n<i>{stamp}</i>"
        )

    if errors:
        fails = flags.get("fail_streak", 0) + 1
        flags["fail_streak"] = fails
        # Bitta-yarimta uzilish normal holat, faqat uch marta ketma-ket
        # xato bo'lsa xabar beramiz.
        if fails == 3:
            messages.append(
                "⚠️ <b>Saytga ulanib bo'lmayapti</b>\n"
                + "\n".join(f"• {esc(e)}" for e in errors)
            )
    else:
        flags["fail_streak"] = 0

    # Kuniga bir marta "tirikman" xabari.
    # Har tekshiruvda hisobot yuborilayotgan bo'lsa, bu ortiqcha.
    if heartbeat_on and not report_every_run and not first_run:
        today = now.strftime("%Y-%m-%d")
        if now.hour >= heartbeat_hour and state.get("last_heartbeat") != today:
            state["last_heartbeat"] = today
            if not cookie:
                status = "ℹ️ faqat ochiq sahifalar (cookie berilmagan)"
            elif flags.get("cookie_expired"):
                status = "🔑 cookie eskirgan — yangilash kerak"
            else:
                status = "✅ shaxsiy kabinet ham tekshirilyapti"
            if not messages:
                messages.append(
                    f"🕗 <b>Kunlik holat</b>\nMandat hali chiqmadi.\n"
                    f"{checked} ta sahifa tekshirildi, {status}.\n<i>{stamp}</i>"
                )

    for message in messages:
        tg.send(message)

    save_state(state)
    print(f"{stamp} | tekshirildi: {checked} | xabar: {len(messages)} | xato: {len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
