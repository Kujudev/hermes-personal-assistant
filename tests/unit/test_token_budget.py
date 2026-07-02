
from hermes_core.token_budget import LIMIT_REACHED_MESSAGE, TokenBudgetService


def test_token_budget_approves_within_limit():
    budget = TokenBudgetService(daily_limit=1000)
    decision = budget.approve("user-1", 200)
    assert decision.approved is True
    assert decision.remaining == 800


def test_token_budget_denies_over_limit():
    budget = TokenBudgetService(daily_limit=1000)
    budget.record_usage("user-1", 900)
    decision = budget.approve("user-1", 200)
    assert decision.approved is False
    assert decision.message == LIMIT_REACHED_MESSAGE


def test_token_budget_counter_accuracy():
    budget = TokenBudgetService(daily_limit=10_000)
    usages = [120, 80, 300, 50]
    for amount in usages:
        decision = budget.approve("user-1", amount)
        assert decision.approved
        budget.record_usage("user-1", amount)
    assert budget.get_usage("user-1") == sum(usages)
