import logging
from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from hermes_core.logging_safe import PIISafeFormatter, assert_no_pii_in_lines
from hermes_core.reminders import ReminderService, ReminderStore

from tests.fixtures.messages import REMIND_MOM


@pytest.mark.guardrail
def test_gr_iso_01_user_reminder_isolation(tmp_path, user_a, user_b):
    store = ReminderStore(tmp_path / "iso.db")
    service = ReminderService(store)
    now = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)

    service.parse_and_create(user_a["user_id"], "Remind me to buy flowers at 5pm", now)
    user_b_reminders = store.list_for_user(user_b["user_id"])
    assert user_b_reminders == []


@pytest.mark.guardrail
@pytest.mark.phase3
def test_gr_iso_02_tenant_rls_not_implemented():
    pytest.skip("PostgreSQL RLS enforced in Phase 3 Aide stack")


@pytest.mark.guardrail
@pytest.mark.phase3
def test_gr_iso_03_filesystem_isolation_not_implemented():
    pytest.skip("Hermes profile filesystem isolation verified in Phase 3")


@pytest.mark.guardrail
def test_gr_auth_01_unauthenticated_rejection(auth_service):
    with pytest.raises(PermissionError, match="Unauthorized"):
        auth_service.require_auth(None)
    with pytest.raises(PermissionError, match="Unauthorized"):
        auth_service.require_auth("not-a-valid-jwt")


@pytest.mark.guardrail
@pytest.mark.phase3
def test_gr_auth_02_cross_tenant_token_rejected(auth_service):
    token = auth_service.issue_token("user-1", tenant_id="tenant-a")
    ctx = auth_service.validate(token)
    assert ctx is not None
    assert auth_service.validate_tenant_access(ctx, "tenant-b") is False


@pytest.mark.guardrail
def test_gr_budget_01_hard_cap_blocks_llm_path(gateway, user_a, token_budget):
    token_budget.daily_limit = 10
    outbound = gateway.inject(user_a["user_id"], user_a["phone_hash"], REMIND_MOM)
    assert "daily limit" in outbound.text.lower()


@pytest.mark.guardrail
def test_gr_budget_02_counter_matches_recorded_usage(token_budget):
    token_budget.record_usage("user-1", 100)
    token_budget.record_usage("user-1", 250)
    assert token_budget.get_usage("user-1") == 350


@pytest.mark.guardrail
def test_gr_sec_01_no_plaintext_pii_in_logs(user_a):
    logger = logging.getLogger("hermes.test.pii")
    handler = logging.StreamHandler()
    handler.setFormatter(PIISafeFormatter("%(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)

    captured: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(handler.format(record))

    list_handler = ListHandler()
    list_handler.setFormatter(PIISafeFormatter("%(message)s"))
    logger.addHandler(list_handler)

    logger.info("User phone %s contacted support", user_a["phone"])
    assert_no_pii_in_lines(captured)
    assert "[REDACTED_PHONE]" in captured[0]


@pytest.mark.guardrail
@pytest.mark.phase2
def test_gr_sec_02_encryption_at_rest_not_implemented():
    pytest.skip("SQLCipher encryption enabled in Phase 2 personal production")


@pytest.mark.guardrail
def test_gr_sec_03_no_secrets_in_repo():
    import subprocess

    result = subprocess.run(
        ["bash", "scripts/check_secrets.sh"],
        cwd="/workspace",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.guardrail
@pytest.mark.phase2
def test_gr_del_01_right_to_erasure(tmp_path, user_a):
    store = ReminderStore(tmp_path / "erase.db")
    service = ReminderService(store)
    now = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    service.parse_and_create(user_a["user_id"], "Remind me to stretch at 8am", now)
    deleted = store.delete_all_for_user(user_a["user_id"])
    assert deleted >= 1
    assert store.list_for_user(user_a["user_id"]) == []


@pytest.mark.guardrail
@pytest.mark.phase1
@freeze_time("2026-07-01 14:59:30", tz_offset=0)
def test_gr_cron_01_reminder_delivery_within_window(tmp_path, user_a):
    store = ReminderStore(tmp_path / "cron.db")
    service = ReminderService(store)
    service.parse_and_create(
        user_a["user_id"], REMIND_MOM, datetime.now(timezone.utc)
    )

    with freeze_time("2026-07-01 15:00:30", tz_offset=0):
        fired = service.process_due(datetime.now(timezone.utc))
    assert len(fired) == 1


@pytest.mark.guardrail
@pytest.mark.phase1
def test_gr_cron_02_idempotent_cron_tick(tmp_path, user_a):
    store = ReminderStore(tmp_path / "cron-idem.db")
    service = ReminderService(store)

    with freeze_time("2026-07-01 10:00:00", tz_offset=0):
        service.parse_and_create(
            user_a["user_id"], REMIND_MOM, datetime.now(timezone.utc)
        )

    with freeze_time("2026-07-01 15:00:30", tz_offset=0):
        now = datetime.now(timezone.utc)
        first = service.process_due(now)
        second = service.process_due(now)
    assert len(first) == 1
    assert len(second) == 0
