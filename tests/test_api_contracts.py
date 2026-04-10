"""API contract tests: handler registration, signatures, endpoint consistency."""

import inspect
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.telegram.admin import admin_callback_router
from src.telegram.handlers import (
    WAITING_FOR_COMMAND,
    enter_your_command_from_hub,
    handle_command_input,
    hub_callback_router,
)
from src.telegram.payments import buy_package_callback
from src.telegram.settings_handlers import lang_buttons, provider_buttons
from src.telegram.setup import ADMIN_COMMANDS, BOT_COMMANDS, COMMAND_HANDLERS
from src.whatsapp.app import create_fastapi_app


class TestCommandHandlerContracts:
    """Every registered command handler is async and has the correct signature."""

    def test_all_handlers_are_callable(self):
        non_callable = [name for name, handler in COMMAND_HANDLERS.items() if not callable(handler)]
        assert not non_callable, f"Non-callable handlers: {non_callable}"

    def test_all_handlers_are_async(self):
        non_async = [
            name
            for name, handler in COMMAND_HANDLERS.items()
            if not inspect.iscoroutinefunction(handler)
        ]
        assert not non_async, f"Sync handlers (must be async): {non_async}"

    def test_all_handlers_accept_update_and_context(self):
        """Each handler must accept (update, context) positional params."""
        bad = []
        for name, handler in COMMAND_HANDLERS.items():
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())
            if len(params) < 2:
                bad.append(f"{name}: only {len(params)} params ({params})")
        assert not bad, "Handlers with wrong signature:\n" + "\n".join(f"  {b}" for b in bad)


class TestBotMenuConsistency:
    """Bot command menus are consistent with registered handlers."""

    def test_bot_commands_registered(self):
        """Every command in BOT_COMMANDS menu is registered in COMMAND_HANDLERS."""
        unregistered = []
        for lang, commands in BOT_COMMANDS.items():
            for cmd in commands:
                if cmd.command not in COMMAND_HANDLERS:
                    unregistered.append(f"{cmd.command} ({lang})")
        assert not unregistered, f"Menu commands not in COMMAND_HANDLERS: {unregistered}"

    def test_admin_commands_registered(self):
        """Every command in ADMIN_COMMANDS menu is registered in COMMAND_HANDLERS."""
        unregistered = [
            cmd.command for cmd in ADMIN_COMMANDS if cmd.command not in COMMAND_HANDLERS
        ]
        assert not unregistered, f"Admin commands not in COMMAND_HANDLERS: {unregistered}"

    def test_all_languages_have_same_commands(self):
        """All languages in BOT_COMMANDS define the same set of commands."""
        langs = list(BOT_COMMANDS.keys())
        reference = {cmd.command for cmd in BOT_COMMANDS[langs[0]]}
        mismatched = {}
        for lang in langs[1:]:
            commands = {cmd.command for cmd in BOT_COMMANDS[lang]}
            if commands != reference:
                mismatched[lang] = {
                    "missing": reference - commands,
                    "extra": commands - reference,
                }
        assert not mismatched, f"Language command mismatch vs {langs[0]}: {mismatched}"


class TestCallbackQueryContracts:
    """Callback query handlers match expected patterns."""

    def test_hub_callback_handler_is_async(self):
        assert inspect.iscoroutinefunction(hub_callback_router)

    def test_admin_callback_handler_is_async(self):
        assert inspect.iscoroutinefunction(admin_callback_router)

    def test_lang_buttons_handler_is_async(self):
        assert inspect.iscoroutinefunction(lang_buttons)

    def test_provider_buttons_handler_is_async(self):
        assert inspect.iscoroutinefunction(provider_buttons)

    def test_buy_package_callback_handler_is_async(self):
        assert inspect.iscoroutinefunction(buy_package_callback)


class TestFastAPIContracts:
    """FastAPI app exposes expected endpoints."""

    def test_health_endpoint_exists(self):
        """The /health GET endpoint is registered."""
        with patch("src.whatsapp.client.get_whatsapp_client", return_value=None):
            app = create_fastapi_app()

        routes = {(r.path, tuple(r.methods)) for r in app.routes if hasattr(r, "methods")}
        assert ("/health", ("GET",)) in routes, f"Missing /health GET. Routes: {routes}"

    def test_health_returns_ok(self):
        """Health endpoint returns 200 with expected schema."""
        with patch("src.whatsapp.client.get_whatsapp_client", return_value=None):
            app = create_fastapi_app()
            client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body, f"Missing 'status' key in response: {body}"
        assert body["status"] == "ok"


class TestConversationHandlerContract:
    """ConversationHandler for /enter_your_command is properly structured."""

    def test_waiting_state_constant_is_int(self):
        assert isinstance(WAITING_FOR_COMMAND, int)

    def test_command_input_handler_is_async(self):
        assert inspect.iscoroutinefunction(handle_command_input)

    def test_enter_from_hub_handler_is_async(self):
        assert inspect.iscoroutinefunction(enter_your_command_from_hub)
