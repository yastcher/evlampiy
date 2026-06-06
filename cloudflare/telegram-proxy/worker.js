// Reverse proxy for the Telegram Bot API.
//
// Lets the bot reach Telegram from a host where api.telegram.org is blocked
// (e.g. a Russian VPS). Point aiogram at this Worker via:
//   TELEGRAM_API_BASE=https://<worker-name>.<subdomain>.workers.dev
//
// It only ever forwards to api.telegram.org, so it is not an open proxy.
// Both bot calls (/bot<token>/<method>) and file downloads
// (/file/bot<token>/<path>) are handled by swapping the hostname.

const UPSTREAM = "api.telegram.org";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (!url.pathname.startsWith("/bot") && !url.pathname.startsWith("/file/bot")) {
      return new Response("Not found", { status: 404 });
    }

    url.hostname = UPSTREAM;
    url.protocol = "https:";
    url.port = "";

    return fetch(new Request(url, request));
  },
};
