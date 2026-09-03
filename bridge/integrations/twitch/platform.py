from __future__ import annotations

import logging
from typing import Any, Callable

from platforms.chat_platform import ChatPlatform
from platforms.models import ChatMessage
from integrations.twitch.config import TwitchConfig
from integrations.twitch.auth import TwitchAuth
from integrations.twitch.event_handler import TwitchEventHandler
from integrations.twitch.client import TwitchWSClient

logger = logging.getLogger(__name__)


class TwitchPlatform(ChatPlatform):
    """Twitch integration implementing the ChatPlatform interface.

    Manages the lifecycle of the Twitch EventSub connection and provides
    diagnostic capabilities for troubleshooting.
    """

    def __init__(self, config: TwitchConfig) -> None:
        self._config = config
        self._auth = TwitchAuth(config)
        self._event_handler = TwitchEventHandler()
        self._ws_client: TwitchWSClient | None = None
        self._on_message: Callable[[ChatMessage], None] | None = None

    @property
    def name(self) -> str:
        return "twitch"

    @property
    def connected(self) -> bool:
        return self._ws_client.connected if self._ws_client else False

    @property
    def session_id(self) -> str | None:
        return self._ws_client.session_id if self._ws_client else None

    def start(self) -> None:
        if not self._config.enabled:
            return

        logger.info("[INFO] Starting Twitch integration...")

        token_info = self._auth.validate_token()
        if not token_info.valid:
            logger.error("[ERROR] Twitch token validation failed: %s", token_info.error)
            return

        logger.info(
            "[INFO] Twitch token validated (login=%s, user_id=%s)",
            token_info.login, token_info.user_id,
        )

        has_all, missing = self._auth.has_all_required_scopes()
        if not has_all:
            logger.error(
                "[ERROR] Missing required scopes: %s",
                ", ".join(missing),
            )
            return

        if not self._config.broadcaster_id:
            self._config.broadcaster_id = token_info.user_id
            logger.info(
                "[INFO] Using authenticated user as broadcaster (user_id=%s)",
                token_info.user_id,
            )

        self._ws_client = TwitchWSClient(
            config=self._config,
            auth=self._auth,
            event_handler=self._event_handler,
            on_chat_message=self._on_message,
        )
        self._ws_client.start()
        logger.info("[INFO] Twitch EventSub client started")

    def stop(self) -> None:
        if self._ws_client:
            self._ws_client.stop()

    def set_on_message(self, callback: Callable[[ChatMessage], None]) -> None:
        self._on_message = callback
        if self._ws_client:
            self._ws_client._on_chat_message = callback

    def run_diagnostics(self) -> dict[str, Any]:
        """Run full diagnostic checks without starting the client.

        Returns a dict with diagnostic results for each step.
        """
        results = {
            "config_valid": False,
            "token_valid": False,
            "token_info": None,
            "scopes_ok": False,
            "missing_scopes": [],
            "broadcaster_id": "",
            "websocket_url": "",
            "ready": False,
            "errors": [],
        }

        config_errors = self._config.validate()
        if config_errors:
            results["errors"].extend(config_errors)
            return results
        results["config_valid"] = True

        token_info = self._auth.validate_token()
        results["token_valid"] = token_info.valid
        results["token_info"] = {
            "login": token_info.login,
            "user_id": token_info.user_id,
            "client_id": token_info.client_id,
            "scopes": token_info.scopes,
            "expires_in": token_info.expires_in,
        }
        if not token_info.valid:
            results["errors"].append(f"Token validation failed: {token_info.error}")
            return results

        has_all, missing = self._auth.has_all_required_scopes()
        results["scopes_ok"] = has_all
        results["missing_scopes"] = missing
        if not has_all:
            results["errors"].append(
                f"Missing required scopes: {', '.join(missing)}. "
                "Re-authorize with user:read:chat scope."
            )
            return results

        broadcaster_id = self._config.broadcaster_id or token_info.user_id
        results["broadcaster_id"] = broadcaster_id
        results["websocket_url"] = self._config.websocket_url.split("?")[0]
        results["ready"] = True

        return results
