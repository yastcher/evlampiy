from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import Field


class UserSettings(Document):
    """
    User model MongoDB for Beanie.
    """

    chat_id: str
    language: str | None = None
    command: str | None = None
    github_settings: dict[str, str] | None = None
    save_to_obsidian: bool = False
    auto_categorize: bool = False

    class Settings:
        name = "users"


class UserTier(str, Enum):
    FREE = "free"
    PAID = "paid"
    VIP = "vip"


class UserCredits(Document):
    user_id: str
    credits: int = 0
    tier: UserTier = UserTier.FREE
    total_transcriptions: int = 0
    total_audio_seconds: int = 0
    total_credits_spent: int = 0
    total_credits_purchased: int = 0

    class Settings:
        name = "user_credits"


class UsedTrial(Document):
    user_hash: str

    class Settings:
        name = "used_trials"


class WitUsageStats(Document):
    month_key: str  # "2026-01"
    request_count: int = 0

    class Settings:
        name = "wit_usage_stats"


class MonthlyStats(Document):
    month_key: str  # "2026-01"
    total_transcriptions: int = 0
    total_payments: int = 0
    total_credits_sold: int = 0
    groq_audio_seconds: int = 0

    class Settings:
        name = "monthly_stats"


def _utc_now():
    return datetime.now(timezone.utc)


class AlertState(Document):
    alert_type: str
    month_key: str
    sent_at: datetime = Field(default_factory=_utc_now)

    class Settings:
        name = "alert_state"


class AccountLink(Document):
    telegram_user_id: str
    whatsapp_phone: str

    class Settings:
        name = "account_links"


class LinkCode(Document):
    code: str
    telegram_user_id: str
    created_at: datetime = Field(default_factory=_utc_now)

    class Settings:
        name = "link_codes"


class LinkAttempt(Document):
    whatsapp_phone: str
    attempt_count: int = 0
    first_attempt_at: datetime = Field(default_factory=_utc_now)
    locked_until: datetime | None = None

    class Settings:
        name = "link_attempts"
