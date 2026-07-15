# LLM provider API proxy (Cloudflare Worker)

A reverse proxy for the LLM provider APIs that are geo-blocked on some hosts (e.g. a
Russian VPS) while Cloudflare stays reachable: the bot talks to the Worker, the Worker
talks to the provider. Covers **Groq, OpenRouter, Gemini, Anthropic, OpenAI** (DeepSeek
and Qwen are reached directly and are not proxied).

## Deploy

Requires the Cloudflare credentials already in `.env`:

```bash
export CLOUDFLARE_ACCOUNT_ID=...   # from .env
export CLOUDFLARE_API_TOKEN=...    # from .env, needs "Edit Workers" permission
npx wrangler deploy
```

Wrangler prints the Worker URL, e.g. `https://llm-proxy.<subdomain>.workers.dev`.

## Wire up the bot

Set on the bot host:

```
LLM_API_BASE=https://llm-proxy.<subdomain>.workers.dev
```

The bot then calls `<LLM_API_BASE>/<provider>/<path>` and the Worker swaps the
`<provider>` prefix for the matching upstream host. Empty `LLM_API_BASE` calls providers
directly. The Worker forwards only to the five hosts in its allowlist, so it cannot be
used as an open proxy.

> Provider API keys pass through your Worker in the request headers (as they would to the
> provider directly). The Worker lives in your own Cloudflare account and never logs
> headers or bodies, so the keys stay within your infrastructure.
