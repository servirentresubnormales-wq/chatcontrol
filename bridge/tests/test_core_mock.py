from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from core.config import Config
from core.models import PROTOCOL_VERSION, BridgeRequest
from core.protocol import serialize_auth_request, serialize_request
from minecraft.client import MinecraftClient
from mocks.core_mock import CoreMock, ErrorCode


@pytest.fixture
def mock_port():
    return 18765


@pytest.fixture
def mock(mock_port):
    m = CoreMock(port=mock_port, auth_token="TEST_TOKEN", auth_enabled=True)
    m.start()
    time.sleep(0.1)
    yield m
    m.stop()
    time.sleep(0.1)


@pytest.fixture
def mock_no_auth(mock_port):
    m = CoreMock(port=mock_port + 1, auth_enabled=False)
    m.start()
    time.sleep(0.1)
    yield m
    m.stop()
    time.sleep(0.1)


@pytest.fixture
def config(mock_port):
    return Config({
        "minecraft": {"host": "127.0.0.1", "port": mock_port, "auth_token": "TEST_TOKEN"},
        "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
        "commands": {"prefix": "!", "cooldowns": {}},
    })


def _raw_send(port: int, data: str) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(("127.0.0.1", port))
    sock.sendall((data + "\n").encode("utf-8"))
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
        if b"\n" in response:
            break
    sock.close()
    return response.decode("utf-8").strip()


def _auth_handshake(port: int, token: str = "TEST_TOKEN") -> tuple[socket.socket, str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(("127.0.0.1", port))
    auth_msg = json.dumps({"type": "auth", "token": token, "protocol_version": PROTOCOL_VERSION})
    sock.sendall((auth_msg + "\n").encode("utf-8"))
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
        if b"\n" in response:
            break
    return sock, response.decode("utf-8").strip()


# ─── CoreMock Unit Tests ─────────────────────────────────────────────────────


class TestCoreMockStartStop:
    def test_start_and_stop(self, mock_port):
        m = CoreMock(port=mock_port + 10)
        m.start()
        time.sleep(0.1)
        assert m._running is True
        m.stop()
        assert m._running is False

    def test_double_start(self, mock_port):
        m = CoreMock(port=mock_port + 11)
        m.start()
        time.sleep(0.1)
        m.start()
        assert m._running is True
        m.stop()

    def test_stop_without_start(self, mock_port):
        m = CoreMock(port=mock_port + 12)
        m.stop()


class TestCoreMockAuth:
    def test_auth_correct_token(self, mock):
        sock, resp = _auth_handshake(mock.port, "TEST_TOKEN")
        data = json.loads(resp)
        assert data["type"] == "auth"
        assert data["success"] is True
        assert data["message"] == "Authenticated"
        sock.close()

    def test_auth_wrong_token(self, mock):
        sock, resp = _auth_handshake(mock.port, "WRONG_TOKEN")
        data = json.loads(resp)
        assert data["type"] == "auth"
        assert data["success"] is False
        assert data["error"] == ErrorCode.UNAUTHORIZED
        sock.close()

    def test_auth_empty_token(self, mock):
        sock, resp = _auth_handshake(mock.port, "")
        data = json.loads(resp)
        assert data["success"] is False
        sock.close()

    def test_auth_no_auth_msg_sends_action(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        action = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "test-001"})
        sock.sendall((action + "\n").encode("utf-8"))
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break
        data = json.loads(response.decode("utf-8").strip())
        assert data["success"] is False
        assert data["error"] in (ErrorCode.UNAUTHORIZED, ErrorCode.INVALID_PROTOCOL)
        sock.close()

    def test_auth_timeout(self, mock_port):
        m = CoreMock(port=mock_port + 13, auth_token="TEST_TOKEN", auth_enabled=True, auth_timeout=0.5)
        m.start()
        time.sleep(0.1)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect(("127.0.0.1", mock_port + 13))
            time.sleep(1.0)
            action = json.dumps({"action": "zombie", "protocol_version": 1})
            sock.sendall((action + "\n").encode("utf-8"))
            time.sleep(1.0)
            try:
                data = sock.recv(4096)
                if data:
                    resp = json.loads(data.decode("utf-8").strip())
                    assert resp.get("success") is False
            except (ConnectionError, OSError):
                pass
            sock.close()
        finally:
            m.stop()

    def test_auth_invalid_json(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        sock.sendall(b"not json\n")
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["type"] == "auth"
        assert data["success"] is False
        assert data["error"] == ErrorCode.INVALID_JSON
        sock.close()

    def test_auth_wrong_type(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        msg = json.dumps({"type": "command", "token": "TEST_TOKEN", "protocol_version": 1})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.INVALID_PROTOCOL
        sock.close()

    def test_auth_wrong_protocol(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        msg = json.dumps({"type": "auth", "token": "TEST_TOKEN", "protocol_version": 999})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.INVALID_PROTOCOL
        sock.close()

    def test_auth_disabled_skips_handshake(self, mock_no_auth):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock_no_auth.port))
        action = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "test-002"})
        sock.sendall((action + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is True
        assert data["action"] == "zombie"
        sock.close()


class TestCoreMockActions:
    def test_all_valid_actions(self, mock):
        for action in ["zombie", "spiders", "slowness", "blindness", "creeper",
                       "storm", "random_teleport", "explosion", "random_event", "chickens"]:
            sock, resp = _auth_handshake(mock.port)
            action_msg = json.dumps({
                "action": action, "target": "Streamer", "protocol_version": 1,
                "message_id": f"test-{action}"
            })
            sock.sendall((action_msg + "\n").encode("utf-8"))
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\n" in response:
                    break
            data = json.loads(response.decode("utf-8").strip())
            assert data["success"] is True, f"Action {action} failed: {data}"
            assert data["action"] == action
            sock.close()

    def test_unknown_action(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "nonexistent", "protocol_version": 1, "message_id": "test-unk"})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.UNKNOWN_ACTION
        sock.close()

    def test_missing_action(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"protocol_version": 1, "message_id": "test-miss"})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.MISSING_ACTION
        sock.close()

    def test_player_not_found(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({
            "action": "zombie", "target": "JugadorInexistente",
            "protocol_version": 1, "message_id": "test-pnf"
        })
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.PLAYER_NOT_FOUND
        sock.close()

    def test_system_disabled(self, mock):
        mock.set_system_enabled(False)
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "test-dis"})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.SYSTEM_DISABLED
        mock.set_system_enabled(True)
        sock.close()

    def test_invalid_json(self, mock):
        sock, _ = _auth_handshake(mock.port)
        sock.sendall(b"not json\n")
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.INVALID_JSON
        sock.close()

    def test_wrong_protocol_version(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "zombie", "protocol_version": 999, "message_id": "test-proto"})
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.INVALID_PROTOCOL
        sock.close()

    def test_message_too_large(self, mock):
        sock, _ = _auth_handshake(mock.port)
        huge_msg = json.dumps({"action": "zombie" * 2000, "protocol_version": 1})
        sock.sendall((huge_msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is False
        assert data["error"] == ErrorCode.INVALID_JSON
        sock.close()

    def test_player_alias(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({
            "action": "zombie", "player": "Streamer",
            "protocol_version": 1, "message_id": "test-alias"
        })
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is True
        assert data["action"] == "zombie"
        sock.close()

    def test_response_fields(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({
            "action": "zombie", "target": "Streamer", "source": "twitch",
            "user": "Viewer1", "protocol_version": 1, "message_id": "test-fields"
        })
        sock.sendall((msg + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(response)
        assert data["success"] is True
        assert data["action"] == "zombie"
        assert data["target"] == "Streamer"
        assert data["protocol_version"] == PROTOCOL_VERSION
        assert "execution_time_ms" in data
        sock.close()


class TestCoreMockCooldowns:
    def test_cooldown_blocks_action(self, mock):
        mock.set_default_cooldown(5.0)
        sock, _ = _auth_handshake(mock.port)
        msg1 = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "cd-1"})
        sock.sendall((msg1 + "\n").encode("utf-8"))
        resp1 = sock.recv(4096).decode("utf-8").strip()
        data1 = json.loads(resp1)
        assert data1["success"] is True

        msg2 = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "cd-2"})
        sock.sendall((msg2 + "\n").encode("utf-8"))
        resp2 = sock.recv(4096).decode("utf-8").strip()
        data2 = json.loads(resp2)
        assert data2["success"] is False
        assert data2["error"] == ErrorCode.ON_COOLDOWN
        mock.set_default_cooldown(0.0)
        sock.close()

    def test_chickens_bypass_cooldown(self, mock):
        mock.set_default_cooldown(60.0)
        sock, _ = _auth_handshake(mock.port)
        for i in range(5):
            msg = json.dumps({"action": "chickens", "protocol_version": 1, "message_id": f"ch-{i}"})
            sock.sendall((msg + "\n").encode("utf-8"))
            resp = sock.recv(4096).decode("utf-8").strip()
            data = json.loads(resp)
            assert data["success"] is True, f"Chickens attempt {i} failed"
        mock.set_default_cooldown(0.0)
        sock.close()

    def test_different_actions_independent_cooldown(self, mock):
        mock.set_cooldown("zombie", 10.0)
        mock.set_cooldown("spiders", 0.0)
        sock, _ = _auth_handshake(mock.port)

        msg1 = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "ind-1"})
        sock.sendall((msg1 + "\n").encode("utf-8"))
        resp1 = sock.recv(4096).decode("utf-8").strip()
        assert json.loads(resp1)["success"] is True

        msg2 = json.dumps({"action": "spiders", "protocol_version": 1, "message_id": "ind-2"})
        sock.sendall((msg2 + "\n").encode("utf-8"))
        resp2 = sock.recv(4096).decode("utf-8").strip()
        assert json.loads(resp2)["success"] is True

        msg3 = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "ind-3"})
        sock.sendall((msg3 + "\n").encode("utf-8"))
        resp3 = sock.recv(4096).decode("utf-8").strip()
        assert json.loads(resp3)["success"] is False

        mock.set_cooldown("zombie", 0.0)
        sock.close()


class TestCoreMockControlledResponses:
    def test_custom_success_response(self, mock):
        mock.set_action_response("zombie", success=True, message="Custom zombie message")
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "ctrl-1"})
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(resp)
        assert data["success"] is True
        assert data["message"] == "Custom zombie message"
        sock.close()

    def test_custom_error_response(self, mock):
        mock.set_action_response("creeper", success=False, error=ErrorCode.EXECUTION_ERROR, message="Creeper exploded too early")
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "creeper", "protocol_version": 1, "message_id": "ctrl-2"})
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(resp)
        assert data["success"] is False
        assert data["error"] == ErrorCode.EXECUTION_ERROR
        assert data["message"] == "Creeper exploded too early"
        sock.close()


class TestCoreMockTCP:
    def test_empty_line_ignored(self, mock):
        sock, _ = _auth_handshake(mock.port)
        sock.sendall(b"\n")
        msg = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "tcp-1"})
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(resp)
        assert data["success"] is True
        sock.close()

    def test_multiple_requests_same_connection(self, mock):
        sock, _ = _auth_handshake(mock.port)
        for i in range(5):
            msg = json.dumps({"action": "chickens", "protocol_version": 1, "message_id": f"multi-{i}"})
            sock.sendall((msg + "\n").encode("utf-8"))
            resp = sock.recv(4096).decode("utf-8").strip()
            data = json.loads(resp)
            assert data["success"] is True
        sock.close()

    def test_connection_close_detected(self, mock):
        sock, _ = _auth_handshake(mock.port)
        sock.close()
        time.sleep(0.2)
        assert mock.get_client_count() == 0


class TestCoreMockReceivedRequests:
    def test_requests_recorded(self, mock):
        mock.clear_received_requests()
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "rec-1"})
        sock.sendall((msg + "\n").encode("utf-8"))
        sock.recv(4096)
        time.sleep(0.1)
        requests = mock.get_received_requests()
        assert len(requests) == 1
        assert requests[0]["action"] == "zombie"
        sock.close()

    def test_clear_requests(self, mock):
        mock.clear_received_requests()
        assert len(mock.get_received_requests()) == 0


# ─── Bridge Integration Tests ────────────────────────────────────────────────


class TestBridgeIntegration:
    def test_connect_auth_send(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        assert client.connected
        result = client.authenticate()
        assert result is True
        assert client.authenticated

        request = BridgeRequest(action="zombie", target="Streamer", source="twitch", user="TestUser")
        response = client.send_and_wait(request)
        assert response.success is True
        assert response.action == "zombie"
        client.disconnect()

    def test_auth_wrong_token_fails(self, mock_port):
        m = CoreMock(port=mock_port + 20, auth_token="REAL_SECRET")
        m.start()
        time.sleep(0.1)
        try:
            config = Config({
                "minecraft": {"host": "127.0.0.1", "port": mock_port + 20, "auth_token": "WRONG"},
                "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
                "commands": {"prefix": "!", "cooldowns": {}},
            })
            client = MinecraftClient(config)
            client.connect()
            result = client.authenticate()
            assert result is False
            assert client.authenticated is False
            client.disconnect()
        finally:
            m.stop()

    def test_send_before_auth_rejected(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        request = BridgeRequest(action="zombie", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is False
        assert response.error == "NOT_AUTHENTICATED"
        client.disconnect()

    def test_disconnect_clears_auth(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        assert client.authenticated
        client.disconnect()
        assert not client.authenticated
        assert not client.connected


# ─── Event Numbers 1-10 Integration ──────────────────────────────────────────


EVENT_MAP = {
    "1": "zombie", "2": "spiders", "3": "slowness", "4": "blindness",
    "5": "creeper", "6": "storm", "7": "random_teleport", "8": "explosion",
    "9": "random_event", "10": "chickens",
}


class TestEventNumbersIntegration:
    @pytest.mark.parametrize("number,expected_action", list(EVENT_MAP.items()))
    def test_event_number_full_flow(self, mock, config, number, expected_action):
        from chat.command_parser import CommandParser
        from cooldowns.manager import CooldownManager
        from platforms.pipeline import ChatPipeline
        from platforms.models import ChatMessage

        parser = CommandParser(prefix="!", event_number_map=EVENT_MAP)
        cooldowns = CooldownManager({a: 0 for a in EVENT_MAP.values()})
        pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")

        msg = ChatMessage(
            platform="twitch", user_id="100", username="viewer",
            display_name="Viewer", message_id=f"ev-{number}",
            message_text=number, channel_id="ch", channel_name="Ch",
        )
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == expected_action

        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        response = client.send_and_wait(request)
        assert response.success is True
        assert response.action == expected_action
        client.disconnect()

    def test_all_ten_events_rapid(self, mock, config):
        from chat.command_parser import CommandParser
        from cooldowns.manager import CooldownManager
        from platforms.pipeline import ChatPipeline
        from platforms.models import ChatMessage

        parser = CommandParser(prefix="!", event_number_map=EVENT_MAP)
        cooldowns = CooldownManager({a: 0 for a in EVENT_MAP.values()})
        pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")

        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        for number, expected_action in EVENT_MAP.items():
            msg = ChatMessage(
                platform="twitch", user_id="100", username="viewer",
                display_name="Viewer", message_id=f"rapid-{number}",
                message_text=number, channel_id="ch", channel_name="Ch",
            )
            request = pipeline.process(msg)
            assert request is not None
            assert request.action == expected_action
            response = client.send_and_wait(request)
            assert response.success is True

        client.disconnect()


# ─── Chickens Rapid Fire ─────────────────────────────────────────────────────


class TestChickensRapid:
    def test_chickens_no_cooldown(self, mock, config):
        from chat.command_parser import CommandParser
        from cooldowns.manager import CooldownManager
        from platforms.pipeline import ChatPipeline
        from platforms.models import ChatMessage

        parser = CommandParser(prefix="!", event_number_map=EVENT_MAP)
        cooldowns = CooldownManager({a: 10 for a in EVENT_MAP.values()})
        cooldowns.set_cooldown("chickens", 0)
        pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")

        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        for i in range(5):
            msg = ChatMessage(
                platform="twitch", user_id="100", username="viewer",
                display_name="Viewer", message_id=f"chick-{i}",
                message_text="10", channel_id="ch", channel_name="Ch",
            )
            request = pipeline.process(msg)
            assert request is not None
            assert request.action == "chickens"
            response = client.send_and_wait(request)
            assert response.success is True

        client.disconnect()


# ─── Reconnection ────────────────────────────────────────────────────────────


class TestReconnection:
    def test_reconnect_after_server_restart(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        assert client.authenticated

        request = BridgeRequest(action="zombie", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is True

        mock.stop()
        time.sleep(0.3)

        mock.start()
        time.sleep(0.2)

        client.disconnect()
        client.connect()
        result = client.authenticate()
        assert result is True

        request2 = BridgeRequest(action="spiders", target="Streamer")
        response2 = client.send_and_wait(request2)
        assert response2.success is True
        client.disconnect()


# ─── Multiple Users ──────────────────────────────────────────────────────────


class TestMultipleUsers:
    def test_different_users_same_action(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        for user in ["Alice", "Bob", "Charlie"]:
            request = BridgeRequest(action="zombie", target="Streamer", source="twitch", user=user)
            response = client.send_and_wait(request)
            assert response.success is True

        client.disconnect()


# ─── Security ────────────────────────────────────────────────────────────────


class TestSecurity:
    def test_token_not_in_response(self, mock):
        sock, _ = _auth_handshake(mock.port, "TEST_TOKEN")
        msg = json.dumps({"action": "zombie", "protocol_version": 1, "message_id": "sec-1"})
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        assert "TEST_TOKEN" not in resp
        assert "token" not in resp.lower() or "auth_token" not in resp
        sock.close()

    def test_invalid_action_params(self, mock):
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({
            "action": "zombie", "target": "Streamer",
            "params": {"radius": -999}, "protocol_version": 1, "message_id": "sec-2"
        })
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(resp)
        assert data["success"] is True
        sock.close()

    def test_action_before_auth(self, mock):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", mock.port))
        msg = json.dumps({"action": "zombie", "protocol_version": 1})
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(resp)
        assert data["success"] is False
        assert data["error"] in (ErrorCode.UNAUTHORIZED, ErrorCode.INVALID_PROTOCOL)
        sock.close()


# ─── CoreMock Configurable ───────────────────────────────────────────────────


class TestCoreMockConfigurable:
    def test_custom_host_port(self, mock_port):
        m = CoreMock(host="127.0.0.1", port=mock_port + 30)
        assert m.host == "127.0.0.1"
        assert m.port == mock_port + 30

    def test_set_action_response(self, mock):
        mock.set_action_response("storm", success=False, error=ErrorCode.ACTION_DISABLED, message="Storm disabled")
        sock, _ = _auth_handshake(mock.port)
        msg = json.dumps({"action": "storm", "protocol_version": 1, "message_id": "cfg-1"})
        sock.sendall((msg + "\n").encode("utf-8"))
        resp = sock.recv(4096).decode("utf-8").strip()
        data = json.loads(resp)
        assert data["success"] is False
        assert data["error"] == ErrorCode.ACTION_DISABLED
        sock.close()
