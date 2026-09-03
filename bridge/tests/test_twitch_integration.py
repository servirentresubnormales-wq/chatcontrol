"""Twitch Integration Mock Tests — Full flow simulation.

Tests the complete Twitch → Bridge → Minecraft pipeline using mocks.
No real Twitch or Minecraft connections needed.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from platforms.models import ChatMessage
from platforms.pipeline import ChatPipeline
from chat.command_parser import CommandParser
from cooldowns.manager import CooldownManager
from minecraft.command_builder import build_action
from integrations.twitch.config import TwitchConfig
from integrations.twitch.auth import TwitchAuth, TokenInfo
from integrations.twitch.event_handler import TwitchEventHandler, MessageDeduplicator
from integrations.twitch.client import TwitchWSClient
from integrations.twitch.platform import TwitchPlatform


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_event(
    message_id: str = "msg-001",
    text: str = "!zombie",
    chatter_id: str = "456789",
    chatter_name: str = "Viewer123",
    chatter_login: str = "viewer123",
    broadcaster_id: str = "12826",
    broadcaster_name: str = "StreamChannel",
    badges: list | None = None,
) -> dict:
    return {
        "broadcaster_user_id": broadcaster_id,
        "broadcaster_user_name": broadcaster_name,
        "broadcaster_user_login": broadcaster_name.lower(),
        "chatter_user_id": chatter_id,
        "chatter_user_name": chatter_name,
        "chatter_user_login": chatter_login,
        "message_id": message_id,
        "message": {
            "text": text,
            "fragments": [{"type": "text", "text": text, "cheermote": None, "emote": None, "mention": None}],
        },
        "color": "#00FF7F",
        "badges": badges or [],
        "message_type": "text",
        "cheer": None,
        "reply": None,
        "channel_points_custom_reward_id": None,
        "source_broadcaster_user_id": None,
        "source_broadcaster_user_login": None,
    }


SAMPLE_WELCOME = {
    "metadata": {"message_id": "welcome-001", "message_type": "session_welcome", "message_timestamp": "2024-01-01T00:00:00Z"},
    "payload": {
        "session": {
            "id": "session-abc-123",
            "status": "connected",
            "keepalive_timeout_seconds": 30,
            "reconnect_url": None,
            "connected_at": "2024-01-01T00:00:00Z",
        }
    },
}

SAMPLE_KEEPALIVE = {
    "metadata": {"message_id": "keepalive-001", "message_type": "session_keepalive", "message_timestamp": "2024-01-01T00:01:00Z"},
    "payload": {},
}

SAMPLE_RECONNECT = {
    "metadata": {"message_id": "reconnect-001", "message_type": "session_reconnect", "message_timestamp": "2024-01-01T00:02:00Z"},
    "payload": {
        "session": {
            "id": "session-new-456",
            "status": "reconnecting",
            "keepalive_timeout_seconds": None,
            "reconnect_url": "wss://eventsub.wss.twitch.tv/ws?session=session-new-456",
            "connected_at": "2024-01-01T00:00:00Z",
        }
    },
}

SAMPLE_NOTIFICATION = {
    "metadata": {
        "message_id": "notif-001",
        "message_type": "notification",
        "message_timestamp": "2024-01-01T00:03:00Z",
        "subscription_type": "channel.chat.message",
        "subscription_version": "1",
    },
    "payload": {
        "subscription": {
            "id": "sub-001",
            "status": "enabled",
            "type": "channel.chat.message",
            "version": "1",
            "cost": 0,
            "condition": {"broadcaster_user_id": "12826", "user_id": "12826"},
            "transport": {"method": "websocket", "session_id": "session-abc-123"},
            "created_at": "2024-01-01T00:00:00Z",
        },
        "event": _make_event(),
    },
}

SAMPLE_REVOCATION = {
    "metadata": {"message_id": "revoke-001", "message_type": "revocation", "message_timestamp": "2024-01-01T00:04:00Z", "subscription_type": "channel.chat.message", "subscription_version": "1"},
    "payload": {
        "subscription": {
            "id": "sub-001",
            "status": "authorization_revoked",
            "type": "channel.chat.message",
            "version": "1",
            "cost": 0,
            "condition": {},
            "transport": {"method": "websocket", "session_id": "session-abc-123"},
            "created_at": "2024-01-01T00:00:00Z",
        }
    },
}


def _make_pipeline(prefix="!", cooldowns_dict=None):
    parser = CommandParser(prefix=prefix)
    cooldowns = CooldownManager(cooldowns_dict or {"zombie": 10, "spiders": 10, "creeper": 30, "storm": 60, "chickens": 0})
    return ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")


def _make_platform(enabled=True, client_id="test_client", access_token="test_token", broadcaster_id="12826", channel="StreamChannel"):
    config = TwitchConfig(
        enabled=enabled,
        client_id=client_id,
        access_token=access_token,
        broadcaster_id=broadcaster_id,
        channel=channel,
    )
    return TwitchPlatform(config)


# ─── Integration: Full Flow ──────────────────────────────────────────────────


class TestFullFlow:
    """Test complete: Twitch Event → ChatMessage → Pipeline → BridgeRequest."""

    def test_zombie_command_full_flow(self):
        pipeline = _make_pipeline()
        event = _make_event(text="!zombie", chatter_name="Viewer123")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None
        assert chat_msg.platform == "twitch"
        assert chat_msg.message_text == "!zombie"
        assert chat_msg.display_name == "Viewer123"

        request = pipeline.process(chat_msg)
        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"
        assert request.user == "Viewer123"

    def test_chickens_command_full_flow(self):
        pipeline = _make_pipeline()
        event = _make_event(text="!pollos", message_id="msg-chickens-001")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is not None
        assert request.action == "chickens"

    def test_creeper_command_full_flow(self):
        pipeline = _make_pipeline()
        event = _make_event(text="!creeper", message_id="msg-creeper-001")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is not None
        assert request.action == "creeper"

    def test_slowness_with_params_full_flow(self):
        pipeline = _make_pipeline()
        event = _make_event(text="!slowness 30 2", message_id="msg-slow-001")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is not None
        assert request.action == "slowness"
        assert request.params["duration"] == 30
        assert request.params["amplifier"] == 2

    def test_normal_text_ignored(self):
        pipeline = _make_pipeline()
        event = _make_event(text="hola chat", message_id="msg-hello-001")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is None

    def test_unknown_command_ignored(self):
        pipeline = _make_pipeline()
        event = _make_event(text="!unknown", message_id="msg-unknown-001")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is None


# ─── Integration: Minecraft Mock ────────────────────────────────────────────


class TestMinecraftMock:
    """Test that MinecraftClient mock receives correct requests."""

    def test_mock_client_receives_request(self):
        pipeline = _make_pipeline()
        mc_client = MagicMock()
        mc_client.connected = True
        mc_client.send_and_wait.return_value = MagicMock(success=True, message="OK")

        from main import _process_chat_message
        event = _make_event(text="!zombie")
        handler = TwitchEventHandler()
        chat_msg = handler.handle_notification("channel.chat.message", event)

        _process_chat_message(chat_msg, pipeline, mc_client)
        mc_client.send_and_wait.assert_called_once()

        sent_request = mc_client.send_and_wait.call_args[0][0]
        assert sent_request.action == "zombie"
        assert sent_request.source == "twitch"
        assert sent_request.user == "Viewer123"
        assert sent_request.target == "Streamer"

    def test_mock_client_not_called_on_invalid_command(self):
        pipeline = _make_pipeline()
        mc_client = MagicMock()
        mc_client.connected = True

        from main import _process_chat_message
        event = _make_event(text="!invalid", message_id="msg-invalid-001")
        handler = TwitchEventHandler()
        chat_msg = handler.handle_notification("channel.chat.message", event)

        _process_chat_message(chat_msg, pipeline, mc_client)
        mc_client.send_and_wait.assert_not_called()

    def test_mock_client_not_called_on_cooldown(self):
        pipeline = _make_pipeline()
        mc_client = MagicMock()
        mc_client.connected = True

        from main import _process_chat_message
        event1 = _make_event(text="!zombie", message_id="msg-cool-001")
        handler = TwitchEventHandler()
        chat_msg1 = handler.handle_notification("channel.chat.message", event1)
        _process_chat_message(chat_msg1, pipeline, mc_client)

        event2 = _make_event(text="!zombie", message_id="msg-cool-002")
        chat_msg2 = handler.handle_notification("channel.chat.message", event2)
        _process_chat_message(chat_msg2, pipeline, mc_client)

        assert mc_client.send_and_wait.call_count == 1


# ─── Deduplication ───────────────────────────────────────────────────────────


class TestDeduplication:
    def test_same_message_id_processed_once(self):
        handler = TwitchEventHandler()
        event = _make_event(message_id="msg-dedup-001")

        msg1 = handler.handle_notification("channel.chat.message", event)
        msg2 = handler.handle_notification("channel.chat.message", event)

        assert msg1 is not None
        assert msg2 is None

    def test_different_ids_both_processed(self):
        handler = TwitchEventHandler()

        msg1 = handler.handle_notification("channel.chat.message", _make_event(message_id="msg-a"))
        msg2 = handler.handle_notification("channel.chat.message", _make_event(message_id="msg-b"))

        assert msg1 is not None
        assert msg2 is not None


# ─── Cooldown ────────────────────────────────────────────────────────────────


class TestCooldown:
    def test_zombie_cooldown_blocks_second(self):
        pipeline = _make_pipeline()
        handler = TwitchEventHandler()

        msg1 = handler.handle_notification("channel.chat.message", _make_event(text="!zombie", message_id="msg-cd-001"))
        req1 = pipeline.process(msg1)
        assert req1 is not None

        msg2 = handler.handle_notification("channel.chat.message", _make_event(text="!zombie", message_id="msg-cd-002"))
        req2 = pipeline.process(msg2)
        assert req2 is None

    def test_chickens_no_cooldown(self):
        pipeline = _make_pipeline()
        handler = TwitchEventHandler()

        msg1 = handler.handle_notification("channel.chat.message", _make_event(text="!pollos", message_id="msg-chk-001"))
        req1 = pipeline.process(msg1)
        assert req1 is not None
        assert req1.action == "chickens"

        msg2 = handler.handle_notification("channel.chat.message", _make_event(text="!pollos", message_id="msg-chk-002"))
        req2 = pipeline.process(msg2)
        assert req2 is not None

        msg3 = handler.handle_notification("channel.chat.message", _make_event(text="!pollos", message_id="msg-chk-003"))
        req3 = pipeline.process(msg3)
        assert req3 is not None

    def test_different_actions_independent(self):
        pipeline = _make_pipeline()
        handler = TwitchEventHandler()

        msg1 = handler.handle_notification("channel.chat.message", _make_event(text="!zombie", message_id="msg-idx-001"))
        req1 = pipeline.process(msg1)
        assert req1 is not None

        msg2 = handler.handle_notification("channel.chat.message", _make_event(text="!creeper", message_id="msg-idx-002"))
        req2 = pipeline.process(msg2)
        assert req2 is not None


# ─── Multi-User Cooldown ────────────────────────────────────────────────────


class TestMultiUserCooldown:
    def test_different_users_independent(self):
        pipeline = _make_pipeline()
        handler = TwitchEventHandler()

        msg_a = handler.handle_notification("channel.chat.message", _make_event(
            text="!zombie", message_id="msg-ua-001", chatter_id="111", chatter_name="UserA", chatter_login="usera"
        ))
        req_a = pipeline.process(msg_a)
        assert req_a is not None

        msg_b = handler.handle_notification("channel.chat.message", _make_event(
            text="!zombie", message_id="msg-ub-001", chatter_id="222", chatter_name="UserB", chatter_login="userb"
        ))
        req_b = pipeline.process(msg_b)
        assert req_b is not None

    def test_same_user_cooldown(self):
        pipeline = _make_pipeline()
        handler = TwitchEventHandler()

        msg1 = handler.handle_notification("channel.chat.message", _make_event(
            text="!zombie", message_id="msg-same-001", chatter_id="111", chatter_name="UserA", chatter_login="usera"
        ))
        req1 = pipeline.process(msg1)
        assert req1 is not None

        msg2 = handler.handle_notification("channel.chat.message", _make_event(
            text="!zombie", message_id="msg-same-002", chatter_id="111", chatter_name="UserA", chatter_login="usera"
        ))
        req2 = pipeline.process(msg2)
        assert req2 is None


# ─── EventSub Mock Events ───────────────────────────────────────────────────


class TestEventSubEvents:
    def test_welcome_accepted(self):
        ws_client = MagicMock()
        ws_client._session_id = None
        ws_client._subscription_created = False
        ws_client._reconnecting = False
        ws_client._old_ws = None
        ws_client._config = MagicMock()
        ws_client._config.keepalive_timeout = 30

        TwitchWSClient._handle_welcome(ws_client, SAMPLE_WELCOME)
        assert ws_client._session_id == "session-abc-123"

    def test_keepalive_accepted(self):
        ws_client = MagicMock()
        ws_client._last_message_time = 0
        ws_client._on_message(ws_client, json.dumps(SAMPLE_KEEPALIVE))

    def test_notification_accepted(self):
        ws_client = MagicMock()
        ws_client._last_message_time = 0
        ws_client._event_handler = TwitchEventHandler()
        ws_client._on_chat_message = MagicMock()
        ws_client._handle_notification = lambda data: TwitchWSClient._handle_notification(ws_client, data)

        TwitchWSClient._on_message(ws_client, None, json.dumps(SAMPLE_NOTIFICATION))
        ws_client._on_chat_message.assert_called_once()

    def test_revocation_accepted(self):
        ws_client = MagicMock()
        ws_client._last_message_time = 0
        ws_client._on_message(ws_client, json.dumps(SAMPLE_REVOCATION))

    def test_unknown_event_ignored(self):
        ws_client = MagicMock()
        ws_client._last_message_time = 0
        unknown = {
            "metadata": {"message_id": "x", "message_type": "unknown_type", "message_timestamp": "2024-01-01T00:00:00Z"},
            "payload": {},
        }
        ws_client._on_message(ws_client, json.dumps(unknown))

    def test_incomplete_payload_no_crash(self):
        handler = TwitchEventHandler()
        msg = handler.handle_notification("channel.chat.message", {})
        assert msg is None

    def test_invalid_json_no_crash(self):
        ws_client = MagicMock()
        ws_client._last_message_time = 0
        ws_client._on_message(ws_client, "not valid json {{{")


# ─── Reconnect ───────────────────────────────────────────────────────────────


class TestReconnect:
    def test_reconnect_does_not_close_old_immediately(self):
        ws_client = MagicMock()
        ws_client._reconnect_url = None
        ws_client._session_id = "session-old"
        ws_client._reconnecting = False
        ws_client._old_ws = None
        ws_client._ws = MagicMock()
        ws_client._config = TwitchConfig(websocket_url="wss://test")
        ws_client._on_message = MagicMock()
        ws_client._on_error = MagicMock()
        ws_client._on_close = MagicMock()
        ws_client._on_open = MagicMock()

        with patch("integrations.twitch.client.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            TwitchWSClient._handle_reconnect(ws_client, SAMPLE_RECONNECT)

        assert ws_client._reconnect_url is not None
        assert ws_client._reconnecting is True
        assert ws_client._old_ws is not None

    def test_welcome_on_new_connection_closes_old(self):
        ws_client = MagicMock()
        ws_client._reconnecting = True
        old_ws_mock = MagicMock()
        ws_client._old_ws = old_ws_mock
        ws_client._session_id = "session-new-456"
        ws_client._subscription_created = True
        ws_client._config = MagicMock()
        ws_client._config.keepalive_timeout = 30

        welcome_new = {
            "metadata": {"message_id": "w2", "message_type": "session_welcome", "message_timestamp": "2024-01-01T00:00:00Z"},
            "payload": {
                "session": {
                    "id": "session-new-456",
                    "status": "connected",
                    "keepalive_timeout_seconds": 30,
                    "reconnect_url": None,
                    "connected_at": "2024-01-01T00:00:00Z",
                }
            },
        }

        TwitchWSClient._handle_welcome(ws_client, welcome_new)
        old_ws_mock.close.assert_called_once()
        assert ws_client._reconnecting is False


# ─── Error Handling ──────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_invalid_token_config(self):
        config = TwitchConfig(enabled=True, client_id="", access_token="", broadcaster_id="", channel="")
        errors = config.validate()
        assert len(errors) >= 3

    def test_token_validation_failure(self):
        config = TwitchConfig(enabled=True, client_id="id", access_token="bad", broadcaster_id="123", channel="test")
        auth = TwitchAuth(config)
        result = auth.validate_token()
        assert result.valid is False

    def test_event_with_missing_message(self):
        handler = TwitchEventHandler()
        event = {"chatter_user_id": "123", "message_id": "msg-err-001"}
        msg = handler.handle_notification("channel.chat.message", event)
        assert msg is None

    def test_event_with_empty_message(self):
        handler = TwitchEventHandler()
        event = _make_event(text="", message_id="msg-empty-001")
        msg = handler.handle_notification("channel.chat.message", event)
        assert msg is None

    def test_minecraft_client_not_connected(self):
        from main import _process_chat_message
        pipeline = _make_pipeline()
        mc_client = MagicMock()
        mc_client.connected = False

        event = _make_event(text="!zombie")
        handler = TwitchEventHandler()
        chat_msg = handler.handle_notification("channel.chat.message", event)

        _process_chat_message(chat_msg, pipeline, mc_client, None)
        mc_client.send_and_wait.assert_not_called()

    def test_queue_full_drops_action(self):
        from main import _process_chat_message, ACTION_QUEUE_MAX_SIZE
        pipeline = _make_pipeline()
        action_queue = queue.Queue(maxsize=ACTION_QUEUE_MAX_SIZE)
        for _ in range(ACTION_QUEUE_MAX_SIZE):
            action_queue.put_nowait("x")

        event = _make_event(text="!zombie", message_id="msg-qfull-001")
        handler = TwitchEventHandler()
        chat_msg = handler.handle_notification("channel.chat.message", event)
        _process_chat_message(chat_msg, pipeline, None, action_queue)

    def test_non_chat_event_ignored(self):
        handler = TwitchEventHandler()
        msg = handler.handle_notification("channel.follow", {})
        assert msg is None


# ─── Load Test ───────────────────────────────────────────────────────────────


class TestLoadSimulation:
    def test_many_messages_processed(self):
        handler = TwitchEventHandler()
        pipeline = _make_pipeline()
        processed = 0

        for i in range(200):
            event = _make_event(text="!zombie", message_id=f"msg-load-{i:04d}", chatter_id=str(i % 5))
            msg = handler.handle_notification("channel.chat.message", event)
            if msg:
                req = pipeline.process(msg)
                if req:
                    processed += 1

        assert processed > 0
        assert processed < 200

    def test_memory_does_not_grow_unbounded(self):
        dedup = MessageDeduplicator(max_size=100)
        for i in range(500):
            dedup.is_duplicate(f"msg-{i:04d}")
        assert len(dedup._messages) <= 101

    def test_concurrent_dedup_no_duplicates(self):
        dedup = MessageDeduplicator()
        seen = []
        lock = threading.Lock()

        def check(msg_id):
            result = dedup.is_duplicate(msg_id)
            with lock:
                seen.append((msg_id, result))

        threads = [threading.Thread(target=check, args=(f"msg-{i}",)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(not r for _, r in seen)


# ─── Security ────────────────────────────────────────────────────────────────


class TestSecurity:
    def test_token_never_in_logs(self):
        config = TwitchConfig(enabled=True, client_id="cid", access_token="secret_token_abc123", broadcaster_id="123", channel="test")
        auth = TwitchAuth(config)
        diag = auth.get_diagnostics()
        assert "secret_token_abc123" not in str(diag)
        assert diag["token_prefix"] == "secret_t..."

    def test_validate_token_error_no_secret(self):
        config = TwitchConfig(enabled=True, client_id="cid", access_token="bad_token", broadcaster_id="123", channel="test")
        auth = TwitchAuth(config)
        result = auth.validate_token()
        assert "bad_token" not in result.error

    def test_config_validate_no_secrets_in_errors(self):
        config = TwitchConfig(enabled=True, client_id="cid", access_token="my_secret", broadcaster_id="123", channel="test")
        errors = config.validate()
        for err in errors:
            assert "my_secret" not in err


# ─── Diagnostic Mode ─────────────────────────────────────────────────────────


class TestDiagnosticMode:
    def test_check_twitch_disabled(self):
        from main import run_check_twitch
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            config_data = {"twitch": {"enabled": False}}
            with patch("main.load_config") as mock_load:
                mock_config = MagicMock()
                mock_config._data = config_data
                mock_load.return_value = mock_config
                run_check_twitch(None)
        finally:
            sys.stdout = old_stdout

        output = buffer.getvalue()
        assert "DISABLED" in output or "disabled" in output

    def test_check_twitch_missing_fields(self):
        from main import run_check_twitch
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            config_data = {"twitch": {"enabled": True, "client_id": "", "access_token": "", "broadcaster_id": "", "channel": ""}}
            with patch("main.load_config") as mock_load:
                mock_config = MagicMock()
                mock_config._data = config_data
                mock_load.return_value = mock_config
                run_check_twitch(None)
        finally:
            sys.stdout = old_stdout

        output = buffer.getvalue()
        assert "FAIL" in output or "errors" in output


# ─── Integration: Event Numbers ──────────────────────────────────────────────


class TestEventNumberIntegration:
    """Test complete flow: Twitch Event → ChatMessage → "1" → ParsedCommand → action → BridgeRequest."""

    @pytest.mark.parametrize("number,expected_action", [
        ("1", "zombie"),
        ("2", "spiders"),
        ("3", "slowness"),
        ("4", "blindness"),
        ("5", "creeper"),
        ("6", "storm"),
        ("7", "random_teleport"),
        ("8", "explosion"),
        ("9", "random_event"),
        ("10", "chickens"),
    ])
    def test_event_number_full_flow(self, number, expected_action):
        pipeline = _make_pipeline()
        event = _make_event(text=number, chatter_name="Viewer123")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is not None
        assert request.action == expected_action
        assert request.user == "Viewer123"
        assert request.target == "Streamer"
        assert request.source == "twitch"

    @pytest.mark.parametrize("number,expected_action", [
        ("1", "zombie"),
        ("5", "creeper"),
        ("10", "chickens"),
    ])
    def test_event_number_with_spaces(self, number, expected_action):
        pipeline = _make_pipeline()
        event = _make_event(text=f"  {number}  ", chatter_name="Viewer123")
        handler = TwitchEventHandler()

        chat_msg = handler.handle_notification("channel.chat.message", event)
        assert chat_msg is not None

        request = pipeline.process(chat_msg)
        assert request is not None
        assert request.action == expected_action

    def test_event_number_10_chickens_bypasses_cooldown(self):
        pipeline = _make_pipeline(cooldowns_dict={"zombie": 10, "chickens": 0})

        event1 = _make_event(text="10", message_id="msg-a", chatter_name="Viewer123")
        handler = TwitchEventHandler()
        chat_msg1 = handler.handle_notification("channel.chat.message", event1)
        request1 = pipeline.process(chat_msg1)
        assert request1 is not None
        assert request1.action == "chickens"

        event2 = _make_event(text="10", message_id="msg-b", chatter_name="Viewer123")
        chat_msg2 = handler.handle_notification("channel.chat.message", event2)
        request2 = pipeline.process(chat_msg2)
        assert request2 is not None
        assert request2.action == "chickens"

    def test_event_number_receives_correct_minecraft_request(self):
        pipeline = _make_pipeline()
        mc_client = MagicMock()
        mc_client.connected = True
        mc_client.send_and_wait.return_value = MagicMock(success=True, message="OK")

        event = _make_event(text="5", chatter_name="CreeperFan")
        handler = TwitchEventHandler()
        chat_msg = handler.handle_notification("channel.chat.message", event)

        from main import _process_chat_message
        _process_chat_message(chat_msg, pipeline, mc_client)

        mc_client.send_and_wait.assert_called_once()
        request = mc_client.send_and_wait.call_args[0][0]
        assert request.action == "creeper"
        assert request.user == "CreeperFan"
        assert request.source == "twitch"


class TestEventNumberCooldown:
    """Test cooldown behavior with event numbers."""

    def test_event_number_respects_cooldown(self):
        pipeline = _make_pipeline(cooldowns_dict={"zombie": 10})

        event1 = _make_event(text="1", message_id="msg-1", chatter_name="ViewerA")
        handler = TwitchEventHandler()
        chat_msg1 = handler.handle_notification("channel.chat.message", event1)
        request1 = pipeline.process(chat_msg1)
        assert request1 is not None
        assert request1.action == "zombie"

        event2 = _make_event(text="1", message_id="msg-2", chatter_name="ViewerA")
        chat_msg2 = handler.handle_notification("channel.chat.message", event2)
        request2 = pipeline.process(chat_msg2)
        assert request2 is None

    def test_different_users_independent_cooldowns(self):
        pipeline = _make_pipeline(cooldowns_dict={"zombie": 10})

        event1 = _make_event(text="1", message_id="msg-1", chatter_name="ViewerA", chatter_login="viewera")
        handler = TwitchEventHandler()
        chat_msg1 = handler.handle_notification("channel.chat.message", event1)
        request1 = pipeline.process(chat_msg1)
        assert request1 is not None

        event2 = _make_event(text="1", message_id="msg-2", chatter_name="ViewerB", chatter_login="viewerb")
        chat_msg2 = handler.handle_notification("channel.chat.message", event2)
        request2 = pipeline.process(chat_msg2)
        assert request2 is not None

    def test_chickens_number_10_no_cooldown(self):
        pipeline = _make_pipeline(cooldowns_dict={"chickens": 0})

        for i in range(5):
            event = _make_event(text="10", message_id=f"msg-{i}", chatter_name="ViewerA")
            handler = TwitchEventHandler()
            chat_msg = handler.handle_notification("channel.chat.message", event)
            request = pipeline.process(chat_msg)
            assert request is not None
            assert request.action == "chickens"

    def test_mixed_prefix_and_number_commands(self):
        pipeline = _make_pipeline(cooldowns_dict={"zombie": 10, "creeper": 30})

        event1 = _make_event(text="!zombie", message_id="msg-1", chatter_name="ViewerA")
        handler = TwitchEventHandler()
        chat_msg1 = handler.handle_notification("channel.chat.message", event1)
        request1 = pipeline.process(chat_msg1)
        assert request1 is not None
        assert request1.action == "zombie"

        event2 = _make_event(text="5", message_id="msg-2", chatter_name="ViewerA")
        chat_msg2 = handler.handle_notification("channel.chat.message", event2)
        request2 = pipeline.process(chat_msg2)
        assert request2 is not None
        assert request2.action == "creeper"
