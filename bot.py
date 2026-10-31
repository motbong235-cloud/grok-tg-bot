#!/usr/bin/env python3
"""
Porpor Fix AI — Grok Telegram bot (text + image vision)
Env:
  TELEGRAM_BOT_TOKEN
  XAI_API_KEY
  GROK_MODEL          default grok-3
  GROK_VISION_MODEL   default grok-2-vision-1212
  BOT_NAME            default Porpor Fix AI
  SYSTEM_PROMPT       optional
  MAX_HISTORY         default 12
"""
from __future__ import annotations

import os
import io
import time
import base64
import logging
import threading
from collections import defaultdict, deque

import requests
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("porpor-fix-ai")

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
XAI_KEY = (os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY") or "").strip()
MODEL = (os.getenv("GROK_MODEL") or "grok-3").strip()
VISION_MODEL = (os.getenv("GROK_VISION_MODEL") or "grok-2-vision-1212").strip()
BOT_NAME = (os.getenv("BOT_NAME") or "Porpor Fix AI").strip()
MAX_HISTORY = int(os.getenv("MAX_HISTORY") or "12")
XAI_URL = (os.getenv("XAI_API_URL") or "https://api.x.ai/v1/chat/completions").strip()

DEFAULT_SYSTEM = """អ្នកជា AI Maintenance Assistant សម្រាប់គម្រោង **Porpor Topup** តែប៉ុណ្ណោះ។
ឈ្មោះ: {name} · Powered by Grok (xAI).

## តួនាទី
- ផ្តោតតែការថែទាំ / fix / កែ UI·UX / payment (ABA PayWay·KHQR) / admin / deploy Render នៃ Porpor Topup
- Repo: github.com/motbong235-cloud/porpor-topup
- Live: porportopup.com · Admin /pp-console
- កុំនិយាយអំពីគម្រោងផ្សេង លុះតែអ្នកប្រើសួរច្បាស់

## រូបភាព
- បើមានរូប (screenshot error, UI, admin) — ពិពណ៌នាអ្វីដែលឃើញ រួចឲ្យជំហាន fix
- ចង្អុលបង្ហាញ bug / UI មិនស្រួល / អត្ថបទខុស

## របៀបឆ្លើយ
- ភាសាខ្មែរ បើគេសរសេរខ្មែរ
- ខ្លី ច្បាស់ · ជំហាន 1,2,3
- បើត្រូវកែកូដ: ប្រាប់ file · ថា «សុំ Grok chat ធ្វើ commit + push porpor-topup»
""".format(name=BOT_NAME)

SYSTEM_PROMPT = (os.getenv("SYSTEM_PROMPT") or DEFAULT_SYSTEM).strip()

if not TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN")
if not XAI_KEY:
    raise SystemExit("Missing XAI_API_KEY")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
user_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)


def call_grok(messages: list, *, model: str | None = None) -> str:
    headers = {
        "Authorization": f"Bearer {XAI_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or MODEL,
        "messages": messages,
        "temperature": 0.6,
        "stream": False,
    }
    r = requests.post(XAI_URL, headers=headers, json=payload, timeout=120)
    if r.status_code >= 400:
        log.warning("xAI %s: %s", r.status_code, r.text[:500])
        try:
            err = r.json().get("error") or r.json()
        except Exception:
            err = r.text[:250]
        raise RuntimeError(f"Grok API {r.status_code}: {err}")
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Empty response from Grok")
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        raise RuntimeError("Empty content from Grok")
    return content


def remember_text(uid: int, role: str, content: str):
    histories[uid].append({"role": role, "content": content})


def history_as_messages(uid: int) -> list:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in histories[uid]:
        msgs.append({"role": m["role"], "content": m["content"]})
    return msgs


def download_telegram_file(file_id: str) -> tuple[bytes, str]:
    info = bot.get_file(file_id)
    path = info.file_path or ""
    url = f"https://api.telegram.org/file/bot{TOKEN}/{path}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    mime = "image/jpeg"
    low = path.lower()
    if low.endswith(".png"):
        mime = "image/png"
    elif low.endswith(".webp"):
        mime = "image/webp"
    elif low.endswith(".gif"):
        mime = "image/gif"
    return r.content, mime


def image_to_data_url(data: bytes, mime: str) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💬 Chat", "🗑 Clear memory")
    kb.row("ℹ️ About", "🖼 Send screenshot")
    return kb


@bot.message_handler(commands=["start", "help"])
def cmd_start(message: types.Message):
    name = message.from_user.first_name or "friend"
    bot.send_message(
        message.chat.id,
        f"សួស្តី <b>{name}</b> 👋\n"
        f"ខ្ញុំ <b>{BOT_NAME}</b> — AI ថែទាំ <b>Porpor Topup</b>\n"
        f"(Grok · text + <b>vision</b>)\n\n"
        f"ផ្ញើ <b>សារ</b> ឬ <b>screenshot</b> មក — ខ្ញុំមើលរូប និងណែនាំ fix។\n"
        f"· /clear — លុប memory\n"
        f"· Model: <code>{MODEL}</code> · Vision: <code>{VISION_MODEL}</code>",
        reply_markup=main_kb(),
    )


@bot.message_handler(commands=["clear", "reset"])
def cmd_clear(message: types.Message):
    histories[message.from_user.id].clear()
    bot.reply_to(message, "✅ Memory cleared")


@bot.message_handler(commands=["about"])
def cmd_about(message: types.Message):
    bot.reply_to(
        message,
        f"<b>{BOT_NAME}</b>\n"
        f"Porpor Topup maintenance only\n"
        f"Text: <code>{MODEL}</code>\n"
        f"Vision: <code>{VISION_MODEL}</code>\n"
        f"ផ្ញើរូប screenshot បាន",
    )


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("🗑 Clear memory", "Clear memory"))
def btn_clear(message: types.Message):
    cmd_clear(message)


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("ℹ️ About", "About"))
def btn_about(message: types.Message):
    cmd_about(message)


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("🖼 Send screenshot", "Send screenshot"))
def btn_shot(message: types.Message):
    bot.reply_to(message, "ផ្ញើរូប screenshot នៃ bug / UI / error មកតែម្តង។")


@bot.message_handler(func=lambda m: (m.text or "").strip() in ("💬 Chat", "Chat"))
def btn_chat(message: types.Message):
    bot.reply_to(message, "សរសេរសំណួរ ឬផ្ញើរូប…")


def reply_with_grok(message: types.Message, user_content, *, model: str, remember_user: str):
    uid = message.from_user.id
    with user_locks[uid]:
        wait = bot.send_message(message.chat.id, "⏳ Grok កំពុងមើល…")
        try:
            msgs = history_as_messages(uid)
            msgs.append({"role": "user", "content": user_content})
            answer = call_grok(msgs, model=model)
            remember_text(uid, "user", remember_user)
            remember_text(uid, "assistant", answer)
            if len(answer) > 4000:
                answer = answer[:4000] + "…"
            try:
                bot.edit_message_text(answer, message.chat.id, wait.message_id)
            except Exception:
                bot.send_message(message.chat.id, answer)
        except Exception as e:
            log.exception("grok fail")
            err = str(e)
            tip = ""
            if "401" in err:
                tip = "\n🔑 ពិនិត្យ XAI_API_KEY"
            elif "429" in err:
                tip = "\n⏱ Rate limit — រង់ចាំបន្តិច"
            try:
                bot.edit_message_text(
                    f"❌ មិនបាន\n<code>{err[:350]}</code>{tip}",
                    message.chat.id,
                    wait.message_id,
                )
            except Exception:
                bot.reply_to(message, f"❌ {err[:350]}")


@bot.message_handler(content_types=["photo"])
def on_photo(message: types.Message):
    """Largest photo size → vision model."""
    photos = message.photo or []
    if not photos:
        return
    file_id = photos[-1].file_id
    caption = (message.caption or "").strip() or "នេះជា screenshot នៃ Porpor Topup។ សូមវិភាគ និងប្រាប់វិធី fix។"
    try:
        data, mime = download_telegram_file(file_id)
        # limit ~4MB base64 safety
        if len(data) > 4_500_000:
            bot.reply_to(message, "រូបធំពេក — បង្រួម ឬ crop សិន")
            return
        data_url = image_to_data_url(data, mime)
    except Exception as e:
        bot.reply_to(message, f"❌ ទាញរូបមិនបាន: {e}")
        return

    user_content = [
        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
        {"type": "text", "text": caption},
    ]
    reply_with_grok(
        message,
        user_content,
        model=VISION_MODEL,
        remember_user=f"[image] {caption}",
    )


@bot.message_handler(content_types=["document"])
def on_document(message: types.Message):
    doc = message.document
    if not doc:
        return
    mime = (doc.mime_type or "").lower()
    name = (doc.file_name or "").lower()
    if not (mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))):
        bot.reply_to(message, "ផ្ញើជា photo ឬ file រូប (png/jpg) សម្រាប់ vision")
        return
    caption = (message.caption or "").strip() or "Screenshot Porpor — វិភាគ និង fix"
    try:
        data, mime2 = download_telegram_file(doc.file_id)
        if len(data) > 4_500_000:
            bot.reply_to(message, "រូបធំពេក")
            return
        if not mime.startswith("image/"):
            mime = mime2
        data_url = image_to_data_url(data, mime if mime.startswith("image/") else mime2)
    except Exception as e:
        bot.reply_to(message, f"❌ {e}")
        return
    user_content = [
        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
        {"type": "text", "text": caption},
    ]
    reply_with_grok(message, user_content, model=VISION_MODEL, remember_user=f"[image] {caption}")


@bot.message_handler(content_types=["text"])
def on_text(message: types.Message):
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    if text in ("💬 Chat", "🗑 Clear memory", "ℹ️ About", "🖼 Send screenshot", "Chat", "About"):
        return
    reply_with_grok(message, text, model=MODEL, remember_user=text)


def main():
    log.info("Start %s | text=%s vision=%s", BOT_NAME, MODEL, VISION_MODEL)
    try:
        bot.remove_webhook()
    except Exception:
        pass
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=50, skip_pending=True)
        except Exception as e:
            log.warning("polling: %s", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
