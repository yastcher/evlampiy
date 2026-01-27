from enum import Enum

from beanie import Document


class UserSettings(Document):
    """
    User model MongoDB for Beanie.
    """

    chat_id: str
    language: str | None = None
    command: str | None = None
    github_settings: dict[str, str] | None = None
    save_to_obsidian: bool = False

    class Settings:
        name = "users"


class UserTier(str, Enum):
    FREE = "free"
    PAID = "paid"
    VIP = "vip"


class UserCredits(Document):
    user_id: int
    credits: int = 0
    tier: UserTier = UserTier.FREE

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
