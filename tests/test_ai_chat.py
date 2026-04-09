"""Tests for messages-based AI chat completion with tool calling."""

from unittest.mock import patch

import httpx

from src.ai_chat import (
    _messages_to_anthropic,
    _messages_to_gemini,
    _parse_anthropic_response,
    _parse_gemini_response,
    _parse_openai_response,
    chat_complete,
    tools_to_anthropic,
    tools_to_gemini,
    tools_to_openai,
)

SAMPLE_TOOLS = [
    {
        "name": "get_notes",
        "description": "Get recent notes",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [],
        },
    },
]


class TestToolSchemaConversion:
    """Test tool schema format conversion."""

    def test_to_openai(self):
        result = tools_to_openai(SAMPLE_TOOLS)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "get_notes"
        assert result[0]["function"]["parameters"]["type"] == "object"

    def test_to_gemini(self):
        result = tools_to_gemini(SAMPLE_TOOLS)
        assert len(result) == 1
        assert "function_declarations" in result[0]
        decl = result[0]["function_declarations"][0]
        assert decl["name"] == "get_notes"

    def test_to_anthropic(self):
        result = tools_to_anthropic(SAMPLE_TOOLS)
        assert len(result) == 1
        assert result[0]["name"] == "get_notes"
        assert result[0]["input_schema"]["type"] == "object"


class TestMessageConversion:
    """Test message format conversion for different providers."""

    def test_gemini_extracts_system(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        system, contents = _messages_to_gemini(messages)
        assert system == "You are helpful"
        assert len(contents) == 1
        assert contents[0]["role"] == "user"

    def test_gemini_converts_assistant_to_model(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        _, contents = _messages_to_gemini(messages)
        assert contents[1]["role"] == "model"
        assert contents[1]["parts"][0]["text"] == "Hi there"

    def test_gemini_converts_tool_calls(self):
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "tc_1",
                        "function": {"name": "get_notes", "arguments": '{"limit": 3}'},
                    }
                ],
            },
        ]
        _, contents = _messages_to_gemini(messages)
        part = contents[0]["parts"][0]
        assert "functionCall" in part
        assert part["functionCall"]["name"] == "get_notes"
        assert part["functionCall"]["args"] == {"limit": 3}

    def test_gemini_converts_tool_results(self):
        messages = [
            {"role": "tool", "tool_call_id": "tc_1", "name": "get_notes", "content": "result data"},
        ]
        _, contents = _messages_to_gemini(messages)
        part = contents[0]["parts"][0]
        assert "functionResponse" in part
        assert part["functionResponse"]["response"]["result"] == "result data"

    def test_anthropic_extracts_system(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        system, msgs = _messages_to_anthropic(messages)
        assert system == "You are helpful"
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"

    def test_anthropic_converts_tool_calls(self):
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "tc_1",
                        "function": {"name": "get_notes", "arguments": '{"limit": 3}'},
                    }
                ],
            },
        ]
        _, msgs = _messages_to_anthropic(messages)
        block = msgs[0]["content"][0]
        assert block["type"] == "tool_use"
        assert block["id"] == "tc_1"
        assert block["input"] == {"limit": 3}

    def test_anthropic_converts_tool_results(self):
        messages = [
            {"role": "tool", "tool_call_id": "tc_1", "content": "result data"},
        ]
        _, msgs = _messages_to_anthropic(messages)
        block = msgs[0]["content"][0]
        assert block["type"] == "tool_result"
        assert block["tool_use_id"] == "tc_1"
        assert block["content"] == "result data"


class TestParseOpenAIResponse:
    """Test OpenAI-compatible response parsing."""

    def test_parses_text_response(self):
        data = {"choices": [{"message": {"content": "Hello!", "role": "assistant"}}]}
        result = _parse_openai_response(data)
        assert result.content == "Hello!"
        assert result.tool_calls == []
        assert result.raw_message["role"] == "assistant"

    def test_parses_tool_calls(self):
        data = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "get_notes",
                                    "arguments": '{"limit": 5}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        result = _parse_openai_response(data)
        assert result.content is None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_notes"
        assert result.tool_calls[0].id == "call_123"
        assert result.tool_calls[0].arguments == '{"limit": 5}'

    def test_parses_content_with_tool_calls(self):
        data = {
            "choices": [
                {
                    "message": {
                        "content": "Let me check",
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "get_notes", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ]
        }
        result = _parse_openai_response(data)
        assert result.content == "Let me check"
        assert len(result.tool_calls) == 1


class TestParseGeminiResponse:
    """Test Gemini response parsing."""

    def test_parses_text_response(self):
        data = {"candidates": [{"content": {"parts": [{"text": "Hello!"}]}}]}
        result = _parse_gemini_response(data)
        assert result is not None
        assert result.content == "Hello!"
        assert result.tool_calls == []

    def test_parses_function_call(self):
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_notes",
                                    "args": {"limit": 3},
                                }
                            }
                        ]
                    }
                }
            ]
        }
        result = _parse_gemini_response(data)
        assert result is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_notes"

    def test_returns_none_on_empty_candidates(self):
        result = _parse_gemini_response({"candidates": []})
        assert result is None


class TestParseAnthropicResponse:
    """Test Anthropic response parsing."""

    def test_parses_text_response(self):
        data = {"content": [{"type": "text", "text": "Hello!"}]}
        result = _parse_anthropic_response(data)
        assert result.content == "Hello!"
        assert result.tool_calls == []

    def test_parses_tool_use(self):
        data = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "get_notes",
                    "input": {"limit": 3},
                }
            ]
        }
        result = _parse_anthropic_response(data)
        assert result.content is None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "toolu_123"
        assert result.tool_calls[0].name == "get_notes"

    def test_parses_mixed_content(self):
        data = {
            "content": [
                {"type": "text", "text": "Let me check"},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "get_notes",
                    "input": {},
                },
            ]
        }
        result = _parse_anthropic_response(data)
        assert result.content == "Let me check"
        assert len(result.tool_calls) == 1


class TestChatComplete:
    """Test the chat_complete orchestration function."""

    async def test_returns_response_on_success(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        api_response = {"choices": [{"message": {"content": "Hi!", "role": "assistant"}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        messages = [{"role": "user", "content": "Hello"}]

        with (
            patch("src.ai_client.settings.deepseek_api_key", "test-key"),
            patch("src.ai_client.settings.deepseek_model", "deepseek-chat"),
        ):
            result = await chat_complete(["deepseek"], messages)

        assert result is not None
        assert result.content == "Hi!"

    async def test_falls_back_on_rate_limit(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        rate_limited = mock_httpx_response_factory(status_code=429)
        ok_response = mock_httpx_response_factory(
            {"candidates": [{"content": {"parts": [{"text": "Gemini ok"}]}}]}, 200
        )

        async def fake_post(url: str, **kwargs):
            if "deepseek" in url:
                return rate_limited
            if "generativelanguage" in url:
                return ok_response
            return mock_httpx_response_factory(status_code=404)

        mock_ai_http.post.side_effect = fake_post

        messages = [{"role": "user", "content": "Hello"}]

        with (
            patch("src.ai_client.settings.deepseek_api_key", "test-key"),
            patch("src.ai_client.settings.deepseek_model", "deepseek-chat"),
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
        ):
            result = await chat_complete(["deepseek", "gemini"], messages)

        assert result is not None
        assert result.content == "Gemini ok"

    async def test_returns_none_when_all_fail(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, no_fallback_keys
    ):
        messages = [{"role": "user", "content": "Hello"}]

        result = await chat_complete(["deepseek"], messages)
        assert result is None

    async def test_passes_tools_in_request(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        api_response = {"choices": [{"message": {"content": "ok", "role": "assistant"}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        messages = [{"role": "user", "content": "Hello"}]

        with (
            patch("src.ai_client.settings.deepseek_api_key", "test-key"),
            patch("src.ai_client.settings.deepseek_model", "deepseek-chat"),
        ):
            result = await chat_complete(["deepseek"], messages, tools=SAMPLE_TOOLS)

        assert result is not None
        # Verify tools were included in the request
        call_kwargs = mock_ai_http.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "tools" in payload
        assert payload["tools"][0]["type"] == "function"

    async def test_network_error_returns_none(
        self, mock_ai_http, mock_rate_limiter, no_fallback_keys
    ):
        mock_ai_http.post.side_effect = httpx.ConnectError("Connection refused")

        messages = [{"role": "user", "content": "Hello"}]

        with (
            patch("src.ai_client.settings.deepseek_api_key", "test-key"),
            patch("src.ai_client.settings.deepseek_model", "deepseek-chat"),
        ):
            result = await chat_complete(["deepseek"], messages)

        assert result is None

    async def test_gemini_chat_complete(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Gemini provider returns ChatResponse via chat_complete."""
        api_response = {"candidates": [{"content": {"parts": [{"text": "Gemini says hi"}]}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]

        with patch("src.ai_client.settings.gemini_api_key", "test-key"):
            result = await chat_complete(["gemini"], messages)

        assert result is not None
        assert result.content == "Gemini says hi"

    async def test_gemini_with_tool_call(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Gemini returns function call in response."""
        api_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"functionCall": {"name": "get_notes", "args": {"limit": 2}}}]
                    }
                }
            ]
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        messages = [{"role": "user", "content": "Show notes"}]

        with patch("src.ai_client.settings.gemini_api_key", "test-key"):
            result = await chat_complete(["gemini"], messages, tools=SAMPLE_TOOLS)

        assert result is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_notes"

    async def test_gemini_rate_limit(
        self,
        mock_httpx_response_factory,
        mock_ai_http,
        mock_rate_limiter,
        mock_ai_sleep,
        no_fallback_keys,
    ):
        """Gemini 429 exhausts retries and returns None."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=429)

        with patch("src.ai_client.settings.gemini_api_key", "test-key"):
            result = await chat_complete(["gemini"], [{"role": "user", "content": "Hi"}])

        assert result is None

    async def test_anthropic_chat_complete(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Anthropic provider returns ChatResponse via chat_complete."""
        api_response = {"content": [{"type": "text", "text": "Claude says hi"}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]

        with patch("src.ai_client.settings.anthropic_bot_api_key", "test-key"):
            result = await chat_complete(["anthropic"], messages)

        assert result is not None
        assert result.content == "Claude says hi"

    async def test_anthropic_with_tool_use(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Anthropic returns tool_use block in response."""
        api_response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_abc",
                    "name": "get_notes",
                    "input": {"limit": 3},
                }
            ]
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        messages = [{"role": "user", "content": "Show notes"}]

        with patch("src.ai_client.settings.anthropic_bot_api_key", "test-key"):
            result = await chat_complete(["anthropic"], messages, tools=SAMPLE_TOOLS)

        assert result is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "toolu_abc"

    async def test_anthropic_rate_limit(
        self,
        mock_httpx_response_factory,
        mock_ai_http,
        mock_rate_limiter,
        mock_ai_sleep,
        no_fallback_keys,
    ):
        """Anthropic 429 exhausts retries and returns None."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=429)

        with patch("src.ai_client.settings.anthropic_bot_api_key", "test-key"):
            result = await chat_complete(["anthropic"], [{"role": "user", "content": "Hi"}])

        assert result is None

    async def test_server_error_returns_none(
        self,
        mock_httpx_response_factory,
        mock_ai_http,
        mock_rate_limiter,
        mock_ai_sleep,
        no_fallback_keys,
    ):
        """5xx server error exhausts retries and returns None."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=500)

        with (
            patch("src.ai_client.settings.deepseek_api_key", "test-key"),
            patch("src.ai_client.settings.deepseek_model", "deepseek-chat"),
        ):
            result = await chat_complete(["deepseek"], [{"role": "user", "content": "Hi"}])

        assert result is None

    async def test_unknown_provider_returns_none(self, mock_rate_limiter, no_fallback_keys):
        """Unknown provider name returns None."""
        result = await chat_complete(["nonexistent"], [{"role": "user", "content": "Hi"}])
        assert result is None
