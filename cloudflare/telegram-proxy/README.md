# Telegram Bot API proxy (Cloudflare Worker)

A reverse proxy for `api.telegram.org`. Use it when the bot runs on a host where
Telegram is blocked (e.g. a Russian VPS) but Cloudflare is reachable: the bot
talks to the Worker, the Worker talks to Telegram.

## Deploy

Requires the Cloudflare credentials already in `.env`:

```bash
export CLOUDFLARE_ACCOUNT_ID=...   # from .env
export CLOUDFLARE_API_TOKEN=...    # from .env, needs "Edit Workers" permission
npx wrangler deploy
```

Wrangler prints the Worker URL, e.g. `https://telegram-proxy.<subdomain>.workers.dev`.

## Wire up the bot

Set on the bot host:

```
TELEGRAM_API_BASE=https://telegram-proxy.<subdomain>.workers.dev
```

Empty `TELEGRAM_API_BASE` keeps the official endpoint. The Worker only forwards to
`api.telegram.org` (paths `/bot<token>/<method>` and `/file/bot<token>/<path>`),
so it cannot be used as an open proxy.

> The bot token passes through your Worker (it is part of the URL path). The Worker
> lives in your own Cloudflare account, so the token stays within your infrastructure.
