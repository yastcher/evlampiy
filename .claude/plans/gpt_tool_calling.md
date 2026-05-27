# Tool Calling для GPT-команд

## Context

Karpathy "LLM OS" — бот как интерфейс к данным и действиям пользователя через tool calling.

## Phase 1 — DONE (v0.8.13, коммит 274f03b)

- Tools: `get_recent_notes`, `get_user_settings`, `get_categories`
- Все 7 провайдеров (OpenAI-compatible + Gemini + Anthropic)
- Фиксированный system prompt в `prompts.py`
- Файлы: `src/ai_chat.py`, `src/tools.py`, `src/tool_calling.py`
- Тесты: `test_ai_chat.py`, `test_tools.py`, `test_tool_calling.py`, `test_gpt_commands.py`

## Phase 2 — TODO

- Больше tools: `create_note`, `search_notes`, `update_settings`
- Conversation history (multi-turn) с TTL в MongoDB
- Streaming ответов
- Tool calling для WhatsApp handler
- Расширяемый реестр инструментов
