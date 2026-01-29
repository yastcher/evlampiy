from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENGLISH = "en"
RUSSIAN = "ru"
SPANISH = "es"
GERMANY = "de"
LANGUAGES = (
    ENGLISH,
    RUSSIAN,
    SPANISH,
    GERMANY,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
    )

    debug: bool = True
    environment: str = "dev"
    default_language: str = RUSSIAN
    telegram_bot_command: str = "евлампий"
    telegram_bot_token: str = ""

    mongo_uri: str = "mongodb://mongodb:27017/"

    gpt_token: str = ""
    gpt_model: str = "gpt-3.5-turbo"

    wit_ru_token: str = ""
    wit_en_token: str = ""
    wit_es_token: str = ""
    wit_de_token: str = ""

    # GitHub OAuth
    github_client_id: str = ""

    # WhatsApp (Meta Cloud API)
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_id: str = ""
    whatsapp_app_secret: str = ""

    # Monetization
    vip_user_ids: set[int] = set()
    admin_user_ids: set[int] = set()
    initial_credits: int = 3
    credit_cost_voice: int = 1
    credits_per_star: int = 1

    # Groq
    groq_api_key: str = ""
    groq_model: str = "whisper-large-v3-turbo"

    # Wit.ai monthly free limit
    wit_free_monthly_limit: int = 500

    @field_validator("vip_user_ids", "admin_user_ids", mode="before")
    @classmethod
    def parse_user_id_set(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return set()
            return {int(x.strip()) for x in v.split(",") if x.strip()}
        return v


settings: Settings = Settings()
