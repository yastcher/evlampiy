"""Admin stats text builder. Framework-agnostic — does not import aiogram."""

from collections.abc import Sequence

from src import const
from src.ai_client import _PROVIDER_LIMITS, CATEGORIZATION_FALLBACK_CHAIN, GPT_FALLBACK_CHAIN
from src.config import settings
from src.credits import current_month_key, get_monthly_stats
from src.mongo import get_bot_config
from src.wit_tracking import get_all_wit_usage_this_month


def _provider_icon(name: str, keys: dict[str, bool]) -> str:
    """Return check/cross based on whether the provider has a key configured."""
    return "✅" if keys.get(name) else "❌"


def _provider_rpm(name: str) -> str:
    rpm = _PROVIDER_LIMITS.get(name)
    return f" {rpm}rpm" if rpm else ""


async def build_stats_text() -> str:
    """Build admin stats message text."""
    month = current_month_key()
    stats = await get_monthly_stats(month)
    wit_limit = settings.wit_free_monthly_limit
    wit_usage_by_lang = await get_all_wit_usage_this_month()

    total_transcriptions = stats.total_transcriptions if stats else 0
    total_payments = stats.total_payments if stats else 0
    total_credits_sold = stats.total_credits_sold if stats else 0
    groq_audio_seconds = stats.groq_audio_seconds if stats else 0

    revenue = total_credits_sold * const.STAR_TO_DOLLAR
    groq_cost = groq_audio_seconds / 3600 * 0.04

    def _wit_status(usage: int) -> str:
        if usage >= wit_limit * 0.95:
            return "CRITICAL"
        if usage >= wit_limit * 0.8:
            return "Warning"
        return "OK"

    keys: dict[str, bool] = {
        const.PROVIDER_GROQ: bool(settings.groq_api_key),
        const.PROVIDER_GEMINI: bool(settings.gemini_api_key),
        const.PROVIDER_ANTHROPIC: bool(settings.anthropic_bot_api_key),
        const.PROVIDER_OPENROUTER: bool(settings.openrouter_api_key),
        const.PROVIDER_OPENAI: bool(settings.gpt_token),
    }

    def _chain_str(primary: str, fallback_chain: Sequence[str]) -> str:
        chain = [primary] + [p for p in fallback_chain if p != primary]
        parts = [f"{p}{_provider_rpm(p)} {_provider_icon(p, keys)}" for p in chain]
        return " → ".join(parts)

    categ_primary = await get_bot_config(
        "categorization_provider", settings.categorization_provider
    )
    gpt_primary = await get_bot_config("gpt_provider", settings.gpt_provider)
    categ_chain = _chain_str(categ_primary, CATEGORIZATION_FALLBACK_CHAIN)
    gpt_chain = _chain_str(gpt_primary, GPT_FALLBACK_CHAIN)

    all_chain_providers = set(CATEGORIZATION_FALLBACK_CHAIN) | set(GPT_FALLBACK_CHAIN)
    unused_with_key = [p for p, has_key in keys.items() if has_key and p not in all_chain_providers]
    unused_line = f"\n• Not in chain: {', '.join(unused_with_key)}" if unused_with_key else ""

    return (
        f"📊 <b>System Stats ({month})</b>\n\n"
        f"<b>Users</b>\n"
        f"• Total transcriptions: {total_transcriptions:,}\n"
        f"• Payments: {total_payments}\n\n"
        f"<b>Revenue</b>\n"
        f"• Stars received: {total_credits_sold}★\n"
        f"• Credits sold: {total_credits_sold}\n"
        f"• Revenue: ${revenue:.2f}\n\n"
        f"<b>Costs</b>\n"
        f"• Wit.ai / {wit_limit:,} req/mo:\n"
        + "".join(
            f"  - {lang}: {usage:,} ({usage / wit_limit * 100:.1f}%)\n"
            for lang, usage in sorted(wit_usage_by_lang.items())
        )
        + ("  - (no data yet)\n" if not wit_usage_by_lang else "")
        + f"• Groq audio: {groq_audio_seconds} sec/mo (${groq_cost:.2f})"
        f" | limit: {settings.groq_audio_daily_limit:,} sec/day\n\n"
        f"<b>LLM Providers</b>\n"
        f"• Categ: {categ_chain}\n"
        f"• GPT:   {gpt_chain}"
        f"{unused_line}\n\n"
        f"<b>Health</b>\n"
        + "".join(
            f"• Wit.ai ({lang}): "
            f"{'✅' if _wit_status(u) == 'OK' else '⚠️' if _wit_status(u) == 'Warning' else '🚨'} "
            f"{_wit_status(u)}\n"
            for lang, u in sorted(wit_usage_by_lang.items())
        )
        + ("• Wit.ai: ✅ OK (no data)\n" if not wit_usage_by_lang else "")
        + f"• Groq: {'✅' if settings.groq_api_key else '❌'} "
        f"{'Configured' if settings.groq_api_key else 'Not configured'}"
    )
