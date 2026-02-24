"""Application configuration helpers.

Centralizes all environment-driven settings so the rest of the codebase
stays free of hard-coded secrets or magic numbers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

try:  # Optional dependency for local development convenience
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - fallback when python-dotenv missing
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if load_dotenv and ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)


def _to_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "off", "no"}


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class AppSettings:
    environment: str = os.getenv("APP_ENV", "local")
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    email_from: str = os.getenv("FROM_EMAIL", os.getenv("EMAIL_FROM", "noreply@example.com"))
    email_from_name: str = os.getenv("FROM_NAME", os.getenv("EMAIL_FROM_NAME", "AI Inventory Copilot"))
    email_enabled: bool = _to_bool(os.getenv("EMAIL_ENABLED"), True)
    default_alert_recipients: List[str] = field(
        default_factory=lambda: _split_csv(os.getenv("ALERT_RECIPIENTS"))
    )
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    teams_webhook_url: str = os.getenv("TEAMS_WEBHOOK_URL", "")
    alert_scheduler_enabled: bool = _to_bool(os.getenv("ALERT_SCHEDULER_ENABLED"), True)
    alert_scheduler_interval_seconds: int = int(os.getenv("ALERT_SCHEDULER_INTERVAL_SECONDS", "900"))
    alert_dedupe_window_minutes: int = int(os.getenv("ALERT_DEDUPE_WINDOW_MINUTES", "120"))
    log_notifications: bool = _to_bool(os.getenv("LOG_NOTIFICATIONS"), True)

    def ensure_default_recipients(self) -> List[str]:
        """Always provide at least one recipient so alerts are not dropped."""
        if self.default_alert_recipients:
            return self.default_alert_recipients
        fallback = os.getenv("FALLBACK_ALERT_EMAIL")
        return [fallback] if fallback else []


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Singleton-style accessor for app settings."""
    return AppSettings()
