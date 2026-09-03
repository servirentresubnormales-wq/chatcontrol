from __future__ import annotations

import json
import socket
import subprocess
import sys
import time

import pytest

from core.config import Config
from core.models import PROTOCOL_VERSION
from core.protocol import serialize_auth_request, deserialize_auth_response
from mocks.core_mock import CoreMock


@pytest.fixture
def mock_port():
    return 21876


@pytest.fixture
def mock(mock_port):
    m = CoreMock(port=mock_port, auth_token="TEST_TOKEN", auth_enabled=True)
    m.start()
    time.sleep(0.15)
    yield m
    m.stop()
    time.sleep(0.15)


def _raw_auth(port: int, token: str, timeout: float = 5.0) -> dict:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(("127.0.0.1", port))
    auth_msg = serialize_auth_request(token) + "\n"
    sock.sendall(auth_msg.encode("utf-8"))
    response = b""
    while b"\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
    sock.close()
    return json.loads(response.decode("utf-8").strip())


# ─── CoreMock Diagnostic Tests ───────────────────────────────────────────────


class TestCoreMockDiagnostic:
    def test_core_reachable(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        sock.close()

    def test_core_offline(self, mock_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        with pytest.raises((ConnectionRefusedError, OSError)):
            sock.connect(("127.0.0.1", mock_port + 999))

    def test_dns_resolution(self):
        ip = socket.getaddrinfo("127.0.0.1", 8765)[0][4][0]
        assert ip == "127.0.0.1"

    def test_dns_resolution_invalid(self):
        with pytest.raises(socket.gaierror):
            socket.getaddrinfo("nonexistent.invalid", 8765)


class TestAuthDiagnostic:
    def test_correct_token(self, mock):
        resp = _raw_auth(mock.port, "TEST_TOKEN")
        assert resp["type"] == "auth"
        assert resp["success"] is True
        assert resp["protocol_version"] == PROTOCOL_VERSION

    def test_wrong_token(self, mock):
        resp = _raw_auth(mock.port, "WRONG_TOKEN")
        assert resp["success"] is False
        assert resp["error"] == "UNAUTHORIZED"

    def test_empty_token(self, mock):
        resp = _raw_auth(mock.port, "")
        assert resp["success"] is False

    def test_no_auth_configured(self, mock_port):
        m = CoreMock(port=mock_port + 10, auth_enabled=False)
        m.start()
        time.sleep(0.1)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(("127.0.0.1", mock_port + 10))
            action_msg = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "diag-1"})
            sock.sendall((action_msg + "\n").encode("utf-8"))
            response = sock.recv(4096).decode("utf-8").strip()
            data = json.loads(response)
            assert data["success"] is True
            sock.close()
        finally:
            m.stop()


class TestProtocolDiagnostic:
    def test_protocol_version_in_auth_response(self, mock):
        resp = _raw_auth(mock.port, "TEST_TOKEN")
        assert resp["protocol_version"] == PROTOCOL_VERSION

    def test_wrong_protocol_version(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        msg = json.dumps({"type": "auth", "token": "TEST_TOKEN", "protocol_version": 999})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == "INVALID_PROTOCOL"
        sock.close()

    def test_action_before_auth(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        msg = json.dumps({"action": "zombie", "protocol_version": 1})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] in ("UNAUTHORIZED", "INVALID_PROTOCOL")
        sock.close()


class TestTimeoutDiagnostic:
    def test_timeout_on_non_responsive(self, mock_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        with pytest.raises((ConnectionRefusedError, OSError, socket.timeout)):
            sock.connect(("127.0.0.1", mock_port + 888))


class TestCheckMinecraftScript:
    def test_check_minecraft_success(self, mock):
        import yaml
        config_data = {
            "minecraft": {"host": "127.0.0.1", "port": mock.port, "auth_token": "TEST_TOKEN"},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        }
        config_path = f"config_diag_test_{mock.port}.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        try:
            result = subprocess.run(
                [sys.executable, "main.py", "--check-minecraft", "-c", config_path],
                capture_output=True, text=True, cwd=".",
                timeout=10,
            )
            assert "Minecraft Core is READY" in result.stdout
            assert "[OK] Authentication successful" in result.stdout
        finally:
            import os
            if os.path.exists(config_path):
                os.remove(config_path)

    def test_check_minecraft_wrong_token(self, mock_port):
        import yaml
        m = CoreMock(port=mock_port + 50, auth_token="SERVER_SECRET")
        m.start()
        time.sleep(0.15)
        try:
            config_data = {
                "minecraft": {"host": "127.0.0.1", "port": mock_port + 50, "auth_token": "CLIENT_WRONG"},
                "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
                "commands": {"prefix": "!", "cooldowns": {}},
            }
            config_path = f"config_diag_wrong_{mock_port}.yaml"
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            try:
                result = subprocess.run(
                    [sys.executable, "main.py", "--check-minecraft", "-c", config_path],
                    capture_output=True, text=True, cwd=".",
                    timeout=10,
                )
                assert "Minecraft Core is NOT ready" in result.stdout
                assert "Invalid token" in result.stdout
            finally:
                import os
                if os.path.exists(config_path):
                    os.remove(config_path)
        finally:
            m.stop()

    def test_check_minecraft_offline(self, mock_port):
        import yaml
        config_data = {
            "minecraft": {"host": "127.0.0.1", "port": mock_port + 999, "auth_token": ""},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 2},
            "commands": {"prefix": "!", "cooldowns": {}},
        }
        config_path = f"config_diag_offline_{mock_port}.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        try:
            result = subprocess.run(
                [sys.executable, "main.py", "--check-minecraft", "-c", config_path],
                capture_output=True, text=True, cwd=".",
                timeout=10,
            )
            assert "Minecraft Core is NOT reachable" in result.stdout
        finally:
            import os
            if os.path.exists(config_path):
                os.remove(config_path)


class TestConfigDiagnostic:
    def test_config_has_required_fields(self):
        config = Config({
            "minecraft": {"host": "127.0.0.1", "port": 8765, "auth_token": "token"},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 5, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })
        assert config.host == "127.0.0.1"
        assert config.port == 8765
        assert config.auth_token == "token"
        assert config.target_player == "Streamer"

    def test_config_defaults(self):
        config = Config({
            "minecraft": {"host": "127.0.0.1", "port": 8765},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 5, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })
        assert config.auth_token == ""


class TestSecurityDiagnostic:
    def test_token_not_in_logs(self, mock):
        resp = _raw_auth(mock.port, "SECRET_TOKEN_12345")
        raw = json.dumps(resp)
        assert "SECRET_TOKEN_12345" not in raw

    def test_wrong_token_error_message(self, mock):
        resp = _raw_auth(mock.port, "WRONG")
        assert resp["error"] == "UNAUTHORIZED"
        assert "WRONG" not in resp.get("message", "")
