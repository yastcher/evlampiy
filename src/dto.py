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
