from __future__ import annotations

from hermes_core.models import BudgetDecision

LIMIT_REACHED_MESSAGE = (
    "I've reached my daily limit. Try again tomorrow or ask my admin."
)


class TokenBudgetService:
    """In-memory token budget enforcement (Redis-backed in later phases)."""

    def __init__(self, daily_limit: int) -> None:
        self.daily_limit = daily_limit
        self._usage: dict[str, int] = {}

    def estimate_tokens(self, message: str) -> int:
        # Rough heuristic: ~4 chars per token, minimum 50 for routing overhead.
        return max(50, len(message) // 4 + 100)

    def get_usage(self, user_id: str) -> int:
        return self._usage.get(user_id, 0)

    def approve(self, user_id: str, estimate: int) -> BudgetDecision:
        current = self.get_usage(user_id)
        if current + estimate > self.daily_limit:
            return BudgetDecision(approved=False, message=LIMIT_REACHED_MESSAGE, remaining=0)
        return BudgetDecision(
            approved=True,
            remaining=self.daily_limit - current - estimate,
        )

    def record_usage(self, user_id: str, actual: int) -> None:
        self._usage[user_id] = self.get_usage(user_id) + actual

    def reset_daily(self, user_id: str | None = None) -> None:
        if user_id is None:
            self._usage.clear()
        else:
            self._usage.pop(user_id, None)
