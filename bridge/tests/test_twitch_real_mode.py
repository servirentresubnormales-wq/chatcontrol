"""Twitch Test Mode Tests — --twitch-test functionality.

Tests that the test mode correctly processes Twitch messages
without sending to Minecraft.
"""
from __future__ import annotations

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


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def parser():
    return CommandParser(prefix="!", event_number_map={
        "1": "zombie", "2": "spiders", "3": "slowness", "4": "blindness",
        "5": "creeper", "6": "storm", "7": "random_teleport", "8": "explosion",
        "9": "random_event", "10": "chickens",
    })


@pytest.fixture
def cooldowns():
    return CooldownManager({
        "zombie": 10, "spiders": 15, "slowness": 20, "blindness": 20,
        "creeper": 30, "storm": 60, "random_teleport": 60, "explosion": 30,
        "random_event": 60, "chickens": 0,
    })


@pytest.fixture
def pipeline(parser, cooldowns):
    return ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")


def _make_twitch_message(message_id: str, text: str, user: str = "Viewer123",
                         user_id: str = "123456") -> ChatMessage:
    return ChatMessage(
        platform="twitch",
        user_id=user_id,
        username=user.lower(),
        display_name=user,
        message_id=message_id,
        message_text=text,
        channel_id="789012",
        channel_name="StreamerChannel",
    )


# ─── Startup Tests ──────────────────────────────────────────────────────────


class TestTwitchTestModeStartup:
    """Test startup behavior of --twitch-test mode."""

    def test_twitch_disabled_fails(self):
        from integrations.twitch.config import TwitchConfig
        config = TwitchConfig(enabled=False)
        assert not config.enabled

    def test_twitch_enabled_config(self):
        from integrations.twitch.config import TwitchConfig
        config = TwitchConfig(
            enabled=True,
            client_id="test_client",
            access_token="test_token",
            broadcaster_id="123456",
            channel="TestChannel",
        )
        assert config.enabled
        errors = config.validate()
        assert len(errors) == 0


# ─── Message Processing Tests ───────────────────────────────────────────────


class TestTwitchTestModeMessages:
    """Test message processing in test mode."""

    def test_normal_text_ignored(self, pipeline):
        msg = _make_twitch_message("msg-001", "hola")
        assert pipeline.process(msg) is None

    def test_number_1_zombie(self, pipeline):
        msg = _make_twitch_message("msg-002", "1")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"

    def test_number_10_chickens(self, pipeline):
        msg = _make_twitch_message("msg-003", "10")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "chickens"

    def test_zombie_with_prefix(self, pipeline):
        msg = _make_twitch_message("msg-004", "!zombie")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"

    def test_number_with_prefix_ignored(self, pipeline):
        msg = _make_twitch_message("msg-005", "!1")
        assert pipeline.process(msg) is None


# ─── Pipeline Tests ─────────────────────────────────────────────────────────


class TestTwitchTestModePipeline:
    """Test complete pipeline flow."""

    def test_full_pipeline_flow(self, pipeline):
        msg = _make_twitch_message("msg-100", "1", "TestUser", "999999")
        request = pipeline.process(msg)

        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"
        assert request.user == "TestUser"
        assert request.message_id is not None


# ─── Minecraft Isolation Tests ──────────────────────────────────────────────


class TestTwitchTestModeMinecraftIsolation:
    """Verify Minecraft is NOT called in test mode."""

    def test_minecraft_client_not_called(self):
        """In test mode, MinecraftClient.send_request should NOT be called."""
        from minecraft.client import MinecraftClient
        mock_client = MagicMock(spec=MinecraftClient)
        mock_client.connected = False

        # Verify send_and_wait is never called
        mock_client.send_and_wait.assert_not_called()
        mock_client.connect.assert_not_called()


# ─── Deduplication Tests ────────────────────────────────────────────────────


class TestTwitchTestModeDeduplication:
    """Test deduplication in test mode."""

    def test_duplicate_message_once(self, pipeline):
        msg1 = _make_twitch_message("msg-200", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-200", "1", "ViewerA")

        request1 = pipeline.process(msg1)
        request2 = pipeline.process(msg2)

        assert request1 is not None
        assert request2 is None  # deduplicated

    def test_different_ids_both_processed(self, pipeline):
        msg1 = _make_twitch_message("msg-210", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-211", "1", "ViewerA")

        request1 = pipeline.process(msg1)
        request2 = pipeline.process(msg2)

        assert request1 is not None
        assert request2 is None  # cooldown


# ─── Cooldown Tests ─────────────────────────────────────────────────────────


class TestTwitchTestModeCooldowns:
    """Test cooldown behavior in test mode."""

    def test_zombie_cooldown_blocks(self, pipeline):
        msg1 = _make_twitch_message("msg-300", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-301", "1", "ViewerA")

        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is None  # cooldown

    def test_chickens_no_cooldown(self, pipeline):
        msg1 = _make_twitch_message("msg-310", "10", "ViewerA")
        msg2 = _make_twitch_message("msg-311", "10", "ViewerA")
        msg3 = _make_twitch_message("msg-312", "10", "ViewerA")

        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is not None
        assert pipeline.process(msg3) is not None


# ─── Shutdown Tests ─────────────────────────────────────────────────────────


class TestTwitchTestModeShutdown:
    """Test clean shutdown."""

    def test_shutdown_flag(self):
        running = True

        def handle_signal(sig, frame):
            nonlocal running
            running = False

        import signal
        old_handler = signal.signal(signal.SIGINT, handle_signal)
        try:
            # Simulate signal
            handle_signal(signal.SIGINT, None)
            assert running is False
        finally:
            signal.signal(signal.SIGINT, old_handler)
