from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENGLISH = "en"
RUSSIAN = "ru"
SPANISH = "es"
GERMAN = "de"
LANGUAGES = (
    ENGLISH,
    RUSSIAN,
    SPANISH,
    GERMAN,
)


def _parse_comma_separated_ids(value: str) -> set[str]:
    if not value.strip():
        return set()
    return {x.strip() for x in value.split(",") if x.strip()}


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
    vip_user_ids_raw: str = Field(default="", validation_alias="VIP_USER_IDS")
    admin_user_ids_raw: str = Field(default="", validation_alias="ADMIN_USER_IDS")
    free_monthly_tokens: int = 10
    seconds_per_token: int = 20

    # Groq
    groq_api_key: str = ""
    groq_model: str = "whisper-large-v3-turbo"

    # AI provider selection
    categorization_provider: str = "gemini"
    gpt_provider: str = "gemini"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Anthropic
    anthropic_bot_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"

    # Wit.ai monthly free limit
    wit_free_monthly_limit: int = 500

    # Self-test
    selftest_sample_path: str = "./data/e2e_deploy_ru.ogg"

    # FastAPI server
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000

    @property
    def vip_user_ids(self) -> set[str]:
        return _parse_comma_separated_ids(self.vip_user_ids_raw)

    @property
    def admin_user_ids(self) -> set[str]:
        return _parse_comma_separated_ids(self.admin_user_ids_raw)


settings: Settings = Settings()
