from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class ChatMessage:
    id: str
    user_id: str
    role: str
    content: str
    created_at: datetime


class ChatStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, created_at)"
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, user_id: str, role: str, content: str, created_at: datetime) -> ChatMessage:
        message_id = str(uuid.uuid4())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, user_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, user_id, role, content, created_at.isoformat()),
            )
        return ChatMessage(
            id=message_id,
            user_id=user_id,
            role=role,
            content=content,
            created_at=created_at,
        )

    def list_recent(self, user_id: str, limit: int = 50) -> list[ChatMessage]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_messages
                WHERE user_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ChatMessage:
        return ChatMessage(
            id=row["id"],
            user_id=row["user_id"],
            role=row["role"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
