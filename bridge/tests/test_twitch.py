import pytest
from platforms.models import ChatMessage
from integrations.twitch.config import TwitchConfig
from integrations.twitch.event_handler import TwitchEventHandler, MessageDeduplicator, _extract_badges


SAMPLE_EVENT = {
    "broadcaster_user_id": "12826",
    "broadcaster_user_name": "StreamChannel",
    "broadcaster_user_login": "streamchannel",
    "chatter_user_id": "456789",
    "chatter_user_name": "Viewer123",
    "chatter_user_login": "viewer123",
    "message_id": "msg-abc-123",
    "message": {
        "text": "!zombie",
        "fragments": [
            {"type": "text", "text": "!zombie", "cheermote": None, "emote": None, "mention": None}
        ],
    },
    "color": "#00FF7F",
    "badges": [
        {"set_id": "subscriber", "id": "12", "info": "16"},
    ],
    "message_type": "text",
    "cheer": None,
    "reply": None,
    "channel_points_custom_reward_id": None,
    "source_broadcaster_user_id": None,
    "source_broadcaster_user_login": None,
}

SAMPLE_EVENT_MODERATOR = {
    **SAMPLE_EVENT,
    "message_id": "msg-mod-001",
    "chatter_user_id": "789012",
    "chatter_user_name": "ModUser",
    "chatter_user_login": "moduser",
    "badges": [
        {"set_id": "moderator", "id": "1", "info": ""},
        {"set_id": "subscriber", "id": "1", "info": "6"},
    ],
}

SAMPLE_EVENT_BROADCASTER = {
    **SAMPLE_EVENT,
    "message_id": "msg-bc-001",
    "chatter_user_id": "12826",
    "chatter_user_name": "StreamChannel",
    "chatter_user_login": "streamchannel",
    "badges": [
        {"set_id": "broadcaster", "id": "1", "info": ""},
    ],
}

SAMPLE_EVENT_VIP = {
    **SAMPLE_EVENT,
    "message_id": "msg-vip-001",
    "chatter_user_id": "345678",
    "chatter_user_name": "VIPUser",
    "chatter_user_login": "vipuser",
    "badges": [
        {"set_id": "vip", "id": "1", "info": ""},
    ],
}

SAMPLE_EVENT_NORMAL_TEXT = {
    "broadcaster_user_id": "12826",
    "broadcaster_user_name": "StreamChannel",
    "broadcaster_user_login": "streamchannel",
    "chatter_user_id": "456789",
    "chatter_user_name": "Viewer123",
    "chatter_user_login": "viewer123",
    "message_id": "msg-abc-456",
    "message": {
        "text": "hello everyone!",
        "fragments": [],
    },
    "color": "",
    "badges": [],
    "message_type": "text",
    "cheer": None,
    "reply": None,
    "channel_points_custom_reward_id": None,
}


class TestExtractBadges:
    def test_empty_badges(self):
        result = _extract_badges([])
        assert result["is_broadcaster"] is False
        assert result["is_moderator"] is False
        assert result["is_vip"] is False
        assert result["is_subscriber"] is False
        assert result["badge_count"] == 0

    def test_subscriber_badge(self):
        badges = [{"set_id": "subscriber", "id": "12", "info": "16"}]
        result = _extract_badges(badges)
        assert result["is_subscriber"] is True
        assert result["is_moderator"] is False
        assert result["badge_count"] == 1

    def test_moderator_badge(self):
        badges = [{"set_id": "moderator", "id": "1", "info": ""}]
        result = _extract_badges(badges)
        assert result["is_moderator"] is True
        assert result["is_subscriber"] is False

    def test_broadcaster_badge(self):
        badges = [{"set_id": "broadcaster", "id": "1", "info": ""}]
        result = _extract_badges(badges)
        assert result["is_broadcaster"] is True

    def test_vip_badge(self):
        badges = [{"set_id": "vip", "id": "1", "info": ""}]
        result = _extract_badges(badges)
        assert result["is_vip"] is True

    def test_multiple_badges(self):
        badges = [
            {"set_id": "moderator", "id": "1", "info": ""},
            {"set_id": "subscriber", "id": "1", "info": "6"},
        ]
        result = _extract_badges(badges)
        assert result["is_moderator"] is True
        assert result["is_subscriber"] is True
        assert result["badge_count"] == 2


class TestTwitchConfig:
    def test_from_dict(self):
        data = {
            "twitch": {
                "enabled": True,
                "client_id": "my_client_id",
                "client_secret": "my_secret",
                "broadcaster_id": "12345",
                "bot_user_id": "67890",
                "channel": "TestChannel",
            }
        }
        config = TwitchConfig.from_dict(data)
        assert config.enabled is True
        assert config.client_id == "my_client_id"
        assert config.broadcaster_id == "12345"
        assert config.channel == "TestChannel"

    def test_from_dict_empty(self):
        config = TwitchConfig.from_dict({})
        assert config.enabled is False
        assert config.client_id == ""
        assert config.websocket_url == "wss://eventsub.wss.twitch.tv/ws"

    def test_validate_disabled(self):
        config = TwitchConfig(enabled=False)
        assert config.validate() == []

    def test_validate_missing_fields(self):
        config = TwitchConfig(enabled=True)
        errors = config.validate()
        assert len(errors) >= 3

    def test_validate_complete(self):
        config = TwitchConfig(
            enabled=True,
            client_id="id",
            access_token="token",
            broadcaster_id="123",
            channel="test",
        )
        assert config.validate() == []


class TestMessageDeduplicator:
    def test_new_message(self):
        dedup = MessageDeduplicator()
        assert dedup.is_duplicate("msg-001") is False

    def test_duplicate_message(self):
        dedup = MessageDeduplicator()
        dedup.is_duplicate("msg-001")
        assert dedup.is_duplicate("msg-001") is True

    def test_different_messages(self):
        dedup = MessageDeduplicator()
        assert dedup.is_duplicate("msg-001") is False
        assert dedup.is_duplicate("msg-002") is False

    def test_empty_id_not_deduped(self):
        dedup = MessageDeduplicator()
        assert dedup.is_duplicate("") is False
        assert dedup.is_duplicate("") is False

    def test_max_size_eviction(self):
        dedup = MessageDeduplicator(max_size=3)
        dedup.is_duplicate("msg-1")
        dedup.is_duplicate("msg-2")
        dedup.is_duplicate("msg-3")
        dedup.is_duplicate("msg-4")
        assert dedup.is_duplicate("msg-1") is False
        assert dedup.is_duplicate("msg-4") is True

    def test_concurrent_access(self):
        import threading
        dedup = MessageDeduplicator()
        results = []

        def check_dup(msg_id):
            results.append(dedup.is_duplicate(msg_id))

        threads = [threading.Thread(target=check_dup, args=(f"msg-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r is False for r in results)


class TestTwitchEventHandler:
    def setup_method(self):
        self.handler = TwitchEventHandler()

    def test_handle_chat_message(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT)
        assert msg is not None
        assert msg.platform == "twitch"
        assert msg.user_id == "456789"
        assert msg.username == "viewer123"
        assert msg.display_name == "Viewer123"
        assert msg.message_text == "!zombie"
        assert msg.message_id == "msg-abc-123"
        assert msg.channel_id == "12826"

    def test_handle_normal_text(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT_NORMAL_TEXT)
        assert msg is not None
        assert msg.message_text == "hello everyone!"

    def test_ignore_non_chat_event(self):
        msg = self.handler.handle_notification("channel.follow", {})
        assert msg is None

    def test_deduplication(self):
        msg1 = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT)
        assert msg1 is not None
        msg2 = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT)
        assert msg2 is None

    def test_empty_message_text(self):
        event = {**SAMPLE_EVENT, "message": {"text": "", "fragments": []}}
        msg = self.handler.handle_notification("channel.chat.message", event)
        assert msg is None

    def test_message_as_string(self):
        event = {**SAMPLE_EVENT, "message": "!zombie"}
        msg = self.handler.handle_notification("channel.chat.message", event)
        assert msg is not None
        assert msg.message_text == "!zombie"

    def test_missing_fields(self):
        msg = self.handler.handle_notification("channel.chat.message", {})
        assert msg is None

    def test_moderator_badges(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT_MODERATOR)
        assert msg is not None
        assert msg.raw_metadata["badges_flags"]["is_moderator"] is True

    def test_broadcaster_badges(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT_BROADCASTER)
        assert msg is not None
        assert msg.raw_metadata["badges_flags"]["is_broadcaster"] is True

    def test_vip_badges(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT_VIP)
        assert msg is not None
        assert msg.raw_metadata["badges_flags"]["is_vip"] is True

    def test_color_preserved(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT)
        assert msg is not None
        assert msg.raw_metadata["color"] == "#00FF7F"

    def test_fragments_preserved(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT)
        assert msg is not None
        assert len(msg.raw_metadata["fragments"]) > 0

    def test_broadcaster_fields(self):
        msg = self.handler.handle_notification("channel.chat.message", SAMPLE_EVENT)
        assert msg is not None
        assert msg.raw_metadata["broadcaster_user_login"] == "streamchannel"


class TestTwitchPlatform:
    def test_diagnostics_disabled(self):
        config = TwitchConfig(enabled=False)
        from integrations.twitch.platform import TwitchPlatform
        platform = TwitchPlatform(config)
        results = platform.run_diagnostics()
        assert results["config_valid"] is True
        assert results["ready"] is False

    def test_diagnostics_missing_fields(self):
        config = TwitchConfig(enabled=True)
        from integrations.twitch.platform import TwitchPlatform
        platform = TwitchPlatform(config)
        results = platform.run_diagnostics()
        assert results["config_valid"] is False
        assert len(results["errors"]) > 0
