"""Wit.ai client initialization."""
import wit

from src.config import ENGLISH, GERMANY, RUSSIAN, SPANISH, settings

voice_translators = {
    ENGLISH: wit.Wit(settings.wit_en_token),
    RUSSIAN: wit.Wit(settings.wit_ru_token),
    SPANISH: wit.Wit(settings.wit_es_token),
    GERMANY: wit.Wit(settings.wit_de_token),
}
