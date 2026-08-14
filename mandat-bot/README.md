# Mandat kuzatuvchi bot

[my.uzbmb.uz](https://my.uzbmb.uz) saytini avtomatik kuzatadi va mandat javobi
chiqishi bilan Telegram'ga xabar yuboradi. GitHub Actions'da har 15 daqiqada
o'zi ishga tushadi — kompyuter yoqiq turishi shart emas.

## Nega parol emas, cookie?

Saytning login sahifasida **rasmli CAPTCHA** bor (`/site/captcha`), shuning uchun
bot parol bilan o'zi kira olmaydi. Buning o'rniga: siz bir marta brauzerda
o'zingiz kirasiz (CAPTCHA'ni odam yechadi), bot esa o'sha sessiyaning
`PHPSESSID` cookie'sidan foydalanadi.

Cookie eskirganda bot sizga «🔑 Cookie eskirdi» deb xabar beradi — yangilaysiz.

## Ikki qatlam

| Qatlam | Cookie kerakmi | Nima qiladi |
|---|---|---|
| Ochiq sahifalar | ❌ yo'q | Asosiy sahifa, qabul xizmati va «Natijani ko'rish» sahifalaridagi o'zgarishlarni kuzatadi |
| Shaxsiy kabinet | ✅ ha | `/person` va `/my-task` sahifalarini tekshiradi, aniq shaxsiy natijani topadi |

Cookie bermasangiz ham bot ishlaydi — faqat birinchi qatlam bilan.

---

## Sozlash

### 1. Telegram bot va chat_id

1. [@BotFather](https://t.me/BotFather) → `/newbot` → tokenni oling.
2. O'z botingizni Telegram'da oching va **/start** bosing (busiz bot sizga yoza olmaydi).
3. chat_id ni aniqlang:

```bash
pip install -r mandat-bot/requirements.txt
```

```bash
TELEGRAM_BOT_TOKEN=SIZNING_TOKEN python mandat-bot/chat_id.py
```

Windows PowerShell'da:

```bash
$env:TELEGRAM_BOT_TOKEN="SIZNING_TOKEN"; python mandat-bot/chat_id.py
```

### 2. PHPSESSID cookie (ixtiyoriy, lekin tavsiya qilinadi)

1. Chrome'da [my.uzbmb.uz/site/login](https://my.uzbmb.uz/site/login) ga kiring.
2. `F12` → **Application** → **Storage → Cookies → https://my.uzbmb.uz**.
3. `PHPSESSID` qatoridagi **Value** qiymatini nusxalang.

### 3. GitHub Secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Nomi | Qiymati |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather bergan token |
| `TELEGRAM_CHAT_ID` | 3-qadamda topilgan raqam |
| `UZBMB_PHPSESSID` | Cookie qiymati (ixtiyoriy) |

> Bu qiymatlar hech qachon kodga yozilmaydi va repoda ko'rinmaydi.

### 4. Ishga tushirish

Workflow **`main` shoxida** bo'lishi shart — GitHub jadval bo'yicha ishlaydigan
workflow'larni faqat asosiy shoxdan ishga tushiradi.

Birinchi marta qo'lda sinab ko'ring: repo → **Actions → Mandat tekshiruvi →
Run workflow**. Telegram'ga «✅ Bot ishga tushdi» xabari kelishi kerak.

---

## Lokal sinash

```bash
cp mandat-bot/.env.example mandat-bot/.env
```

`.env` ni to'ldiring va ishga tushiring:

```bash
python mandat-bot/check.py
```

## Sozlamalar

Sozlamalar [`.github/workflows/mandat-check.yml`](../.github/workflows/mandat-check.yml)
faylining `env:` bo'limida turadi.

| O'zgaruvchi | Standart | Ma'nosi |
|---|---|---|
| `REPORT_EVERY_RUN` | `1` | Har tekshiruvda «chiqdi/chiqmadi» hisoboti. Kuniga ~96 ta xabar. `0` — o'chiradi |
| `SEND_HEARTBEAT` | `1` | Kuniga bir marta «hali chiqmadi» xabari. `REPORT_EVERY_RUN=1` bo'lsa e'tiborga olinmaydi |
| `HEARTBEAT_HOUR` | `8` | Kunlik xabar soati (Toshkent vaqti) |

Xabar kamroq kelishini xohlasangiz ikki yo'l bor: `REPORT_EVERY_RUN` ni `0` ga
o'tkazish, yoki tekshirish oralig'ini oshirish (`*/30` — yarim soatda bir marta).

Tekshirish oralig'ini o'zgartirish: [`.github/workflows/mandat-check.yml`](../.github/workflows/mandat-check.yml)
faylidagi `cron: "*/15 * * * *"` qatori.

## Qanday ishlaydi

Har ishga tushganda sahifalarning matni tozalanadi (skript, CSRF token, captcha
havolalari olib tashlanadi) va `state.json` dagi oldingi nusxa bilan
solishtiriladi. Faqat haqiqiy o'zgarish bo'lgandagina xabar yuboriladi, shuning
uchun spam bo'lmaydi.

`state.json` o'zgarganda workflow uni repoga commit qiladi — keyingi ishga
tushishda taqqoslash uchun kerak.

## Eslatmalar

- GitHub jadval bo'yicha ishlaydigan workflow'larni **60 kun** repo'da hech
  qanday harakat bo'lmasa to'xtatadi. Qabul mavsumi qisqa, shuning uchun bu
  muammo bo'lmasligi kerak.
- `cron` aniq daqiqada emas, 5–20 daqiqa kechikish bilan ishlashi mumkin —
  bu GitHub'ning odatiy holati.
- Sayt har 15 daqiqada bir marta so'roq qilinadi — bu yuk tug'dirmaydi.
