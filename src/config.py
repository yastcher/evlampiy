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
        # .env is shared with deploy tooling (e.g. wrangler reads CLOUDFLARE_*);
        # ignore env vars the app does not declare instead of crashing on them.
        extra="ignore",
    )

    debug: bool = True
    environment: str = "dev"
    default_language: str = RUSSIAN
    telegram_bot_command: str = "евлампий"
    telegram_bot_token: str = ""
    # Optional reverse-proxy base for the Telegram Bot API (e.g. a Cloudflare Worker)
    # for hosts where api.telegram.org is blocked. Empty = official endpoint.
    telegram_api_base: str = ""

    mongo_uri: str = "mongodb://mongodb:27017/"

    gpt_token: str = ""
    gpt_model: str = "gpt-4o"

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
    groq_llm_model: str = "llama-3.3-70b-versatile"
    # groq_llm_model: str = "llama-3.1-8b-instant"
    groq_audio_daily_limit: int = 7200  # free tier: 7,200 sec/day

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # Qwen (Alibaba DashScope international)
    qwen_api_key: str = ""
    qwen_model: str = "qwen-turbo"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-4-31b-it:free"  # OK, ~1.6s, cleans RU well
    # openrouter_model: str = "openai/gpt-oss-20b:free"  # OK but ~15s
    # Many older :free models now return 404 "No endpoints found"; verify via /api/v1/models.

    # AI provider selection
    categorization_provider: str = "deepseek"
    gpt_provider: str = "deepseek"

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
    fastapi_host: str = "127.0.0.1"
    fastapi_port: int = 8000

    @property
    def vip_user_ids(self) -> set[str]:
        return _parse_comma_separated_ids(self.vip_user_ids_raw)

    @property
    def admin_user_ids(self) -> set[str]:
        return _parse_comma_separated_ids(self.admin_user_ids_raw)


settings: Settings = Settings()
