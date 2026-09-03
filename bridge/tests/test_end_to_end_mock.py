"""End-to-End Mock Tests — Twitch Event → BridgeRequest.

Simulates the complete flow:
Twitch Event → ChatMessage → CommandParser → CooldownManager → BridgeRequest

Tests all event numbers (1-10) and invalid messages.
"""
from __future__ import annotations

import pytest

from platforms.models import ChatMessage
from platforms.pipeline import ChatPipeline
from chat.command_parser import CommandParser
from cooldowns.manager import CooldownManager


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


def _make_twitch_message(message_id: str, text: str, user: str = "Viewer123") -> ChatMessage:
    return ChatMessage(
        platform="twitch",
        user_id="123456",
        username=user.lower(),
        display_name=user,
        message_id=message_id,
        message_text=text,
        channel_id="789012",
        channel_name="StreamerChannel",
    )


# ─── Event Numbers 1-10 ──────────────────────────────────────────────────────


class TestEventNumbersEndToEnd:
    """Test complete flow for each event number."""

    def test_number_1_zombie(self, pipeline):
        msg = _make_twitch_message("msg-001", "1")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"
        assert request.user == "Viewer123"

    def test_number_2_spiders(self, pipeline):
        msg = _make_twitch_message("msg-002", "2")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "spiders"

    def test_number_3_slowness(self, pipeline):
        msg = _make_twitch_message("msg-003", "3")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "slowness"

    def test_number_4_blindness(self, pipeline):
        msg = _make_twitch_message("msg-004", "4")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "blindness"

    def test_number_5_creeper(self, pipeline):
        msg = _make_twitch_message("msg-005", "5")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "creeper"

    def test_number_6_storm(self, pipeline):
        msg = _make_twitch_message("msg-006", "6")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "storm"

    def test_number_7_random_teleport(self, pipeline):
        msg = _make_twitch_message("msg-007", "7")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "random_teleport"

    def test_number_8_explosion(self, pipeline):
        msg = _make_twitch_message("msg-008", "8")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "explosion"

    def test_number_9_random_event(self, pipeline):
        msg = _make_twitch_message("msg-009", "9")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "random_event"

    def test_number_10_chickens(self, pipeline):
        msg = _make_twitch_message("msg-010", "10")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "chickens"

    def test_number_10_with_spaces(self, pipeline):
        msg = _make_twitch_message("msg-011", "10  ")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "chickens"

    def test_number_with_prefix_ignored(self, pipeline):
        msg = _make_twitch_message("msg-012", "!1")
        request = pipeline.process(msg)
        assert request is None


# ─── Invalid Messages ────────────────────────────────────────────────────────


class TestInvalidMessages:
    """Messages that should NOT produce a BridgeRequest."""

    def test_hola_ignored(self, pipeline):
        msg = _make_twitch_message("msg-100", "hola")
        assert pipeline.process(msg) is None

    def test_number_with_text_suffix_ignored(self, pipeline):
        msg = _make_twitch_message("msg-101", "1 hola")
        assert pipeline.process(msg) is None

    def test_evento_prefix_ignored(self, pipeline):
        msg = _make_twitch_message("msg-102", "evento 1")
        assert pipeline.process(msg) is None

    def test_exclamation_1_ignored(self, pipeline):
        msg = _make_twitch_message("msg-103", "!1")
        assert pipeline.process(msg) is None

    def test_number_11_ignored(self, pipeline):
        msg = _make_twitch_message("msg-104", "11")
        assert pipeline.process(msg) is None

    def test_number_0_ignored(self, pipeline):
        msg = _make_twitch_message("msg-105", "0")
        assert pipeline.process(msg) is None

    def test_number_01_ignored(self, pipeline):
        msg = _make_twitch_message("msg-106", "01")
        assert pipeline.process(msg) is None

    def test_number_10_0_ignored(self, pipeline):
        msg = _make_twitch_message("msg-107", "1.0")
        assert pipeline.process(msg) is None

    def test_empty_message_ignored(self, pipeline):
        msg = _make_twitch_message("msg-108", "")
        assert pipeline.process(msg) is None

    def test_whitespace_only_ignored(self, pipeline):
        msg = _make_twitch_message("msg-109", "   ")
        assert pipeline.process(msg) is None


# ─── Cooldowns ───────────────────────────────────────────────────────────────


class TestCooldownsEndToEnd:
    """Test cooldown behavior in the full pipeline."""

    def test_zombie_cooldown_blocks_second(self, pipeline):
        msg1 = _make_twitch_message("msg-200", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-201", "1", "ViewerA")
        request1 = pipeline.process(msg1)
        assert request1 is not None
        request2 = pipeline.process(msg2)
        assert request2 is None

    def test_chickens_no_cooldown(self, pipeline):
        msg1 = _make_twitch_message("msg-210", "10", "ViewerA")
        msg2 = _make_twitch_message("msg-211", "10", "ViewerA")
        msg3 = _make_twitch_message("msg-212", "10", "ViewerA")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is not None
        assert pipeline.process(msg3) is not None

    def test_different_users_independent(self, pipeline):
        msg1 = _make_twitch_message("msg-220", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-221", "1", "ViewerB")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is not None


# ─── Deduplication ───────────────────────────────────────────────────────────


class TestDeduplicationEndToEnd:
    """Test message deduplication in the full pipeline."""

    def test_same_message_id_once(self, pipeline):
        msg1 = _make_twitch_message("msg-300", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-300", "1", "ViewerA")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is None

    def test_different_ids_both_processed(self, pipeline):
        msg1 = _make_twitch_message("msg-310", "1", "ViewerA")
        msg2 = _make_twitch_message("msg-311", "1", "ViewerA")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is None  # cooldown


# ─── BridgeRequest Format ────────────────────────────────────────────────────


class TestBridgeRequestFormat:
    """Verify the BridgeRequest contains correct fields."""

    def test_zombie_request_fields(self, pipeline):
        msg = _make_twitch_message("msg-400", "1", "TestUser")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"
        assert request.user == "TestUser"

    def test_spiders_request_fields(self, pipeline):
        msg = _make_twitch_message("msg-401", "2", "SpiderFan")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "spiders"
        assert request.user == "SpiderFan"

    def test_explosion_request_fields(self, pipeline):
        msg = _make_twitch_message("msg-402", "8", "BoomUser")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "explosion"
        assert request.user == "BoomUser"
