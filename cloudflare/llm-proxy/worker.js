// Reverse proxy for LLM provider APIs that are geo-blocked from some hosts
// (e.g. a Russian VPS). Point the bot at this Worker via:
//   LLM_API_BASE=https://<worker-name>.<subdomain>.workers.dev
//
// The bot calls https://<worker>/<provider>/<path>; the Worker maps <provider> to a
// fixed upstream host and forwards the rest of the request unchanged. It only ever
// forwards to the hosts in UPSTREAM, so it is not an open proxy. API keys ride in the
// request headers straight to the provider — the Worker never logs headers or bodies.

const UPSTREAM = {
  groq: "api.groq.com",
  openrouter: "openrouter.ai",
  gemini: "generativelanguage.googleapis.com",
  anthropic: "api.anthropic.com",
  openai: "api.openai.com",
};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    // pathname is "/<provider>/<rest...>"; split drops the leading empty segment.
    const segments = url.pathname.split("/");
    const host = UPSTREAM[segments[1]];
    if (!host) {
      return new Response("Not found", { status: 404 });
    }

    url.hostname = host;
    url.protocol = "https:";
    url.port = "";
    url.pathname = "/" + segments.slice(2).join("/");

    return fetch(new Request(url, request));
  },
};
