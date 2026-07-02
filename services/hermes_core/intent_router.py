from __future__ import annotations

import re

from hermes_core.models import Complexity, Domain, Intent

DOMAIN_KEYWORDS: dict[Domain, tuple[str, ...]] = {
    Domain.PERSONAL: (
        "remind",
        "reminder",
        "schedule",
        "calendar",
        "habit",
        "call mom",
        "call dad",
    ),
    Domain.FINANCE: (
        "spent",
        "spend",
        "budget",
        "expense",
        "dining",
        "groceries",
        "money",
        "$",
        "hkd",
    ),
    Domain.WORK: (
        "inbox",
        "email",
        "meeting",
        "report",
        "urgent",
        "summarize",
    ),
    Domain.DAILY_OPS: (
        "shopping",
        "list",
        "milk",
        "groceries list",
        "add ",
        "remove ",
    ),
    Domain.LEARNING: (
        "learn",
        "lesson",
        "study",
        "blockchain",
        "course",
        "reading list",
    ),
}

HIGH_COMPLEXITY_PATTERNS = (
    re.compile(r"summarize", re.I),
    re.compile(r"research", re.I),
    re.compile(r"learning plan", re.I),
    re.compile(r"inbox", re.I),
)


class IntentRouter:
    """Cheap keyword-based intent router for Phase 0/1."""

    def classify(self, message: str) -> Intent:
        normalized = message.strip().lower()
        if not normalized:
            return Intent(Domain.UNKNOWN, Complexity.LOW, 0.0)

        scores: dict[Domain, int] = {domain: 0 for domain in Domain if domain != Domain.UNKNOWN}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    scores[domain] += 1

        best_domain = max(scores, key=scores.get)
        best_score = scores[best_domain]
        if best_score == 0:
            return Intent(Domain.UNKNOWN, Complexity.LOW, 0.0)

        is_high = any(p.search(normalized) for p in HIGH_COMPLEXITY_PATTERNS)
        complexity = Complexity.HIGH if is_high else Complexity.LOW
        confidence = min(1.0, best_score / 3.0)
        return Intent(best_domain, complexity, confidence)
