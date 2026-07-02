from datetime import datetime, timezone

import pytest
from freezegun import freeze_time

from tests.fixtures.messages import CANCEL_MOM, LIST_TODAY, REMIND_MOM


@pytest.mark.acceptance
@pytest.mark.phase1
@freeze_time("2026-07-01 10:00:00", tz_offset=0)
def test_acc_pl_01_remind_call_mom_at_3pm(gateway, user_a, reminder_service):
    outbound = gateway.inject(
        user_id=user_a["user_id"],
        phone_hash=user_a["phone_hash"],
        text=REMIND_MOM,
    )
    assert "Reminder set" in outbound.text
    assert "call mom" in outbound.text.lower()
    assert "3:00" in outbound.text or "3pm" in outbound.text.lower()

    with freeze_time("2026-07-01 15:00:30", tz_offset=0):
        fired = reminder_service.process_due(datetime.now(timezone.utc))
    assert len(fired) == 1
    assert "call mom" in fired[0][1].lower()


@pytest.mark.acceptance
@pytest.mark.phase1
@freeze_time("2026-07-01 09:00:00", tz_offset=0)
def test_acc_pl_02_list_today_reminders(gateway, user_a):
    gateway.inject(user_a["user_id"], user_a["phone_hash"], REMIND_MOM)
    outbound = gateway.inject(user_a["user_id"], user_a["phone_hash"], LIST_TODAY)
    assert "call mom" in outbound.text.lower()


@pytest.mark.acceptance
@pytest.mark.phase1
@freeze_time("2026-07-01 09:00:00", tz_offset=0)
def test_acc_pl_03_cancel_reminder(gateway, user_a, reminder_service):
    gateway.inject(user_a["user_id"], user_a["phone_hash"], REMIND_MOM)
    outbound = gateway.inject(user_a["user_id"], user_a["phone_hash"], CANCEL_MOM)
    assert "cancelled" in outbound.text.lower()

    with freeze_time("2026-07-01 15:00:30", tz_offset=0):
        fired = reminder_service.process_due(datetime.now(timezone.utc))
    assert len(fired) == 0


@pytest.mark.acceptance
@pytest.mark.phase1
@freeze_time("2026-07-01 09:00:00", tz_offset=0)
def test_acc_pl_04_reminder_supports_tonight_by_time(gateway, user_a, reminder_service):
    outbound = gateway.inject(
        user_a["user_id"],
        user_a["phone_hash"],
        "Remind me to have dinner with friends by tonight 18:45",
    )
    assert "Reminder set" in outbound.text
    reminders = reminder_service.store.list_for_user(user_a["user_id"])
    assert len(reminders) == 1
    assert reminders[0].text == "have dinner with friends"
    assert reminders[0].fire_at.hour == 18
    assert reminders[0].fire_at.minute == 45


@pytest.mark.acceptance
@pytest.mark.phase1
@freeze_time("2026-07-01 09:00:00", tz_offset=0)
def test_acc_pl_05_reminder_asks_clarification_when_time_missing(gateway, user_a, reminder_service):
    outbound = gateway.inject(
        user_a["user_id"], user_a["phone_hash"], "Remind me to have dinner with friends tonight"
    )
    assert "what time" in outbound.text.lower() or "exact time" in outbound.text.lower()
    reminders = reminder_service.store.list_for_user(user_a["user_id"])
    assert reminders == []


@pytest.mark.acceptance
@pytest.mark.phase1
def test_acc_ux_01_onboarding(gateway, user_a):
    outbound = gateway.inject(user_a["user_id"], user_a["phone_hash"], "Hi")
    assert "👋" in outbound.text
    assert "Reminders" in outbound.text or "reminders" in outbound.text.lower()
    assert len(outbound.text) < 1200


@pytest.mark.acceptance
@pytest.mark.phase1
def test_acc_ux_02_privacy_explainer(gateway, user_a):
    outbound = gateway.inject(user_a["user_id"], user_a["phone_hash"], "How does my privacy work?")
    assert "private" in outbound.text.lower()
    assert "encrypted" in outbound.text.lower()
