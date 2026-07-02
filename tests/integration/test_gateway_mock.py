from pathlib import Path


def test_gateway_mock_injects_and_captures_reply(gateway, user_a):
    outbound = gateway.inject(
        user_id=user_a["user_id"],
        phone_hash=user_a["phone_hash"],
        text="Hi",
    )
    assert outbound.text
    assert "personal assistant" in outbound.text.lower()
    assert gateway.last_outbound() is outbound
    assert len(gateway.inbound_log) == 1


def test_gateway_replay_fixture(gateway):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "whatsapp_onboarding.json"
    outputs = gateway.replay_fixture(fixture)
    assert len(outputs) == 2
    assert "Reminder set" in outputs[1].text
