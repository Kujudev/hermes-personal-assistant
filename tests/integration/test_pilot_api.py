from fastapi.testclient import TestClient
from hermes_core.config import Settings
from pilot_api.main import create_app


def test_health_endpoint():
    settings = Settings.from_env()
    client = TestClient(create_app(settings))
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_chat_onboarding_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "chat.db"))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    settings = Settings.from_env()
    client = TestClient(create_app(settings))

    res = client.post("/api/chat", json={"message": "Hi"})
    assert res.status_code == 200
    assert "personal assistant" in res.json()["reply"].lower()

    res = client.post("/api/chat", json={"message": "Remind me to call mom at 3pm"})
    assert res.status_code == 200
    assert "Reminder set" in res.json()["reply"]


def test_pilot_pin_required(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "pin.db"))
    monkeypatch.setenv("PILOT_PIN", "secret-pin")
    settings = Settings.from_env()
    client = TestClient(create_app(settings))

    denied = client.post("/api/chat", json={"message": "Hi"})
    assert denied.status_code == 401

    ok = client.post(
        "/api/chat",
        json={"message": "Hi"},
        headers={"X-Pilot-Pin": "secret-pin"},
    )
    assert ok.status_code == 200


def test_telegram_webhook_requires_configured_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "telegram.db"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:telegram-token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")

    async def fake_send_telegram_reply(*args, **kwargs):
        return None

    monkeypatch.setattr("pilot_api.main._send_telegram_reply", fake_send_telegram_reply)
    settings = Settings.from_env()
    client = TestClient(create_app(settings))

    denied = client.post(
        "/api/telegram/webhook",
        json={"message": {"text": "Hi", "chat": {"id": 42}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )
    assert denied.status_code == 401

    ok = client.post(
        "/api/telegram/webhook",
        json={"message": {"text": "Hi", "chat": {"id": 42}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )
    assert ok.status_code == 200
    assert ok.json() == {"ok": True}


def test_telegram_webhook_degrades_gracefully_when_llm_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "telegram-fallback.db"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:telegram-token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "enabled")

    async def fake_send_telegram_reply(*args, **kwargs):
        return None

    monkeypatch.setattr("pilot_api.main._send_telegram_reply", fake_send_telegram_reply)

    class FailingLLM:
        def chat(self, user_message, history=None):
            raise RuntimeError("Assistant is temporarily unavailable. Please try again.")

    settings = Settings.from_env()
    app = create_app(settings)
    app.state.handler.llm = FailingLLM()
    client = TestClient(app)

    res = client.post(
        "/api/telegram/webhook",
        json={"message": {"text": "Tell me a joke", "chat": {"id": 42}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True}
