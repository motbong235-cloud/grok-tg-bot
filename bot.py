#!/usr/bin/env python3
"""
Grok AI Telegram Bot — xAI API + Telegram
Env:
  TELEGRAM_BOT_TOKEN  (required)
  XAI_API_KEY         (required)  — https://console.x.ai
  GROK_MODEL          (optional)  — default grok-3
  SYSTEM_PROMPT       (optional)
  ADMIN_ID            (optional)
  MAX_HISTORY         (optional)  — default 12 messages
"""
from __future__ import annotations

import os
import time
import logging
import threading
from collections import defaultdict, deque

import requests
import telebot
from telebot import types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("grok-bot")

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
XAI_KEY = (os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY") or "").strip()
MODEL = (os.getenv("GROK_MODEL") or "grok-3").strip()
BOT_NAME = (os.getenv("BOT_NAME") or "Porpor Fix AI").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID") or "0")
MAX_HISTORY = int(os.getenv("MAX_HISTORY") or "12")
XAI_URL = (os.getenv("XAI_API_URL") or "https://api.x.ai/v1/chat/completions").strip()

DEFAULT_SYSTEM = """អ្នកជា AI Maintenance Assistant សម្រាប់គម្រោង **Porpor Topup** តែប៉ុណ្ណោះ។
ឈ្មោះ: {name} · Powered by Grok (xAI).

## តួនាទី
- ផ្តោតតែការថែទាំ / fix / កែ UI·UX / payment (ABA PayWay·KHQR) / admin / deploy Render នៃ Porpor Topup
- Repo: github.com/motbong235-cloud/porpor-topup
- Live: porportopup.com · Admin path /pp-console
- កុំនិយាយអំពីគម្រោងផ្សេង (REX, Kai bot, ។ល។) លុះតែអ្នកប្រើសួរច្បាស់

## របៀបឆ្លើយ
- ភាសាខ្មែរ បើគេសរសេរខ្មែរ · អង់គ្លេស បើគេសរសេរអង់គ្លេស
- ខ្លី ច្បាស់ · ជំហាន fix លេខ 1,2,3
- បើត្រូវកែកូដ: ប្រាប់ file / ផ្នែកដែលត្រូវប្តូរ · និងថា «សុំ Grok chat ធ្វើ commit + push ទៅ repo porpor-topup»
- កុំបន្លំថាអ្នក push GitHub បានដោយខ្លួនឯងពី Telegram — ការផ្លាស់កូដពិតធ្វើតាម Grok chat / CI

## បច្ចេកទេស Porpor (សង្ខេប)
- Stack: React + Express · payment Khmer System បង្ហាញឈ្មោះ ABA PayWay
- Admin private URL · token/password
- Live chat, stock services, Telegram login, order → channel notify
- Render deploy · starter plan

ជួយ debug error log, UI, QR fail, admin 404, build fail — តែក្នុងវិសាលភាព Porpor Topup។""".format(
    name=BOT_NAME
)

SYSTEM_PROMPT = (os.getenv("SYSTEM_PROMPT") or DEFAULT_SYSTEM).strip()

if not TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN")
if not XAI_KEY:
    raise SystemExit("Missing XAI_API_KEY (from console.x.ai)")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
# user_id -> deque of {role, content}
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
user_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)


def call_grok(messages: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {XAI_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }
    r = requests.post(XAI_URL, headers=headers, json=payload, timeout=90)
    if r.status_code >= 400:
        log.warning("xAI error %s: %s", r.status_code, r.text[:400])
        try:
            err = r.json().get("error") or r.json()
        except Exception:
            err = r.text[:200]
        raise RuntimeError(f"Grok API {r.status_code}: {err}")
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Empty response from Grok")
    msg = choices[0].get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("Empty content from Grok")
    return content


def build_messages(uid: int, user_text: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in histories[uid]:
        msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def remember(uid: int, role: str, content: str):
    histories[uid].append({"role": role, "content": content})


def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💬 Chat", "🗑 Clear memory")
    kb.row("ℹ️ About", "🛑 Stop")
    return kb


@bot.message_handler(commands=["start", "help"])
def cmd_start(message: types.Message):
    uid = message.from_user.id
    name = message.from_user.first_name or "friend"
    bot.send_message(
        message.chat.id,
        f"សួស្តី <b>{name}</b> 👋\n"
        f"ខ្ញុំ <b>{BOT_NAME}</b> — AI ថែទាំ <b>Porpor Topup</b>\n"
        f"(Grok · xAI)\n\n"
        f"ផ្ញើ bug / error / screenshot — ខ្ញុំវិភាគ និងណែនាំ fix។\n"
        f"កែកូដ + <b>push repo</b>: តាម Grok chat (auto upload ពេលរួច)\n\n"
        f"· /clear — លុប memory\n"
        f"· /about — ព័ត៌មាន\n"
        f"<i>Model: {MODEL}</i>",
        reply_markup=main_kb(),
    )


@bot.message_handler(commands=["clear", "reset"])
def cmd_clear(message: types.Message):
    uid = message.from_user.id
    histories[uid].clear()
    bot.reply_to(message, "✅ Memory cleared — ចាប់ផ្តើមសន្ទនាថ្មី។")


@bot.message_handler(commands=["about"])
def cmd_about(message: types.Message):
    bot.reply_to(
        message,
        f"<b>{BOT_NAME}</b>\n"
        f"Powered by <b>xAI Grok</b>\n"
        f"Model: <code>{MODEL}</code>\n"
        f"History: {MAX_HISTORY} messages / user",
    )


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("🗑 Clear memory", "Clear memory", "clear"))
def btn_clear(message: types.Message):
    cmd_clear(message)


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("ℹ️ About", "About"))
def btn_about(message: types.Message):
    cmd_about(message)


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("🛑 Stop", "Stop"))
def btn_stop(message: types.Message):
    histories[message.from_user.id].clear()
    bot.reply_to(message, "បានបញ្ឈប់ context។ ផ្ញើសារថ្មីពេលណាក៏បាន។")


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("💬 Chat", "Chat"))
def btn_chat(message: types.Message):
    bot.reply_to(message, "សរសេរសំណួរ ឬសាររបស់អ្នកមក…")


@bot.message_handler(content_types=["text"])
def on_text(message: types.Message):
    if not message.text or message.text.startswith("/"):
        return
    uid = message.from_user.id
    text = message.text.strip()
    if not text:
        return

    # ignore pure keyboard labels already handled
    if text in ("💬 Chat", "🗑 Clear memory", "ℹ️ About", "🛑 Stop"):
        return

    with user_locks[uid]:
        wait = bot.send_message(message.chat.id, "⏳ Grok កំពុងគិត…")
        try:
            msgs = build_messages(uid, text)
            answer = call_grok(msgs)
            remember(uid, "user", text)
            remember(uid, "assistant", answer)
            # Telegram message limit ~4096
            if len(answer) > 4000:
                answer = answer[:4000] + "…"
            try:
                bot.edit_message_text(answer, message.chat.id, wait.message_id)
            except Exception:
                bot.send_message(message.chat.id, answer)
        except Exception as e:
            log.exception("chat error")
            err = str(e)
            if "401" in err or "Unauthorized" in err:
                tip = "\n\n🔑 ពិនិត្យ <code>XAI_API_KEY</code> នៅ Render env"
            elif "429" in err:
                tip = "\n\n⏱ Rate limit — រង់ចាំបន្តិច"
            else:
                tip = ""
            try:
                bot.edit_message_text(
                    f"❌ មិនអាចឆ្លើយបានទេ។{tip}\n<code>{err[:300]}</code>",
                    message.chat.id,
                    wait.message_id,
                )
            except Exception:
                bot.reply_to(message, f"❌ Error: {err[:300]}")


def main():
    log.info("Starting %s | model=%s", BOT_NAME, MODEL)
    # drop webhook if any, then polling
    try:
        bot.remove_webhook()
    except Exception:
        pass
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=50, skip_pending=True)
        except Exception as e:
            log.warning("polling crash: %s — restart in 3s", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
