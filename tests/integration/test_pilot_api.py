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
