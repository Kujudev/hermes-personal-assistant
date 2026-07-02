from __future__ import annotations

import pytest
from hermes_core.auth import AuthService
from hermes_core.gateway import MessageHandler, WhatsAppGatewayMock
from hermes_core.reminders import ReminderService, ReminderStore
from hermes_core.token_budget import TokenBudgetService


@pytest.fixture
def tmp_db(tmp_path):
    return ReminderStore(tmp_path / "test.db")


@pytest.fixture
def reminder_service(tmp_db):
    return ReminderService(tmp_db)


@pytest.fixture
def token_budget():
    return TokenBudgetService(daily_limit=50_000)


@pytest.fixture
def handler(reminder_service, token_budget):
    return MessageHandler(reminder_service, token_budget)


@pytest.fixture
def gateway(handler):
    return WhatsAppGatewayMock(handler)


@pytest.fixture
def auth_service():
    return AuthService(secret="test-secret-key-for-ci-only-32bx")


@pytest.fixture
def user_a():
    return {"user_id": "user-a", "phone_hash": "hash-a", "phone": "+85290000001"}


@pytest.fixture
def user_b():
    return {"user_id": "user-b", "phone_hash": "hash-b", "phone": "+85290000002"}
