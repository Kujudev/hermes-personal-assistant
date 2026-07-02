from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from hermes_core.config import Settings
from hermes_core.reminders import ReminderService, ReminderStore

logger = logging.getLogger("hermes.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@dataclass(frozen=True)
class Notification:
    id: str
    user_id: str
    content: str
    created_at: datetime
    delivered: bool


class NotificationStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def enqueue(self, user_id: str, content: str, created_at: datetime) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO notifications (id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, content, created_at.isoformat()),
            )


    def list_undelivered(self, user_id: str) -> list[Notification]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notifications
                WHERE user_id = ? AND delivered = 0
                ORDER BY created_at ASC
                """,
                (user_id,),
            ).fetchall()
        return [self._row(row) for row in rows]

    def mark_delivered(self, notification_id: str, user_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE notifications SET delivered = 1 WHERE id = ? AND user_id = ?",
                (notification_id, user_id),
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> Notification:
        return Notification(
            id=row["id"],
            user_id=row["user_id"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            delivered=bool(row["delivered"]),
        )


def run_loop(interval_seconds: int = 30) -> None:
    settings = Settings.from_env()
    tz = ZoneInfo(settings.timezone)
    store = ReminderStore(settings.database_path)
    service = ReminderService(store)
    notifications = NotificationStore(settings.database_path)

    logger.info(
        "Reminder worker started (tz=%s, interval=%ss)",
        settings.timezone,
        interval_seconds,
    )
    while True:
        now = datetime.now(tz)
        fired = service.process_due(now)
        for reminder, message in fired:
            notifications.enqueue(reminder.user_id, message, now)
            logger.info("Reminder fired for user=%s", reminder.user_id)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_loop()
