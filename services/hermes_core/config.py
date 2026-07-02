from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    public_domain: str
    database_path: Path
    token_daily_limit: int
    pilot_user_id: str
    pilot_pin: str
    timezone: str
    telegram_bot_token: str
    telegram_webhook_secret: str
    llm_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        db_path = Path(os.getenv("DATABASE_PATH", "./data/hermes.db"))
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        return cls(
            deepseek_api_key=api_key,
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            public_domain=os.getenv("PUBLIC_DOMAIN", "localhost"),
            database_path=db_path,
            token_daily_limit=int(os.getenv("TOKEN_DAILY_LIMIT", "50000")),
            pilot_user_id=os.getenv("PILOT_USER_ID", "pilot-user"),
            pilot_pin=os.getenv("PILOT_PIN", ""),
            timezone=os.getenv("TZ", "Asia/Hong_Kong"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
            llm_enabled=bool(api_key),
        )
