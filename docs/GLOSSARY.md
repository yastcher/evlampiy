# Glossary

The words this project uses for its own things. Evlampiy (Евлампий) is the bot: the `evlampiy`
package, the `/evlampiy` command, the default GPT trigger. When a discussion uses a word
otherwise, this file is corrected, not the discussion. Module paths are under `evlampiy/`.

## Chats and people

- **Chat id** (`ChatId`): `u_<user_id>` private, `g_<chat_id>` group, `wa_<phone>` WhatsApp;
  settings hang on it, tokens and roles on the Telegram **user id** (`UserId`).
- **Chat settings**: `UserSettings`, one per chat id (collection `users`). In a group, and from
  a linked WhatsApp number, cleanup and the vault follow the user's own `u_` settings
  (`settings_chat_id`).
- **Hub**: the inline menus `/settings`, `/obsidian` (Notes), `/account`; `hub_*` callbacks.
- **Language**: `en`, `ru`, `es` or `de` (`config.LANGUAGES`), per chat, `ru` by default; the
  UI language (`localization.py`) and the transcription language at once.
- **Admin**: a user id in `ADMIN_USER_IDS`, env only. A **chat admin** may change a chat's
  settings: anyone in a private chat, a group's administrators (`chat_params.is_user_admin`).
- **Role**: `vip`, `tester` or `blocked` (`UserRole`), set by `/add_vip`, `/add_tester`,
  `/block`; VIP also from `VIP_USER_IDS`. **Blocked** stops voice transcription on both
  channels, the GPT chat and `/categorize`.
- **Tier** (`UserTier`): `free`, `paid` (since a purchase), `vip` (admins too) or `tester`.
  Above `free`: LLM cleanup, provider choice; `vip` and `tester` spend no tokens.
- **Linking** (`account_linking.py`): `link <code>` sent on WhatsApp, the code from
  `/link_whatsapp`, ties the number to that Telegram user: the number then acts as their
  private chat, tokens and settings included (ADR-001). An unlinked number is told how to link.

## Transcription

- **Voice pipeline**: `services/voice_pipeline.process_voice`, shared by Telegram and
  WhatsApp: transcribe, clean up, save, sort. Admission and billing around it:
  `services/voice_access.py`, for both channels.
- **Transcription provider**: `wit` or `groq`, per message (`voice_access.select_provider`):
  `free` gets Wit.ai only, other tiers their choice, else Wit.ai, else Groq.
- **Wit.ai**: the default provider, a token per language, `WIT_{EN,RU,ES,DE}_TOKEN`
  (`transcription/wit_client.py`); audio goes in 19.5 s chunks, one request each.
- **Wit limit**: `WIT_FREE_MONTHLY_LIMIT` (500) Wit requests per language a month, counted for
  both channels (`wit_tracking.py`); past it `free` is refused, the rest get Groq.
- **Groq**: one key, `GROQ_API_KEY`, for two things: **Groq Whisper** (`GROQ_MODEL`,
  `transcription/groq_client.py`) and the Groq LLM (`GROQ_LLM_MODEL`).

## LLM

- **Categorization provider**, **GPT provider**: first in line for sorting, and for cleanup
  and the GPT chat (`CATEGORIZATION_PROVIDER`, `GPT_PROVIDER`; `BotConfig` overrides).
- **Fallback chain**: the primary, then the rest of `deepseek → openrouter → gemini → groq`
  (`ai_client.py`) while one fails or has no key; Anthropic, OpenAI, Qwen only as primary.
- **Cleanup**: the LLM pass that drops fillers and fixes misheard words
  (`transcript_cleanup.py`), above `free`, given the chat's last 3 **recent transcriptions**.
  **Auto-cleanup** only picks whether the reply is cleaned; the vault gets it anyway.
- **GPT chat**: `/evlampiy <question>` (`gpt_commands.py`), answered by the GPT provider's
  chain (`ai_chat.py`) with the tools in `tools.py`.
- **GPT trigger** ("GPT command" in /settings, `gpt_command` in code): a per-chat word; a
  transcript starting with it only gets a "Command … detected" label.
- **Mask**: emails, phones and names (two capitalized words or more) swapped for `<EMAIL_N>`,
  `<PHONE_N>`, `<NAME_N>` before a request leaves, restored in the answer (`ai/_mask.py`), where
  each LLM client hands it to its providers: `ai_client._ai_complete` (cleanup, sorting) and
  `ai_chat.chat_complete` (the GPT chat, with its tool calls and the notes they found).

## Notes

- **Vault**: the user's GitHub repository, opened in Obsidian and written through the GitHub
  API (`github_api.py`); the bot's folder in it is the **base dir**, `OBSIDIAN_BASE_DIR`.
- **Inbox**, **trash**: `<base dir>/inbox`, where every note lands, and `<base dir>/trash`,
  where sorting puts garbage (`obsidian_layout.py`).
- **Note**: `inbox/<YYYY-MM-DD_HH-MM-SS>.md`, saved while **sync** (`save_to_obsidian`) is on;
  **dual-save** keeps the raw transcript under it in an `<!-- original … -->` comment.
- **Category**: a folder of the base dir (not inbox or trash) named by the LLM; **auto-sort**
  (`auto_categorize`) files each new note in one, `/categorize` all of inbox.
- **Vocabulary**: `vocabulary.json` at the vault's root, category → up to 50 keywords, up to 5
  added per sorted note; read by the categorization prompt only, not by cleanup.
- **Connecting GitHub**: OAuth Device Flow (`github_oauth.py`, `GITHUB_CLIENT_ID`), then a
  repository pick or a new private one; the token is stored unencrypted in `github_settings`.

## Money

- **Token** (**credit** in code): 20 s of audio rounded up, at least 1, per
  `const.SECONDS_PER_TOKEN` (the setting of that name is unused); not an API key or LLM token.
- **Free tokens**: `FREE_MONTHLY_TOKENS` (10) per UTC month (`MonthKey`), spent first, then
  **purchased** ones (Stars, `/add_credits`); a message may overdraw to 0 (**overdraft**).
- **Package**: one of four `CREDIT_PACKAGES` (`services/payments_service.py`) sold for Stars
  by `/buy`; each charge id is claimed in `ProcessedPayment` first, so a payment counts once.

## Operations

- **`/health`**: `{"status": "ok", "whatsapp": …}` from the always-on `http` subsystem;
  `whatsapp` is `on`, `off` (not set up) or `no app secret` (webhook refused).
- **Self-test** (`selftest.py`): at each Telegram start, admins get the sample voice
  (`SELFTEST_SAMPLE_PATH`) and a check of Wit.ai, Groq, cleanup, translations and keys.
- **Alerts**: admin messages, each kind once a month (`alerts.py`): the month's first payment,
  a revenue milestone in Stars (on any payment that crosses it), Wit usage over 80 % and 95 %
  per language.
- **Telegram proxy**, **LLM proxy**: `TELEGRAM_API_BASE`, `LLM_API_BASE`, Cloudflare Workers
  (`cloudflare/`) for hosts where Telegram or the LLM providers are blocked; the LLM one
  carries Groq, OpenRouter, Gemini, Anthropic and OpenAI (`llm_proxy.py`).
