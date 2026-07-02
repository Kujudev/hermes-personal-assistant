from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from hermes_core.models import Reminder

REMINDER_CREATE_PATTERNS = (
    re.compile(
        r"remind(?:\s+me)?\s+(?:to\s+)?(.+?)\s+(?:at|by)"
        r"(?:\s+(?:today|tonight|this evening))?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        re.I,
    ),
    re.compile(
        r"remind(?:\s+me)?\s+(?:to\s+)?(.+?)\s+"
        r"(?:today|tonight|this evening)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        re.I,
    ),
)

REMINDER_INTENT_PATTERN = re.compile(r"\b(remind|reminder)\b", re.I)


def parse_reminder_time(
    hour: int, minute: int, meridiem: str | None, reference: datetime
) -> datetime:
    if meridiem:
        mer = meridiem.lower()
        if mer == "pm" and hour < 12:
            hour += 12
        if mer == "am" and hour == 12:
            hour = 0
    fire_at = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if fire_at <= reference:
        from datetime import timedelta

        fire_at += timedelta(days=1)
    return fire_at


class ReminderStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    fire_at TEXT NOT NULL,
                    sent INTEGER NOT NULL DEFAULT 0,
                    cancelled INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id)"
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create(self, user_id: str, text: str, fire_at: datetime) -> Reminder:
        reminder_id = str(uuid.uuid4())
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO reminders (id, user_id, text, fire_at) VALUES (?, ?, ?, ?)",
                (reminder_id, user_id, text, fire_at.isoformat()),
            )
        return Reminder(id=reminder_id, user_id=user_id, text=text, fire_at=fire_at)

    def list_for_user(self, user_id: str, include_cancelled: bool = False) -> list[Reminder]:
        query = "SELECT * FROM reminders WHERE user_id = ?"
        if not include_cancelled:
            query += " AND cancelled = 0"
        with self.connection() as conn:
            rows = conn.execute(query, (user_id,)).fetchall()
        return [self._row_to_reminder(row) for row in rows]

    def list_due(self, now: datetime, user_id: str | None = None) -> list[Reminder]:
        query = (
            "SELECT * FROM reminders WHERE cancelled = 0 AND sent = 0 AND fire_at <= ?"
        )
        params: list[object] = [now.isoformat()]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_reminder(row) for row in rows]

    def mark_sent(self, reminder_id: str, user_id: str) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                "UPDATE reminders SET sent = 1 WHERE id = ? AND user_id = ? AND sent = 0",
                (reminder_id, user_id),
            )
        return cur.rowcount == 1

    def cancel_by_text(self, user_id: str, text_fragment: str) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                UPDATE reminders SET cancelled = 1
                WHERE user_id = ? AND cancelled = 0 AND lower(text) LIKE ?
                """,
                (user_id, f"%{text_fragment.lower()}%"),
            )
        return cur.rowcount

    def delete_all_for_user(self, user_id: str) -> int:
        with self.connection() as conn:
            cur = conn.execute("DELETE FROM reminders WHERE user_id = ?", (user_id,))
        return cur.rowcount

    @staticmethod
    def _row_to_reminder(row: sqlite3.Row) -> Reminder:
        return Reminder(
            id=row["id"],
            user_id=row["user_id"],
            text=row["text"],
            fire_at=datetime.fromisoformat(row["fire_at"]),
            sent=bool(row["sent"]),
            cancelled=bool(row["cancelled"]),
        )


class ReminderService:
    def __init__(self, store: ReminderStore) -> None:
        self.store = store

    def parse_and_create(self, user_id: str, message: str, now: datetime) -> Reminder | None:
        match = None
        for pattern in REMINDER_CREATE_PATTERNS:
            match = pattern.search(message)
            if match:
                break
        if not match:
            return None
        text = match.group(1).strip()
        hour = int(match.group(2))
        minute = int(match.group(3) or 0)
        meridiem = match.group(4)
        fire_at = parse_reminder_time(hour, minute, meridiem, now)
        return self.store.create(user_id, text, fire_at)

    def looks_like_reminder_intent(self, message: str) -> bool:
        return bool(REMINDER_INTENT_PATTERN.search(message))

    def clarification_message(self) -> str:
        return (
            "I can set that reminder, but I need an exact time. "
            'Try: "Remind me to have dinner with friends at 6:45pm."'
        )

    def format_confirmation(self, reminder: Reminder) -> str:
        time_label = reminder.fire_at.strftime("%I:%M %p").lstrip("0")
        return (
            f"✅ Reminder set: {reminder.text} — Today at {time_label}\n"
            f"I'll message you at {time_label}."
        )

    def format_fire_message(self, reminder: Reminder) -> str:
        return f"⏰ Time to {reminder.text}!"

    def list_today(self, user_id: str, now: datetime) -> list[Reminder]:
        reminders = self.store.list_for_user(user_id)
        return [r for r in reminders if r.fire_at.date() == now.date() and not r.sent]

    def process_due(self, now: datetime) -> list[tuple[Reminder, str]]:
        due = self.store.list_due(now)
        outputs: list[tuple[Reminder, str]] = []
        for reminder in due:
            if self.store.mark_sent(reminder.id, reminder.user_id):
                outputs.append((reminder, self.format_fire_message(reminder)))
        return outputs
