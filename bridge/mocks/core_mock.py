from __future__ import annotations

import hmac
import json
import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 1

VALID_ACTIONS = frozenset({
    "zombie", "spiders", "slowness", "blindness", "creeper",
    "storm", "random_teleport", "explosion", "random_event", "chickens",
})

BYPASS_COOLDOWN_ACTIONS = frozenset({"chickens"})


class ErrorCode:
    INVALID_JSON = "INVALID_JSON"
    MISSING_ACTION = "MISSING_ACTION"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    ACTION_DISABLED = "ACTION_DISABLED"
    PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"
    NO_PLAYERS_ONLINE = "NO_PLAYERS_ONLINE"
    INVALID_PARAMS = "INVALID_PARAMS"
    ON_COOLDOWN = "ON_COOLDOWN"
    RATE_LIMITED = "RATE_LIMITED"
    SYSTEM_DISABLED = "SYSTEM_DISABLED"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_PROTOCOL = "INVALID_PROTOCOL"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ConnectionState:
    IDLE = "idle"
    AUTHENTICATED = "authenticated"
    REJECTED = "rejected"


@dataclass
class ActionResponse:
    success: bool = True
    error: str | None = None
    message: str | None = None


@dataclass
class ClientState:
    connection_id: str
    state: str = ConnectionState.IDLE
    authenticated: bool = False
    last_action_time: float = 0.0
    action_count: int = 0


class CoreMock:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        auth_token: str = "TEST_TOKEN",
        auth_enabled: bool = True,
        auth_timeout: float = 10.0,
        max_failed_attempts: int = 5,
        system_enabled: bool = True,
        default_cooldown: float = 0.0,
    ) -> None:
        self._host = host
        self._port = port
        self._auth_token = auth_token
        self._auth_enabled = auth_enabled
        self._auth_timeout = auth_timeout
        self._max_failed_attempts = max_failed_attempts
        self._system_enabled = system_enabled
        self._default_cooldown = default_cooldown

        self._server_socket: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None

        self._clients: dict[str, ClientState] = {}
        self._clients_lock = threading.Lock()
        self._connection_counter = 0

        self._action_responses: dict[str, ActionResponse] = {}
        self._cooldowns: dict[str, float] = {}
        self._failed_attempts: dict[str, list[float]] = {}
        self._received_requests: list[dict[str, Any]] = []
        self._received_lock = threading.Lock()

        self._force_disconnect: bool = False

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def set_action_response(self, action: str, success: bool = True, error: str | None = None, message: str | None = None) -> None:
        self._action_responses[action] = ActionResponse(success=success, error=error, message=message)

    def set_system_enabled(self, enabled: bool) -> None:
        self._system_enabled = enabled

    def set_auth_enabled(self, enabled: bool) -> None:
        self._auth_enabled = enabled

    def set_default_cooldown(self, seconds: float) -> None:
        self._default_cooldown = seconds

    def set_cooldown(self, action: str, seconds: float) -> None:
        self._cooldowns[action] = seconds

    def set_force_disconnect(self, force: bool) -> None:
        self._force_disconnect = force

    def get_received_requests(self) -> list[dict[str, Any]]:
        with self._received_lock:
            return list(self._received_requests)

    def clear_received_requests(self) -> None:
        with self._received_lock:
            self._received_requests.clear()

    def get_client_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(0.5)
        self._server_socket.bind((self._host, self._port))
        self._server_socket.listen(5)
        self._thread = threading.Thread(target=self._run, name="CoreMock", daemon=True)
        self._thread.start()
        logger.info("[CoreMock] Listening on %s:%d", self._host, self._port)

    def stop(self) -> None:
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("[CoreMock] Stopped")

    def _run(self) -> None:
        while self._running:
            try:
                client_sock, addr = self._server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    name=f"CoreMock-Client",
                    daemon=True,
                )
                client_thread.start()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.error("[CoreMock] Accept error")
                break

    def _handle_client(self, sock: socket.socket, addr: tuple) -> None:
        with self._clients_lock:
            self._connection_counter += 1
            conn_id = f"mock-{self._connection_counter}"
            client = ClientState(connection_id=conn_id)
            self._clients[conn_id] = client

        logger.info("[CoreMock] Client connected: %s (%s)", addr, conn_id)

        try:
            sock.settimeout(self._auth_timeout)

            if self._auth_enabled:
                authenticated = self._handle_auth(sock, client)
                if not authenticated:
                    return
            else:
                client.state = ConnectionState.AUTHENTICATED
                client.authenticated = True

            sock.settimeout(60.0)

            while self._running:
                try:
                    line = self._read_line(sock)
                    if line is None:
                        break

                    if not line:
                        continue

                    if len(line) > 8192:
                        self._send_response(sock, self._error_response(
                            ErrorCode.INVALID_JSON, "Message too large"
                        ))
                        continue

                    response = self._process_command(line, client)
                    self._send_response(sock, response)

                except socket.timeout:
                    continue
                except (ConnectionError, OSError):
                    break

        except (ConnectionError, OSError) as e:
            logger.debug("[CoreMock] Client error: %s", e)
        finally:
            with self._clients_lock:
                self._clients.pop(conn_id, None)
            try:
                sock.close()
            except OSError:
                pass
            logger.info("[CoreMock] Client disconnected: %s", conn_id)

    def _handle_auth(self, sock: socket.socket, client: ClientState) -> bool:
        client.state = "authenticating"

        try:
            auth_line = self._read_line(sock)
            if auth_line is None:
                client.state = ConnectionState.REJECTED
                return False

            try:
                auth_json = json.loads(auth_line)
            except json.JSONDecodeError:
                self._send_auth_response(sock, False, ErrorCode.INVALID_JSON, "Invalid JSON")
                client.state = ConnectionState.REJECTED
                self._record_failed_attempt(client.connection_id)
                return False

            if not isinstance(auth_json, dict):
                self._send_auth_response(sock, False, ErrorCode.INVALID_JSON, "Invalid JSON")
                client.state = ConnectionState.REJECTED
                self._record_failed_attempt(client.connection_id)
                return False

            msg_type = auth_json.get("type", "")
            if msg_type != "auth":
                self._send_auth_response(sock, False, ErrorCode.INVALID_PROTOCOL, "Expected auth message")
                client.state = ConnectionState.REJECTED
                self._record_failed_attempt(client.connection_id)
                return False

            protocol_version = auth_json.get("protocol_version")
            if protocol_version is None or protocol_version != PROTOCOL_VERSION:
                self._send_auth_response(sock, False, ErrorCode.INVALID_PROTOCOL, "Unsupported protocol version")
                client.state = ConnectionState.REJECTED
                self._record_failed_attempt(client.connection_id)
                return False

            token = auth_json.get("token", "")
            if not self._validate_token(token):
                self._send_auth_response(sock, False, ErrorCode.UNAUTHORIZED, "Invalid token")
                client.state = ConnectionState.REJECTED
                self._record_failed_attempt(client.connection_id)
                logger.warning("[CoreMock] Auth failed for %s", client.connection_id)
                return False

            client.state = ConnectionState.AUTHENTICATED
            client.authenticated = True
            self._clear_failed_attempts(client.connection_id)
            self._send_auth_response(sock, True, None, "Authenticated")
            logger.info("[CoreMock] Client authenticated: %s", client.connection_id)
            return True

        except (ConnectionError, OSError):
            client.state = ConnectionState.REJECTED
            return False

    def _validate_token(self, token: str) -> bool:
        if not self._auth_enabled:
            return True
        if not self._auth_token:
            return True
        return hmac.compare_digest(self._auth_token.encode("utf-8"), token.encode("utf-8"))

    def _record_failed_attempt(self, conn_id: str) -> None:
        if self._max_failed_attempts <= 0:
            return
        now = time.time()
        attempts = self._failed_attempts.setdefault(conn_id, [])
        window = 300.0
        cutoff = now - window
        self._failed_attempts[conn_id] = [t for t in attempts if t > cutoff]
        self._failed_attempts[conn_id].append(now)

    def _clear_failed_attempts(self, conn_id: str) -> None:
        self._failed_attempts.pop(conn_id, None)

    def _is_rate_limited(self, conn_id: str) -> bool:
        if self._max_failed_attempts <= 0:
            return False
        attempts = self._failed_attempts.get(conn_id, [])
        window = 300.0
        cutoff = time.time() - window
        recent = [t for t in attempts if t > cutoff]
        return len(recent) >= self._max_failed_attempts

    def _process_command(self, line: str, client: ClientState) -> dict[str, Any]:
        if not client.authenticated and self._auth_enabled:
            return self._error_response(ErrorCode.UNAUTHORIZED, "Not authenticated")

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            return self._error_response(ErrorCode.INVALID_JSON)

        if not isinstance(request, dict):
            return self._error_response(ErrorCode.INVALID_JSON)

        protocol_version = request.get("protocol_version")
        if protocol_version is None:
            return self._error_response(ErrorCode.INVALID_PROTOCOL, "Missing protocol_version")
        if protocol_version != PROTOCOL_VERSION:
            return self._error_response(ErrorCode.INVALID_PROTOCOL, f"Unsupported protocol version: {protocol_version}")

        action = request.get("action")
        if not action:
            return self._error_response(ErrorCode.MISSING_ACTION)

        if action not in VALID_ACTIONS:
            return self._error_response(ErrorCode.UNKNOWN_ACTION, f"Unknown action: {action}")

        if not self._system_enabled:
            return self._error_response(ErrorCode.SYSTEM_DISABLED, "System is not active")

        target = request.get("target") or request.get("player") or "Streamer"
        if target != "Streamer":
            return self._error_response(ErrorCode.PLAYER_NOT_FOUND, f"Player not found: {target}")

        with self._received_lock:
            self._received_requests.append(request)

        now = time.time()
        if action not in BYPASS_COOLDOWN_ACTIONS:
            cooldown = self._cooldowns.get(action, self._default_cooldown)
            if cooldown > 0 and client.last_action_time > 0:
                elapsed = now - client.last_action_time
                if elapsed < cooldown:
                    remaining = cooldown - elapsed
                    return self._error_response(ErrorCode.ON_COOLDOWN, f"Action on cooldown ({remaining:.1f}s remaining)")

        client.last_action_time = now
        client.action_count += 1

        custom = self._action_responses.get(action)
        if custom is not None:
            if custom.success:
                resp = self._success_response(action, target, custom.message)
            else:
                error = custom.error or ErrorCode.EXECUTION_ERROR
                resp = self._error_response(error, custom.message)
        else:
            resp = self._success_response(action, target)

        message_id = request.get("message_id")
        if message_id:
            resp["message_id"] = message_id
        return resp

    def _success_response(self, action: str, target: str, message: str | None = None) -> dict[str, Any]:
        return {
            "success": True,
            "action": action,
            "target": target,
            "message": message or f"Mock action '{action}' executed.",
            "protocol_version": PROTOCOL_VERSION,
            "execution_time_ms": 1,
        }

    def _error_response(self, error: str, message: str | None = None) -> dict[str, Any]:
        default_messages = {
            ErrorCode.INVALID_JSON: "Invalid JSON format",
            ErrorCode.MISSING_ACTION: "Missing 'action' field",
            ErrorCode.UNKNOWN_ACTION: "Unknown action",
            ErrorCode.ACTION_DISABLED: "Action is disabled",
            ErrorCode.PLAYER_NOT_FOUND: "Player not found",
            ErrorCode.NO_PLAYERS_ONLINE: "No players online",
            ErrorCode.INVALID_PARAMS: "Invalid parameters",
            ErrorCode.ON_COOLDOWN: "Action is on cooldown",
            ErrorCode.RATE_LIMITED: "Rate limit exceeded",
            ErrorCode.SYSTEM_DISABLED: "System is not active",
            ErrorCode.UNAUTHORIZED: "Unauthorized",
            ErrorCode.INVALID_PROTOCOL: "Invalid protocol version",
            ErrorCode.EXECUTION_ERROR: "Error executing action",
        }
        return {
            "success": False,
            "error": error,
            "message": message or default_messages.get(error, "Unknown error"),
            "protocol_version": PROTOCOL_VERSION,
        }

    def _send_auth_response(self, sock: socket.socket, success: bool, error: str | None, message: str) -> None:
        response = {
            "type": "auth",
            "success": success,
            "message": message,
            "protocol_version": PROTOCOL_VERSION,
        }
        if error:
            response["error"] = error
        self._send_response(sock, response)

    def _send_response(self, sock: socket.socket, response: dict[str, Any]) -> None:
        data = json.dumps(response, ensure_ascii=False) + "\n"
        try:
            sock.sendall(data.encode("utf-8"))
        except (ConnectionError, OSError):
            pass

    def _read_line(self, sock: socket.socket) -> str | None:
        buffer = b""
        while True:
            try:
                chunk = sock.recv(1)
                if not chunk:
                    return None
                if chunk == b"\n":
                    return buffer.decode("utf-8").rstrip("\r")
                buffer += chunk
            except socket.timeout:
                if not self._running:
                    return None
                continue
            except (ConnectionError, OSError):
                return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ChatControl Core Mock Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--token", default="TEST_TOKEN", help="Auth token (default: TEST_TOKEN)")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")
    parser.add_argument("--cooldown", type=float, default=0.0, help="Default cooldown seconds (default: 0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(name)s: %(message)s")

    mock = CoreMock(
        host=args.host,
        port=args.port,
        auth_token=args.token,
        auth_enabled=not args.no_auth,
        default_cooldown=args.cooldown,
    )

    import signal

    def shutdown(sig, frame):
        logger.info("Shutting down...")
        mock.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    mock.start()
    logger.info("Core Mock running. Press Ctrl+C to stop.")
    try:
        while mock._running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        mock.stop()


if __name__ == "__main__":
    main()
