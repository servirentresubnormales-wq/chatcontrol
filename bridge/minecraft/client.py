from __future__ import annotations

import asyncio
import logging
import socket
import threading
from typing import Any

from core.config import Config
from core.exceptions import ConnectionError, ConnectionTimeoutError, ProtocolError
from core.models import BridgeRequest, BridgeResponse
from core.protocol import (
    deserialize_auth_response,
    deserialize_response,
    serialize_auth_request,
    serialize_request,
    validate_request,
)

logger = logging.getLogger(__name__)


class MinecraftClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._connected = False
        self._authenticated = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def connect(self) -> None:
        with self._lock:
            if self._connected:
                return
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self._config.request_timeout)
                self._sock.connect((self._config.host, self._config.port))
                self._connected = True
                logger.info(
                    "[INFO] Connected to Minecraft Core at %s:%d",
                    self._config.host,
                    self._config.port,
                )
            except OSError as e:
                self._connected = False
                raise ConnectionError(f"Failed to connect: {e}") from e

    def authenticate(self) -> bool:
        with self._lock:
            if not self._connected or not self._sock:
                raise ConnectionError("Not connected to Minecraft Core")

            token = self._config.auth_token
            if not token:
                self._authenticated = True
                return True

            try:
                payload = serialize_auth_request(token) + "\n"
                self._sock.sendall(payload.encode("utf-8"))
                logger.info("[INFO] Sending auth handshake")

                data = self._sock.recv(65536)
                if not data:
                    self._connected = False
                    raise ConnectionError("Connection closed by server during auth")

                raw = data.decode("utf-8").strip()
                auth_response = deserialize_auth_response(raw)

                if auth_response.get("success"):
                    self._authenticated = True
                    logger.info("[INFO] Authenticated with Minecraft Core")
                    return True
                else:
                    self._authenticated = False
                    error = auth_response.get("error", "UNAUTHORIZED")
                    message = auth_response.get("message", "Authentication failed")
                    logger.warning("[WARNING] Authentication failed: %s - %s", error, message)
                    return False

            except ProtocolError as e:
                self._authenticated = False
                logger.error("[ERROR] Auth protocol error: %s", e)
                return False
            except OSError as e:
                self._connected = False
                self._authenticated = False
                raise ConnectionError(f"Auth failed: {e}") from e

    def disconnect(self) -> None:
        with self._lock:
            self._connected = False
            self._authenticated = False
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            logger.info("[INFO] Disconnected from Minecraft Core")

    def send_request(self, request: BridgeRequest) -> BridgeResponse:
        errors = validate_request(request)
        if errors:
            from core.models import BridgeResponse as BR
            return BR(success=False, error="INVALID_REQUEST", message="; ".join(errors))

        payload = serialize_request(request) + "\n"

        with self._lock:
            if not self._connected or not self._sock:
                return BridgeResponse(
                    success=False,
                    error="NOT_CONNECTED",
                    message="Not connected to Minecraft Core",
                )

            if not self._authenticated:
                return BridgeResponse(
                    success=False,
                    error="NOT_AUTHENTICATED",
                    message="Not authenticated with Minecraft Core",
                )

            try:
                self._sock.sendall(payload.encode("utf-8"))
                logger.info("[INFO] Sending action %s", request.action)
            except OSError as e:
                self._connected = False
                raise ConnectionError(f"Send failed: {e}") from e

            try:
                data = self._sock.recv(65536)
                if not data:
                    self._connected = False
                    raise ConnectionError("Connection closed by server")
                raw = data.decode("utf-8").strip()
                response = deserialize_response(raw)
                if response.success:
                    logger.info(
                        "[INFO] Action %s executed successfully",
                        request.action,
                    )
                else:
                    logger.warning(
                        "[WARNING] Action %s failed: %s",
                        request.action,
                        response.error,
                    )
                return response
            except ConnectionTimeoutError:
                raise
            except ConnectionError:
                self._connected = False
                raise
            except OSError as e:
                self._connected = False
                raise ConnectionError(f"Receive failed: {e}") from e

    def send_and_wait(self, request: BridgeRequest) -> BridgeResponse:
        try:
            return self.send_request(request)
        except ConnectionTimeoutError:
            logger.error("[ERROR] Request timed out")
            return BridgeResponse(
                success=False,
                error="TIMEOUT",
                message="Request timed out",
            )
        except ConnectionError as e:
            logger.error("[ERROR] Connection error: %s", e)
            return BridgeResponse(
                success=False,
                error="CONNECTION_ERROR",
                message=str(e),
            )

    def reconnect(self) -> None:
        delay = self._config.reconnect_delay
        logger.info("[INFO] Reconnecting in %d seconds...", delay)
        self.disconnect()
        import time
        time.sleep(delay)
        self.connect()
