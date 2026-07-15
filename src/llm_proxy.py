"""Resolve provider API bases through the optional LLM reverse proxy (``LLM_API_BASE``).

Both the text-generation client (``ai_client``) and the Groq Whisper transcription client
route the same geo-blocked hosts, so the rule lives here instead of being duplicated. See
``cloudflare/llm-proxy/`` for the Worker that maps ``/<provider>/<path>`` to the upstream.
"""

from src import const
from src.config import settings

# Providers geo-blocked from some deploys (e.g. a Russian VPS). Their const API base is
# host-only, so the proxy Worker can route /<provider>/<path> to the upstream host.
# DeepSeek/Qwen keep their path-suffixed bases and stay direct.
PROXYABLE_PROVIDERS = frozenset(
    {
        const.PROVIDER_GROQ,
        const.PROVIDER_OPENROUTER,
        const.PROVIDER_GEMINI,
        const.PROVIDER_ANTHROPIC,
        const.PROVIDER_OPENAI,
    }
)


def api_base(provider: str, default_base: str) -> str:
    """Return the effective API base for a provider, routed through the proxy if set.

    With ``LLM_API_BASE`` configured and a proxyable provider, calls go to
    ``<llm_api_base>/<provider>`` (the Worker swaps that prefix for the upstream host);
    otherwise the provider's direct base is used.
    """
    if settings.llm_api_base and provider in PROXYABLE_PROVIDERS:
        return f"{settings.llm_api_base}/{provider}"
    return default_base
