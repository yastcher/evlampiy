import datetime
import typing
from enum import Enum

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


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
    auto_cleanup: bool = False
    preferred_provider: str | None = None  # "wit", "groq", or None (auto)

    class Settings:
        name = "users"


class UserTier(str, Enum):
    FREE = "free"
    PAID = "paid"
    VIP = "vip"
    TESTER = "tester"


class UserCredits(Document):
    user_id: str

    # Balance
    free_credits: int = 10
    free_credits_month: str = ""
    purchased_credits: int = 0

    # Tier
    tier: UserTier = UserTier.FREE

    # Cumulative stats (per-user, all-time)
    total_transcriptions: int = 0
    total_audio_seconds: int = 0
    total_tokens_used: int = 0
    total_credits_spent: int = 0  # deprecated, kept for backward compat
    total_credits_purchased: int = 0

    class Settings:
        name = "user_credits"


class UserMonthlyUsage(Document):
    user_id: str
    month_key: str  # "2026-02"

    transcriptions: int = 0
    audio_seconds: int = 0
    tokens_used: int = 0
    free_tokens_used: int = 0
    purchased_tokens_used: int = 0

    class Settings:
        name = "user_monthly_usage"


class UsedTrial(Document):
    user_hash: str

    class Settings:
        name = "used_trials"


class BotConfig(Document):
    """Global runtime settings overridable by admin without restart."""

    key: str
    value: str

    class Settings:
        name = "bot_config"


class WitUsageStats(Document):
    month_key: str  # "2026-01"
    language: str = ""  # "en", "ru", "es", "de"; empty for legacy records
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
    return datetime.datetime.now(datetime.UTC)


class AlertState(Document):
    alert_type: str
    month_key: str
    sent_at: datetime.datetime = Field(default_factory=_utc_now)

    class Settings:
        name = "alert_state"


class UserRole(Document):
    user_id: str
    role: str  # "vip" or "tester"
    added_by: str
    added_at: datetime.datetime = Field(default_factory=_utc_now)

    class Settings:
        name = "user_roles"


class AccountLink(Document):
    telegram_user_id: str
    whatsapp_phone: str

    class Settings:
        name = "account_links"


class LinkCode(Document):
    code: str
    telegram_user_id: str
    created_at: datetime.datetime = Field(default_factory=_utc_now)

    class Settings:
        name = "link_codes"


class LinkAttempt(Document):
    whatsapp_phone: str
    attempt_count: int = 0
    first_attempt_at: datetime.datetime = Field(default_factory=_utc_now)
    locked_until: datetime.datetime | None = None

    class Settings:
        name = "link_attempts"


_RECENT_TRANSCRIPTION_TTL_SECONDS = 7200  # 2 hours


class RecentTranscription(Document):
    """Stores recent cleaned transcriptions per chat for cleanup context (TTL 2h)."""

    chat_id: str
    text: str
    created_at: datetime.datetime = Field(default_factory=_utc_now)

    class Settings:
        name = "recent_transcriptions"
        indexes: typing.ClassVar = [
            IndexModel(
                [("created_at", ASCENDING)],
                expireAfterSeconds=_RECENT_TRANSCRIPTION_TTL_SECONDS,
            ),
        ]
