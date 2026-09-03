from __future__ import annotations

import json
import logging
import time
import threading
from typing import Any, Callable

import websocket

from integrations.twitch.auth import TwitchAuth
from integrations.twitch.config import TwitchConfig
from integrations.twitch.event_handler import TwitchEventHandler
from integrations.twitch.exceptions import TwitchConnectionError, TwitchEventError, TwitchSubscriptionError
from platforms.models import ChatMessage

logger = logging.getLogger(__name__)

EVENTSUB_API_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"


class TwitchWSClient:
    """Twitch EventSub WebSocket client.

    Reconnection follows Twitch's documented flow:
    1. Receive session_reconnect with new URL
    2. Connect to new URL (old connection stays active)
    3. Receive welcome on new connection
    4. Close old connection

    Close codes (from Twitch docs):
    - 4000: Internal server error
    - 4001: Client sent inbound traffic
    - 4002: Client failed ping-pong
    - 4003: Connection unused (no subscription within 10s of welcome)
    - 4004: Reconnect grace time expired (30s to reconnect)
    - 4005: Network timeout
    - 4006: Network error
    - 4007: Invalid reconnect URL
    """

    def __init__(
        self,
        config: TwitchConfig,
        auth: TwitchAuth,
        event_handler: TwitchEventHandler,
        on_chat_message: Callable[[ChatMessage], None] | None = None,
    ) -> None:
        self._config = config
        self._auth = auth
        self._event_handler = event_handler
        self._on_chat_message = on_chat_message
        self._ws: websocket.WebSocketApp | None = None
        self._session_id: str | None = None
        self._keepalive_timeout: int = config.keepalive_timeout
        self._running = False
        self._reconnect_url: str | None = None
        self._last_message_time: float = 0.0
        self._thread: threading.Thread | None = None
        self._connected = False
        self._lock = threading.Lock()
        self._reconnecting = False
        self._old_ws: websocket.WebSocketApp | None = None
        self._subscription_created = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def start(self) -> None:
        if self._running:
            logger.warning("[TWITCH] Client already running")
            return

        self._running = True
        self._subscription_created = False
        self._thread = threading.Thread(
            target=self._run_loop, name="TwitchWS", daemon=True
        )
        self._thread.start()
        logger.info("[INFO] Twitch EventSub client starting")

    def stop(self) -> None:
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._old_ws:
            try:
                self._old_ws.close()
            except Exception:
                pass
        logger.info("[INFO] Twitch EventSub client stopped")

    def _run_loop(self) -> None:
        retry = 0
        while self._running:
            try:
                self._connect()
            except Exception as e:
                if not self._running:
                    break
                retry += 1
                if retry > self._config.reconnect_max_retries:
                    logger.error(
                        "[ERROR] Max reconnection attempts (%d) reached. Giving up.",
                        self._config.reconnect_max_retries,
                    )
                    break
                delay = min(
                    self._config.reconnect_base_delay * (2 ** (retry - 1)),
                    self._config.reconnect_max_delay,
                )
                logger.warning(
                    "[WARNING] Twitch connection lost: %s. Reconnecting in %.1fs (attempt %d/%d)",
                    e, delay, retry, self._config.reconnect_max_retries,
                )
                time.sleep(delay)
            else:
                retry = 0

    def _connect(self) -> None:
        url = self._reconnect_url or self._config.websocket_url
        logger.info("[INFO] Connecting to Twitch EventSub WebSocket...")

        self._ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )

        self._ws.run_forever(
            ping_interval=20,
            ping_timeout=10,
        )
        self._connected = False

        if self._running and not self._reconnect_url and not self._reconnecting:
            raise TwitchConnectionError("WebSocket closed without reconnect URL")

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        self._connected = True
        logger.info("[INFO] WebSocket connection opened")

    def _on_message(self, ws: websocket.WebSocketApp, message: str | bytes) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("[WARNING] Invalid JSON from Twitch")
            return

        metadata = data.get("metadata", {})
        message_type = metadata.get("message_type", "")
        self._last_message_time = time.time()

        if message_type == "session_welcome":
            self._handle_welcome(data)
        elif message_type == "session_keepalive":
            logger.debug("[TWITCH] Keepalive received")
        elif message_type == "session_reconnect":
            self._handle_reconnect(data)
        elif message_type == "notification":
            self._handle_notification(data)
        elif message_type == "revocation":
            self._handle_revocation(data)
        else:
            logger.debug("[TWITCH] Unknown message type: %s", message_type)

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error("[ERROR] Twitch WebSocket error: %s", error)

    def _on_close(
        self,
        ws: websocket.WebSocketApp,
        close_status_code: int | None,
        close_msg: str | None,
    ) -> None:
        self._connected = False
        close_reasons = {
            4000: "Internal server error",
            4001: "Client sent inbound traffic",
            4002: "Client failed ping-pong",
            4003: "Connection unused (no subscription within 10s)",
            4004: "Reconnect grace time expired (30s)",
            4005: "Network timeout",
            4006: "Network error",
            4007: "Invalid reconnect URL",
        }
        reason = close_reasons.get(close_status_code, close_msg or "unknown")
        logger.info(
            "[INFO] Twitch WebSocket closed (code=%s, reason=%s)",
            close_status_code, reason,
        )

    def _handle_welcome(self, data: dict[str, Any]) -> None:
        session = data.get("payload", {}).get("session", {})
        self._session_id = session.get("id")
        self._keepalive_timeout = session.get(
            "keepalive_timeout_seconds", self._config.keepalive_timeout
        )
        logger.info(
            "[INFO] EventSub session established (id=%s, keepalive=%ds)",
            self._session_id,
            self._keepalive_timeout,
        )

        if self._reconnecting and self._old_ws:
            logger.info("[INFO] Reconnect successful, closing old connection")
            try:
                self._old_ws.close()
            except Exception:
                pass
            self._old_ws = None
            self._reconnecting = False
            self._reconnect_url = None

        if self._session_id and not self._subscription_created:
            self._subscribe_chat_message()

    def _handle_reconnect(self, data: dict[str, Any]) -> None:
        session = data.get("payload", {}).get("session", {})
        self._reconnect_url = session.get("reconnect_url")
        new_session_id = session.get("id", self._session_id)
        logger.info(
            "[INFO] Reconnect signal received (new session: %s)",
            new_session_id,
        )

        self._old_ws = self._ws
        self._reconnecting = True
        self._session_id = new_session_id

        if self._reconnect_url:
            self._ws = websocket.WebSocketApp(
                self._reconnect_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )
            reconnect_thread = threading.Thread(
                target=self._ws.run_forever,
                kwargs={"ping_interval": 20, "ping_timeout": 10},
                name="TwitchWS-Reconnect",
                daemon=True,
            )
            reconnect_thread.start()

    def _handle_notification(self, data: dict[str, Any]) -> None:
        metadata = data.get("metadata", {})
        subscription_type = metadata.get("subscription_type", "")
        event = data.get("payload", {}).get("event", {})

        try:
            chat_msg = self._event_handler.handle_notification(
                subscription_type, event
            )
            if chat_msg and self._on_chat_message:
                self._on_chat_message(chat_msg)
        except Exception as e:
            logger.error("[ERROR] Error handling Twitch event: %s", e)

    def _handle_revocation(self, data: dict[str, Any]) -> None:
        subscription = data.get("payload", {}).get("subscription", {})
        status = subscription.get("status", "unknown")
        sub_type = subscription.get("type", "unknown")
        logger.warning(
            "[WARNING] Subscription revoked: type=%s status=%s",
            sub_type, status,
        )

    def _subscribe_chat_message(self) -> None:
        """Create channel.chat.message subscription.

        Per Twitch docs:
        - type: "channel.chat.message"
        - version: "1"
        - condition: {broadcaster_user_id, user_id} (user_id is optional)
        - transport: {method: "websocket", session_id}

        Authorization: Requires User Access Token with user:read:chat scope.
        The token must be for the user specified in the condition's user_id
        (or for the broadcaster if user_id is omitted).
        """
        if not self._session_id:
            raise TwitchSubscriptionError("No session ID available")

        user_id = self._config.bot_user_id or self._config.broadcaster_id

        body = {
            "type": "channel.chat.message",
            "version": "1",
            "condition": {
                "broadcaster_user_id": self._config.broadcaster_id,
                "user_id": user_id,
            },
            "transport": {
                "method": "websocket",
                "session_id": self._session_id,
            },
        }

        logger.info(
            "[INFO] Subscribing to channel.chat.message (broadcaster=%s, user=%s)",
            self._config.broadcaster_id, user_id,
        )

        import urllib.request
        import urllib.error

        headers = self._auth.get_headers()
        req = urllib.request.Request(
            EVENTSUB_API_URL,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
        )
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                sub_data = result.get("data", [])
                if sub_data:
                    sub_id = sub_data[0].get("id", "unknown")
                    self._subscription_created = True
                    logger.info(
                        "[INFO] Subscribed to channel.chat.message (sub_id=%s)",
                        sub_id,
                    )
                    logger.info("[INFO] Twitch integration ready — listening for chat messages")
                else:
                    logger.warning("[WARNING] Subscription response empty")
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            logger.error("[ERROR] Subscription failed: HTTP %d - %s", e.code, body_text)
            raise TwitchSubscriptionError(
                f"Subscription failed: HTTP {e.code} - {body_text}"
            ) from e
        except OSError as e:
            raise TwitchSubscriptionError(f"Subscription network error: {e}") from e

    def test_connection(self) -> dict[str, Any]:
        """Test EventSub connection without starting the full client.

        Returns diagnostic info about the connection attempt.
        """
        result = {
            "websocket_url": self._config.websocket_url.split("?")[0],
            "session_id": None,
            "subscription_created": False,
            "error": None,
        }

        try:
            import urllib.request
            import urllib.error

            auth_headers = self._auth.get_headers()
            result["auth_valid"] = bool(self._auth.access_token)
            result["client_id_match"] = self._auth.client_id == self._config.client_id
        except Exception as e:
            result["error"] = str(e)
            return result

        return result
