from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Domain(str, Enum):
    PERSONAL = "personal"
    WORK = "work"
    FINANCE = "finance"
    DAILY_OPS = "daily_ops"
    LEARNING = "learning"
    UNKNOWN = "unknown"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Intent:
    domain: Domain
    complexity: Complexity
    confidence: float


@dataclass(frozen=True)
class BudgetDecision:
    approved: bool
    message: Optional[str] = None
    remaining: Optional[int] = None


@dataclass
class Reminder:
    id: str
    user_id: str
    text: str
    fire_at: datetime
    sent: bool = False
    cancelled: bool = False


@dataclass(frozen=True)
class InboundMessage:
    user_id: str
    phone_hash: str
    text: str
    received_at: datetime


@dataclass(frozen=True)
class OutboundMessage:
    user_id: str
    text: str
    sent_at: datetime
