from __future__ import annotations

import hashlib
import logging
import re
from typing import Iterable

PHONE_PATTERN = re.compile(r"\+?\d{8,15}")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


class PIISafeFormatter(logging.Formatter):
    """Redacts phone numbers and email addresses from log records."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        message = PHONE_PATTERN.sub("[REDACTED_PHONE]", message)
        message = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", message)
        return message


def scan_text_for_pii(text: str) -> list[str]:
    findings: list[str] = []
    if PHONE_PATTERN.search(text):
        findings.append("phone")
    if EMAIL_PATTERN.search(text):
        findings.append("email")
    return findings


def assert_no_pii_in_lines(lines: Iterable[str]) -> None:
    for line in lines:
        if scan_text_for_pii(line):
            raise AssertionError(f"PII detected in log line: {line!r}")
