"""The settings a test session runs with: `Settings`' own defaults and nothing else."""

from evlampiy.config import Settings


def isolated_settings() -> Settings:
    """`Settings`' defaults, read from neither the developer's `.env` nor the shell.

    pydantic-settings reads `.env` apart from `os.environ`, and a key exported in the shell
    beats both, so clearing variables is not enough: a test that forgets a mock would call a
    provider for real, with the owner's money and the users' text. The defaults hold no key
    and no `MONGO_URI`; a test that needs a value patches it. `environment="test"` marks the
    object, so a module holding another one shows.
    """
    return Settings.model_construct(environment="test")
