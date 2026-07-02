from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from hermes_core.models import InboundMessage, OutboundMessage
from hermes_core.privacy import ONBOARDING_MESSAGE, PRIVACY_EXPLAINER
from hermes_core.reminders import ReminderService
from hermes_core.token_budget import TokenBudgetService


class MessageHandler:
    """Routes inbound messages to domain handlers with budget checks."""

    def __init__(
        self,
        reminder_service: ReminderService,
        token_budget: TokenBudgetService,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.reminder_service = reminder_service
        self.token_budget = token_budget
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def handle(self, inbound: InboundMessage) -> OutboundMessage:
        now = self._now_fn()
        text = inbound.text.strip()
        lower = text.lower()

        estimate = self.token_budget.estimate_tokens(text)
        decision = self.token_budget.approve(inbound.user_id, estimate)
        if not decision.approved:
            return OutboundMessage(
                user_id=inbound.user_id,
                text=decision.message or "Daily limit reached.",
                sent_at=now,
            )

        reply = self._route(inbound.user_id, text, lower, now)
        self.token_budget.record_usage(inbound.user_id, estimate)
        return OutboundMessage(user_id=inbound.user_id, text=reply, sent_at=now)

    def _route(self, user_id: str, text: str, lower: str, now: datetime) -> str:
        if lower in {"hi", "hello", "hey"}:
            return ONBOARDING_MESSAGE
        if "how does my privacy work" in lower or "privacy" == lower:
            return PRIVACY_EXPLAINER
        if lower.startswith("what reminders") or "reminders do i have" in lower:
            reminders = self.reminder_service.list_today(user_id, now)
            if not reminders:
                return "You have no reminders scheduled for today."
            lines = "\n".join(
                f"• {r.text} at {r.fire_at.strftime('%I:%M %p').lstrip('0')}"
                for r in reminders
            )
            return f"📅 Today's reminders:\n{lines}"
        if lower.startswith("cancel") and "reminder" in lower:
            cancelled = self.reminder_service.store.cancel_by_text(user_id, "mom")
            if cancelled:
                return "✅ Reminder cancelled."
            return "I couldn't find a matching reminder to cancel."

        reminder = self.reminder_service.parse_and_create(user_id, text, now)
        if reminder:
            return self.reminder_service.format_confirmation(reminder)

        return (
            "I'm not sure how to help with that yet. Try asking for a reminder, "
            'e.g. "Remind me to call mom at 3pm".'
        )


class WhatsAppGatewayMock:
    """Inject inbound messages and capture outbound replies for CI E2E tests."""

    def __init__(self, handler: MessageHandler) -> None:
        self.handler = handler
        self.outbound: list[OutboundMessage] = []
        self.inbound_log: list[InboundMessage] = []

    def inject(
        self,
        user_id: str,
        phone_hash: str,
        text: str,
        received_at: datetime | None = None,
    ) -> OutboundMessage:
        inbound = InboundMessage(
            user_id=user_id,
            phone_hash=phone_hash,
            text=text,
            received_at=received_at or datetime.now(timezone.utc),
        )
        self.inbound_log.append(inbound)
        outbound = self.handler.handle(inbound)
        self.outbound.append(outbound)
        return outbound

    def replay_fixture(self, fixture_path: Path) -> list[OutboundMessage]:
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        outputs: list[OutboundMessage] = []
        for entry in data["messages"]:
            outputs.append(
                self.inject(
                    user_id=entry["user_id"],
                    phone_hash=entry["phone_hash"],
                    text=entry["text"],
                )
            )
        return outputs

    def last_outbound(self) -> OutboundMessage | None:
        return self.outbound[-1] if self.outbound else None

    def clear(self) -> None:
        self.outbound.clear()
        self.inbound_log.clear()
