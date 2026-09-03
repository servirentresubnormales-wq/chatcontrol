from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TwitchConfig:
    """Twitch configuration.

    Fields:
        enabled: Master switch for Twitch integration.
        client_id: Twitch application Client ID from dev console.
        client_secret: Twitch application Client Secret (NOT needed for User Access Token flow).
        access_token: User Access Token (obtained via OAuth, requires user:read:chat scope).
                       This is the ACCOUNT token - it represents the authenticated user.
        refresh_token: Refresh token for the access token (used to refresh expired tokens).
        broadcaster_id: Numeric user ID of the channel to monitor.
                        This is the channel owner (broadcaster), not the bot account.
        bot_user_id: Numeric user ID of the bot account (if separate from broadcaster).
                     If empty, the broadcaster's own token is used.
        channel: Display name or login of the broadcaster (for display purposes only).
        websocket_url: EventSub WebSocket URL (do not change unless Twitch updates it).
        api_base: Twitch API base URL.
        keepalive_timeout: Seconds to wait before assuming connection is dead.
        reconnect_max_retries: Max reconnection attempts before giving up.
        reconnect_base_delay: Initial delay between reconnection attempts.
        reconnect_max_delay: Maximum delay between reconnection attempts.

    Required fields for enabled=true:
        - client_id
        - access_token (User Access Token with user:read:chat scope)
        - broadcaster_id
        - channel

    Optional fields:
        - client_secret (only needed for app token flow, not used by this integration)
        - refresh_token (needed if you want automatic token refresh)
        - bot_user_id (only needed if using a separate bot account)
    """
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    broadcaster_id: str = ""
    bot_user_id: str = ""
    channel: str = ""
    websocket_url: str = "wss://eventsub.wss.twitch.tv/ws"
    api_base: str = "https://api.twitch.tv/helix"
    keepalive_timeout: int = 30
    reconnect_max_retries: int = 10
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 30.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TwitchConfig:
        twitch = data.get("twitch", {})
        return cls(
            enabled=twitch.get("enabled", False),
            client_id=twitch.get("client_id", ""),
            client_secret=twitch.get("client_secret", ""),
            access_token=twitch.get("access_token", ""),
            refresh_token=twitch.get("refresh_token", ""),
            broadcaster_id=twitch.get("broadcaster_id", ""),
            bot_user_id=twitch.get("bot_user_id", ""),
            channel=twitch.get("channel", ""),
            websocket_url=twitch.get("websocket_url", "wss://eventsub.wss.twitch.tv/ws"),
            api_base=twitch.get("api_base", "https://api.twitch.tv/helix"),
            keepalive_timeout=twitch.get("keepalive_timeout", 30),
            reconnect_max_retries=twitch.get("reconnect_max_retries", 10),
            reconnect_base_delay=twitch.get("reconnect_base_delay", 1.0),
            reconnect_max_delay=twitch.get("reconnect_max_delay", 30.0),
        )

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of error messages.

        Only validates when enabled=true. Empty list means valid.
        """
        errors: list[str] = []
        if not self.enabled:
            return errors

        if not self.client_id:
            errors.append("twitch.client_id is missing. Get it from Twitch Developer Console.")

        if not self.access_token:
            errors.append(
                "twitch.access_token is missing. "
                "Create a User Access Token with user:read:chat scope."
            )

        if not self.broadcaster_id:
            errors.append(
                "twitch.broadcaster_id is missing. "
                "This is the numeric user ID of the channel to monitor."
            )

        if not self.channel:
            errors.append(
                "twitch.channel is missing. "
                "This is the display name or login of the broadcaster."
            )

        return errors

    def log_diagnostics(self) -> None:
        """Log configuration diagnostics without exposing secrets."""
        if not self.enabled:
            logger.info("[DIAG] Twitch: DISABLED")
            return

        logger.info("[DIAG] Twitch: ENABLED")
        logger.info("[DIAG] Channel: %s", self.channel or "(not set)")
        logger.info("[DIAG] Broadcaster ID: %s", self.broadcaster_id or "(not set)")
        logger.info("[DIAG] Bot User ID: %s", self.bot_user_id or "(not set, using broadcaster token)")
        logger.info("[DIAG] Client ID: %s", "set" if self.client_id else "MISSING")
        logger.info("[DIAG] Access Token: %s", "set" if self.access_token else "MISSING")
        logger.info("[DIAG] Refresh Token: %s", "set" if self.refresh_token else "not set")
        logger.info("[DIAG] WebSocket URL: %s", self.websocket_url.split("?")[0])

        errors = self.validate()
        if errors:
            logger.error("[DIAG] Configuration errors:")
            for err in errors:
                logger.error("[DIAG]   - %s", err)
        else:
            logger.info("[DIAG] Configuration: VALID")
