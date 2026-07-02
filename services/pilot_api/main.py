from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from hermes_core.app_factory import build_handler, pilot_phone_hash
from hermes_core.chat_store import ChatStore
from hermes_core.config import Settings
from hermes_core.gateway import WhatsAppGatewayMock
from hermes_core.logging_safe import PIISafeFormatter
from pydantic import BaseModel, Field

from pilot_api.reminder_worker import NotificationStore

logger = logging.getLogger("hermes.pilot")
_handler = logging.StreamHandler()
_handler.setFormatter(PIISafeFormatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    sent_at: str


class TelegramUpdate(BaseModel):
    message: dict[str, Any] | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    handler = build_handler(settings)
    gateway = WhatsAppGatewayMock(handler)
    chat_store = ChatStore(settings.database_path)
    notifications = NotificationStore(settings.database_path)

    app = FastAPI(title="Hermes Pilot", version="0.1.0")
    app.state.handler = handler

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "llm": "enabled" if settings.llm_enabled else "disabled"}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(
        body: ChatRequest,
        x_pilot_pin: str | None = Header(default=None),
    ) -> ChatResponse:
        _authorize_pilot(settings, x_pilot_pin)
        user_id = settings.pilot_user_id
        now = datetime.now(ZoneInfo(settings.timezone))
        chat_store.add(user_id, "user", body.message, now)
        outbound = gateway.inject(user_id, pilot_phone_hash(user_id), body.message, now)
        chat_store.add(user_id, "assistant", outbound.text, outbound.sent_at)
        logger.info("Pilot chat handled for user_id=%s", user_id)
        return ChatResponse(reply=outbound.text, sent_at=outbound.sent_at.isoformat())

    @app.get("/api/chat/history")
    def history(x_pilot_pin: str | None = Header(default=None)) -> list[dict[str, str]]:
        _authorize_pilot(settings, x_pilot_pin)
        messages = chat_store.list_recent(settings.pilot_user_id, limit=100)
        return [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

    @app.get("/api/notifications/poll")
    def poll_notifications(x_pilot_pin: str | None = Header(default=None)) -> list[dict[str, str]]:
        _authorize_pilot(settings, x_pilot_pin)
        user_id = settings.pilot_user_id
        pending = notifications.list_undelivered(user_id)
        result = [
            {"id": n.id, "content": n.content, "created_at": n.created_at.isoformat()}
            for n in pending
        ]
        for n in pending:
            notifications.mark_delivered(n.id, user_id)
        return result

    @app.post("/api/telegram/webhook")
    async def telegram_webhook(update: TelegramUpdate, request: Request) -> JSONResponse:
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=503, detail="Telegram not configured")
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        expected = settings.telegram_webhook_secret or settings.telegram_bot_token[-16:]
        if expected and token != expected:
            raise HTTPException(status_code=401, detail="Invalid telegram webhook token")

        message = update.message or {}
        text = message.get("text")
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not text or not chat_id:
            return JSONResponse({"ok": True})

        user_id = f"telegram-{chat_id}"
        now = datetime.now(ZoneInfo(settings.timezone))
        try:
            outbound = gateway.inject(user_id, pilot_phone_hash(chat_id), text, now)
        except RuntimeError:
            outbound = type(
                "Outbound",
                (),
                {"text": "Assistant is temporarily unavailable. Please try again."},
            )()
        await _send_telegram_reply(settings.telegram_bot_token, chat_id, outbound.text)
        return JSONResponse({"ok": True})

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def _authorize_pilot(settings: Settings, pin: str | None) -> None:
    if settings.pilot_pin and pin != settings.pilot_pin:
        raise HTTPException(status_code=401, detail="Invalid pilot PIN")


async def _send_telegram_reply(bot_token: str, chat_id: str, text: str) -> None:
    import urllib.parse
    import urllib.request

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        urllib.request.urlopen(request, timeout=15)
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)


app = create_app()
