import json
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.config import Config
from core.exceptions import ConnectionError, ProtocolError
from core.models import PROTOCOL_VERSION, BridgeRequest
from core.protocol import (
    compare_tokens,
    deserialize_auth_response,
    serialize_auth_request,
)
from minecraft.client import MinecraftClient


class TestAuthProtocol:
    def test_serialize_auth_request(self):
        raw = serialize_auth_request("my-secret-token")
        data = json.loads(raw)
        assert data["type"] == "auth"
        assert data["token"] == "my-secret-token"
        assert data["protocol_version"] == PROTOCOL_VERSION

    def test_deserialize_auth_response_success(self):
        resp = {
            "type": "auth",
            "success": True,
            "message": "Authenticated",
            "protocol_version": PROTOCOL_VERSION,
        }
        result = deserialize_auth_response(json.dumps(resp))
        assert result["success"] is True
        assert result["message"] == "Authenticated"

    def test_deserialize_auth_response_failure(self):
        resp = {
            "type": "auth",
            "success": False,
            "error": "UNAUTHORIZED",
            "message": "Invalid token",
            "protocol_version": PROTOCOL_VERSION,
        }
        result = deserialize_auth_response(json.dumps(resp))
        assert result["success"] is False
        assert result["error"] == "UNAUTHORIZED"

    def test_deserialize_auth_response_invalid_json(self):
        with pytest.raises(ProtocolError, match="Invalid JSON"):
            deserialize_auth_response("not json")

    def test_deserialize_auth_response_wrong_type(self):
        resp = {"type": "command", "success": True}
        with pytest.raises(ProtocolError, match="Expected auth response"):
            deserialize_auth_response(json.dumps(resp))

    def test_deserialize_auth_response_not_dict(self):
        with pytest.raises(ProtocolError, match="Expected JSON object"):
            deserialize_auth_response('"string"')

    def test_compare_tokens_equal(self):
        assert compare_tokens("secret", "secret") is True

    def test_compare_tokens_not_equal(self):
        assert compare_tokens("secret", "wrong") is False

    def test_compare_tokens_empty(self):
        assert compare_tokens("", "") is True
        assert compare_tokens("secret", "") is False
        assert compare_tokens("", "secret") is False

    def test_compare_tokens_unicode(self):
        assert compare_tokens("café", "café") is True
        assert compare_tokens("café", "cafe") is False


class TestMinecraftClientAuth:
    def _make_config(self, auth_token: str = "test-token") -> Config:
        return Config({
            "minecraft": {"host": "127.0.0.1", "port": 8765, "auth_token": auth_token},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })

    def _mock_socket(self, auth_response: dict) -> MagicMock:
        sock = MagicMock()
        response_json = json.dumps(auth_response) + "\n"
        sock.recv.return_value = response_json.encode("utf-8")
        return sock

    @patch("socket.socket")
    def test_authenticate_success(self, mock_socket_cls):
        auth_response = {
            "type": "auth",
            "success": True,
            "message": "Authenticated",
            "protocol_version": PROTOCOL_VERSION,
        }
        sock = self._mock_socket(auth_response)
        mock_socket_cls.return_value = sock

        config = self._make_config("correct-token")
        client = MinecraftClient(config)
        client.connect()
        result = client.authenticate()

        assert result is True
        assert client.authenticated is True
        sent = sock.sendall.call_args[0][0].decode("utf-8")
        sent_data = json.loads(sent.strip())
        assert sent_data["type"] == "auth"
        assert sent_data["token"] == "correct-token"

    @patch("socket.socket")
    def test_authenticate_failure_wrong_token(self, mock_socket_cls):
        auth_response = {
            "type": "auth",
            "success": False,
            "error": "UNAUTHORIZED",
            "message": "Invalid token",
            "protocol_version": PROTOCOL_VERSION,
        }
        sock = self._mock_socket(auth_response)
        mock_socket_cls.return_value = sock

        config = self._make_config("wrong-token")
        client = MinecraftClient(config)
        client.connect()
        result = client.authenticate()

        assert result is False
        assert client.authenticated is False

    @patch("socket.socket")
    def test_authenticate_no_token_skips(self, mock_socket_cls):
        sock = MagicMock()
        mock_socket_cls.return_value = sock

        config = self._make_config("")
        client = MinecraftClient(config)
        client.connect()
        result = client.authenticate()

        assert result is True
        assert client.authenticated is True
        sock.sendall.assert_not_called()

    @patch("socket.socket")
    def test_authenticate_connection_closed(self, mock_socket_cls):
        sock = MagicMock()
        sock.recv.return_value = b""
        mock_socket_cls.return_value = sock

        config = self._make_config("token")
        client = MinecraftClient(config)
        client.connect()

        with pytest.raises(ConnectionError, match="closed by server"):
            client.authenticate()

    @patch("socket.socket")
    def test_authenticate_invalid_response(self, mock_socket_cls):
        sock = MagicMock()
        sock.recv.return_value = b"not json"
        mock_socket_cls.return_value = sock

        config = self._make_config("token")
        client = MinecraftClient(config)
        client.connect()
        result = client.authenticate()

        assert result is False
        assert client.authenticated is False

    @patch("socket.socket")
    def test_send_request_requires_auth(self, mock_socket_cls):
        mock_socket_cls.return_value = MagicMock()

        config = self._make_config("token")
        client = MinecraftClient(config)
        client.connect()

        request = BridgeRequest(action="zombie")
        response = client.send_request(request)

        assert response.success is False
        assert response.error == "NOT_AUTHENTICATED"

    @patch("socket.socket")
    def test_send_request_after_auth(self, mock_socket_cls):
        auth_response = {
            "type": "auth",
            "success": True,
            "message": "Authenticated",
            "protocol_version": PROTOCOL_VERSION,
        }
        action_response = {
            "success": True,
            "action": "zombie",
            "target": "Player1",
            "message": "OK",
            "protocol_version": PROTOCOL_VERSION,
        }

        call_count = [0]
        def mock_recv(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps(auth_response).encode("utf-8")
            return json.dumps(action_response).encode("utf-8")

        sock = MagicMock()
        sock.recv.side_effect = mock_recv
        mock_socket_cls.return_value = sock

        config = self._make_config("token")
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        request = BridgeRequest(action="zombie", target="Player1")
        response = client.send_request(request)

        assert response.success is True
        assert response.action == "zombie"

    @patch("socket.socket")
    def test_disconnect_clears_auth(self, mock_socket_cls):
        mock_socket_cls.return_value = MagicMock()

        config = self._make_config("token")
        client = MinecraftClient(config)
        client.connect()
        client._authenticated = True

        client.disconnect()
        assert client.authenticated is False
        assert client.connected is False

    @patch("socket.socket")
    def test_reconnect_clears_auth(self, mock_socket_cls):
        sock = MagicMock()
        mock_socket_cls.return_value = sock

        config = self._make_config("")
        client = MinecraftClient(config)
        client.connect()
        client._authenticated = True

        with patch("time.sleep"):
            client.reconnect()

        assert client.authenticated is False


class TestMinecraftClientAuthConfig:
    def test_config_has_auth_token(self):
        config = Config({
            "minecraft": {"host": "127.0.0.1", "port": 8765, "auth_token": "my-token"},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 5, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })
        assert config.auth_token == "my-token"

    def test_config_default_auth_token(self):
        config = Config({
            "minecraft": {"host": "127.0.0.1", "port": 8765},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 5, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })
        assert config.auth_token == ""
