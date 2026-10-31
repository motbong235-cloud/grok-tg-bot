# Grok AI Telegram Bot

Telegram bot powered by **xAI Grok API**.

## Env
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `XAI_API_KEY` — from https://console.x.ai
- `GROK_MODEL` — default `grok-3` (or `grok-2`, `grok-3-mini`)
- `SYSTEM_PROMPT` — optional custom personality (Khmer/English)
- `ADMIN_ID` — optional Telegram user id

## Local
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export XAI_API_KEY=...
python bot.py
```

## Render
Web service · start `python bot.py` · set env vars above.
