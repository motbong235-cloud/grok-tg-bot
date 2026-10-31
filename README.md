# Porpor Fix AI (Grok Telegram)

AI for **Porpor Topup** maintenance — **text + image vision**.

## Env
| Key | Required | Notes |
|-----|----------|--------|
| TELEGRAM_BOT_TOKEN | yes | BotFather |
| XAI_API_KEY | yes | console.x.ai |
| GROK_MODEL | no | default `grok-3` |
| GROK_VISION_MODEL | no | default `grok-2-vision-1212` |
| BOT_NAME | no | Porpor Fix AI |

## Features
- Chat text (Grok)
- **Screenshot / photo** → Grok Vision analyzes UI bugs
- Memory per user
- Scope: Porpor Topup only

## Deploy Render
build: `pip install -r requirements.txt`  
start: `python bot.py`
