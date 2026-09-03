import pytest
from unittest.mock import MagicMock
from platforms.models import ChatMessage
from platforms.pipeline import ChatPipeline
from chat.command_parser import CommandParser
from cooldowns.manager import CooldownManager


class TestChatMessage:
    def test_twitch_message(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        assert msg.platform == "twitch"
        assert msg.username == "viewer123"
        assert msg.message_text == "!zombie"

    def test_generic_message(self):
        msg = ChatMessage(
            platform="console",
            user_id="yt-123",
            username="console_user",
            display_name="Console User",
            message_id="msg-001",
            message_text="!pollos",
            channel_id="local",
            channel_name="Local",
        )
        assert msg.platform == "console"
        assert msg.message_text == "!pollos"

    def test_raw_metadata(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
            raw_metadata={"custom": "data"},
        )
        assert msg.raw_metadata == {"custom": "data"}

    def test_optional_fields(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-001",
            message_text="hello",
            channel_id="456",
            channel_name="Streamer",
        )
        assert msg.timestamp == ""
        assert msg.raw_metadata == {}


class TestChatPipeline:
    def setup_method(self):
        self.parser = CommandParser(prefix="!")
        self.cooldowns = CooldownManager({"zombie": 10, "chickens": 0})
        self.pipeline = ChatPipeline(
            parser=self.parser,
            cooldowns=self.cooldowns,
            target_player="Streamer",
        )

    def test_process_command(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"
        assert request.user == "Viewer123"

    def test_process_normal_text(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="hello everyone",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg)
        assert request is None

    def test_process_unknown_command(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="!invalid",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg)
        assert request is None

    def test_cooldown_blocks(self):
        msg1 = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        self.pipeline.process(msg1)

        msg2 = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-002",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg2)
        assert request is None

    def test_chickens_no_cooldown(self):
        msg1 = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="!pollos",
            channel_id="456",
            channel_name="Streamer",
        )
        self.pipeline.process(msg1)

        msg2 = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-002",
            message_text="!pollos",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg2)
        assert request is not None

    def test_callback_called(self):
        callback = MagicMock()
        pipeline = ChatPipeline(
            parser=self.parser,
            cooldowns=self.cooldowns,
            target_player="Streamer",
            on_request=callback,
        )
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer123",
            display_name="Viewer123",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        pipeline.process(msg)
        callback.assert_called_once()

    def test_platform_independence(self):
        twitch_msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        console_msg = ChatMessage(
            platform="console",
            user_id="console-123",
            username="console_user",
            display_name="Console User",
            message_id="msg-002",
            message_text="!zombie",
            channel_id="local",
            channel_name="Local",
        )

        req1 = self.pipeline.process(twitch_msg)
        req2 = self.pipeline.process(console_msg)

        assert req1 is not None
        assert req2 is not None
        assert req1.action == req2.action
        assert req1.source == "twitch"
        assert req2.source == "console"

    def test_user_specific_cooldown(self):
        msg_user1 = ChatMessage(
            platform="twitch",
            user_id="123",
            username="user1",
            display_name="User1",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        self.pipeline.process(msg_user1)

        msg_user2 = ChatMessage(
            platform="twitch",
            user_id="789",
            username="user2",
            display_name="User2",
            message_id="msg-002",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg_user2)
        assert request is not None

    def test_request_source_preserved(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg)
        assert request is not None
        assert request.source == "twitch"
        assert request.user == "Viewer"

    def test_request_user_from_display_name(self):
        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer_login",
            display_name="Viewer_Display",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )
        request = self.pipeline.process(msg)
        assert request is not None
        assert request.user == "Viewer_Display"


class TestMinecraftOffline:
    def test_process_chat_message_no_mc_no_queue(self):
        from main import _process_chat_message
        from platforms.pipeline import ChatPipeline
        from chat.command_parser import CommandParser
        from cooldowns.manager import CooldownManager

        parser = CommandParser(prefix="!")
        cooldowns = CooldownManager({"zombie": 0})
        pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")

        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )

        _process_chat_message(msg, pipeline, None, None)

    def test_process_chat_message_with_queue(self):
        from main import _process_chat_message
        from platforms.pipeline import ChatPipeline
        from chat.command_parser import CommandParser
        from cooldowns.manager import CooldownManager
        import queue

        parser = CommandParser(prefix="!")
        cooldowns = CooldownManager({"zombie": 0})
        pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")
        action_queue = queue.Queue(maxsize=10)

        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-001",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )

        _process_chat_message(msg, pipeline, None, action_queue)
        assert not action_queue.empty()
        request = action_queue.get_nowait()
        assert request.action == "zombie"

    def test_queue_full_drops_action(self):
        from main import _process_chat_message, ACTION_QUEUE_MAX_SIZE
        from platforms.pipeline import ChatPipeline
        from chat.command_parser import CommandParser
        from cooldowns.manager import CooldownManager
        import queue

        parser = CommandParser(prefix="!")
        cooldowns = CooldownManager({"zombie": 0})
        pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")
        action_queue = queue.Queue(maxsize=ACTION_QUEUE_MAX_SIZE)

        for i in range(ACTION_QUEUE_MAX_SIZE):
            action_queue.put_nowait(f"item-{i}")

        msg = ChatMessage(
            platform="twitch",
            user_id="123",
            username="viewer",
            display_name="Viewer",
            message_id="msg-overflow",
            message_text="!zombie",
            channel_id="456",
            channel_name="Streamer",
        )

        _process_chat_message(msg, pipeline, None, action_queue)
