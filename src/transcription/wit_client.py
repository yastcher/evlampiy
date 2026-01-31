"""Wit.ai client initialization."""

import wit

from src.config import ENGLISH, GERMAN, RUSSIAN, SPANISH, settings

voice_translators = {
    ENGLISH: wit.Wit(settings.wit_en_token),
    RUSSIAN: wit.Wit(settings.wit_ru_token),
    SPANISH: wit.Wit(settings.wit_es_token),
    GERMAN: wit.Wit(settings.wit_de_token),
}
