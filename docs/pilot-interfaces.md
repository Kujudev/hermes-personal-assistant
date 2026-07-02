# Pilot Interfaces (WhatsApp Alternatives)

Until WhatsApp Business API credentials are ready, use these channels for the **same assistant experience** during Phase 1 pilot.

## 1. Web Chat (recommended — ready now)

**URL:** `https://paserver.kujuhk.com`

| Feature | Detail |
|---------|--------|
| UX | WhatsApp-style bubbles, mobile-first |
| Install | “Add to Home Screen” on iPhone/Android for app-like access |
| Reminders | Background worker pushes due reminders into chat (polls every 15s) |
| LLM | DeepSeek for natural conversation beyond rule-based skills |
| Auth | Optional `PILOT_PIN` in `.env` — enter in PIN field on page |

This is your **primary pilot interface** until WhatsApp is wired.

## 2. Telegram (optional — when you have a bot token)

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Set in `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_WEBHOOK_SECRET=random-secret-string
   ```
3. Register webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://paserver.kujuhk.com/api/telegram/webhook" \
     -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
   ```
4. Message your bot — same Hermes brain, familiar chat UX

## 3. WhatsApp (later)

When credentials arrive, add to `.env`:
```
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
```
Webhook route will be added at `/api/whatsapp/webhook` in a follow-up.

## Deployment

See [pilot-deployment.md](./pilot-deployment.md).
