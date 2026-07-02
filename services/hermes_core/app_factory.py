from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from hermes_core.chat_store import ChatStore
from hermes_core.config import Settings
from hermes_core.gateway import MessageHandler
from hermes_core.llm import DeepSeekClient
from hermes_core.logging_safe import hash_phone
from hermes_core.models import InboundMessage, OutboundMessage
from hermes_core.reminders import ReminderService, ReminderStore
from hermes_core.token_budget import TokenBudgetService


class LLMMessageHandler(MessageHandler):
    """Rule-based routing with DeepSeek fallback for unmatched messages."""

    def __init__(
        self,
        reminder_service: ReminderService,
        token_budget: TokenBudgetService,
        llm: DeepSeekClient | None = None,
        chat_store: ChatStore | None = None,
        tz_name: str = "Asia/Hong_Kong",
    ) -> None:
        def now_fn() -> datetime:
            return datetime.now(ZoneInfo(tz_name))

        super().__init__(reminder_service, token_budget, now_fn=now_fn)
        self.llm = llm
        self.chat_store = chat_store
        self.tz_name = tz_name
        self._last_tokens_used = 0

    def handle(self, inbound: InboundMessage) -> OutboundMessage:
        now = self._now_fn()
        text = inbound.text.strip()
        estimate = self.token_budget.estimate_tokens(text)
        decision = self.token_budget.approve(inbound.user_id, estimate)
        if not decision.approved:
            return OutboundMessage(
                user_id=inbound.user_id,
                text=decision.message or "Daily limit reached.",
                sent_at=now,
            )

        reply = self._route(inbound.user_id, text, text.lower(), now)
        self.token_budget.record_usage(inbound.user_id, self._last_tokens_used or estimate)
        return OutboundMessage(user_id=inbound.user_id, text=reply, sent_at=now)

    def _route(self, user_id: str, text: str, lower: str, now: datetime) -> str:
        self._last_tokens_used = 0
        rule_reply = super()._route(user_id, text, lower, now)
        fallback = (
            "I'm not sure how to help with that yet. Try asking for a reminder, "
            'e.g. "Remind me to call mom at 3pm".'
        )
        if rule_reply != fallback or self.llm is None:
            self._last_tokens_used = self.token_budget.estimate_tokens(text)
            return rule_reply

        if self.reminder_service.looks_like_reminder_intent(text):
            self._last_tokens_used = self.token_budget.estimate_tokens(text)
            return self.reminder_service.clarification_message()

        history = []
        if self.chat_store:
            history = [
                {"role": m.role, "content": m.content}
                for m in self.chat_store.list_recent(user_id, limit=8)
            ]
        try:
            llm_reply = self.llm.chat(text, history=history)
        except RuntimeError:
            self._last_tokens_used = self.token_budget.estimate_tokens(text)
            return "Assistant is temporarily unavailable. Please try again."
        self._last_tokens_used = llm_reply.tokens_used
        return llm_reply.text


def build_handler(settings: Settings) -> LLMMessageHandler:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    reminder_store = ReminderStore(settings.database_path)
    reminder_service = ReminderService(reminder_store)
    token_budget = TokenBudgetService(daily_limit=settings.token_daily_limit)
    chat_store = ChatStore(settings.database_path)
    llm = (
        DeepSeekClient(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
        if settings.llm_enabled
        else None
    )
    return LLMMessageHandler(
        reminder_service=reminder_service,
        token_budget=token_budget,
        llm=llm,
        chat_store=chat_store,
        tz_name=settings.timezone,
    )


def pilot_phone_hash(user_id: str) -> str:
    return hash_phone(user_id)
