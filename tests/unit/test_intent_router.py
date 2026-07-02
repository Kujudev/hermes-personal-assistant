import pytest
from hermes_core.intent_router import IntentRouter
from hermes_core.models import Complexity, Domain


@pytest.mark.parametrize(
    ("message", "domain", "complexity"),
    [
        ("Remind me to call mom at 3pm", Domain.PERSONAL, Complexity.LOW),
        ("Spent $45 on lunch", Domain.FINANCE, Complexity.LOW),
        ("What's in my inbox?", Domain.WORK, Complexity.HIGH),
        ("Add milk to shopping list", Domain.DAILY_OPS, Complexity.LOW),
        ("I want to learn about blockchain", Domain.LEARNING, Complexity.LOW),
    ],
)
def test_intent_router_classifies_domains(message, domain, complexity):
    router = IntentRouter()
    intent = router.classify(message)
    assert intent.domain == domain
    assert intent.complexity == complexity
    assert intent.confidence > 0


def test_intent_router_unknown_message():
    router = IntentRouter()
    intent = router.classify("   ")
    assert intent.domain == Domain.UNKNOWN
