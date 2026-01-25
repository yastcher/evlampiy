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


settings: Settings = Settings()
