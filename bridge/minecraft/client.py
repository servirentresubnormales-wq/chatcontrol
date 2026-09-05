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
    deserialize_link_request,
    deserialize_unlink_request,
    serialize_auth_request,
    serialize_link_response,
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
        self._reader_running = False
        self._reader_thread: threading.Thread | None = None
        self._on_link_request = None
        self._on_unlink_request = None

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
                    self._start_reader()
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
            self._reader_running = False
            self._connected = False
            self._authenticated = False
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            logger.info("[INFO] Disconnected from Minecraft Core")

    def _start_reader(self):
        """Start the background reader thread (called after auth succeeds)."""
        if not self._reader_running:
            self._reader_running = True
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

    def _reader_loop(self):
        """Background thread: reads from socket and dispatches incoming messages."""
        buffer = b""
        while self._reader_running:
            try:
                data = self._sock.recv(65536)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    raw = line.decode("utf-8").strip()
                    if raw:
                        self._handle_incoming(raw)
            except OSError:
                break
        self._connected = False
        self._authenticated = False

    def _handle_incoming(self, raw: str):
        """Handle an incoming message from Core (not a response to our request)."""
        try:
            import json
            data = json.loads(raw)
            msg_type = data.get("type", "")
            
            if msg_type == "link_request":
                if self._on_link_request:
                    self._on_link_request(data)
            elif msg_type == "unlink_request":
                if self._on_unlink_request:
                    self._on_unlink_request(data)
            else:
                logger.debug("[CORE] Unknown message type: %s", msg_type)
        except Exception as e:
            logger.warning("[CORE] Error handling incoming message: %s", e)

    def set_link_handler(self, handler):
        """Set callback for link_request messages from Core."""
        self._on_link_request = handler

    def set_unlink_handler(self, handler):
        """Set callback for unlink_request messages from Core."""
        self._on_unlink_request = handler

    def send_raw(self, data: str) -> None:
        """Send raw data to Core (thread-safe). Used for unsolicited responses."""
        with self._lock:
            if not self._connected or not self._sock:
                raise ConnectionError("Not connected to Minecraft Core")
            try:
                self._sock.sendall(data.encode("utf-8"))
            except OSError as e:
                self._connected = False
                raise ConnectionError(f"Send failed: {e}") from e

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
