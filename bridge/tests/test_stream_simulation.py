from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from chat.command_parser import CommandParser
from core.config import Config
from core.models import PROTOCOL_VERSION, BridgeRequest
from core.protocol import serialize_request
from cooldowns.manager import CooldownManager
from minecraft.client import MinecraftClient
from mocks.core_mock import CoreMock
from mocks.twitch_mock import TwitchMock, SimScenario, SimMessage, load_scenario_yaml
from platforms.models import ChatMessage
from platforms.pipeline import ChatPipeline


@pytest.fixture
def mock_port():
    return 20876


@pytest.fixture
def mock(mock_port):
    m = CoreMock(port=mock_port, auth_token="TEST_TOKEN", auth_enabled=True)
    m.start()
    time.sleep(0.15)
    yield m
    m.stop()
    time.sleep(0.15)


@pytest.fixture
def config(mock_port):
    return Config({
        "minecraft": {"host": "127.0.0.1", "port": mock_port, "auth_token": "TEST_TOKEN"},
        "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
        "commands": {"prefix": "!", "cooldowns": {
            "zombie": 10, "spiders": 15, "slowness": 20, "blindness": 20,
            "creeper": 30, "storm": 60, "random_teleport": 60, "explosion": 30,
            "random_event": 60, "chickens": 0,
        }},
        "events": {
            "1": "zombie", "2": "spiders", "3": "slowness", "4": "blindness",
            "5": "creeper", "6": "storm", "7": "random_teleport", "8": "explosion",
            "9": "random_event", "10": "chickens",
        },
    })


EVENT_MAP = {
    "1": "zombie", "2": "spiders", "3": "slowness", "4": "blindness",
    "5": "creeper", "6": "storm", "7": "random_teleport", "8": "explosion",
    "9": "random_event", "10": "chickens",
}


def make_pipeline(config: Config) -> tuple[CommandParser, CooldownManager, ChatPipeline]:
    parser = CommandParser(prefix="!", event_number_map=EVENT_MAP)
    cooldowns = CooldownManager(config.get_all_cooldowns())
    pipeline = ChatPipeline(parser=parser, cooldowns=cooldowns, target_player="Streamer")
    return parser, cooldowns, pipeline


def make_chat_msg(user: str, text: str, msg_id: str | None = None) -> ChatMessage:
    return ChatMessage(
        platform="twitch",
        user_id=f"sim-{user.lower()}",
        username=user.lower(),
        display_name=user,
        message_id=msg_id or f"test-{user}-{int(time.time()*1000)}",
        message_text=text,
        channel_id="sim-ch",
        channel_name="SimChannel",
    )


# ─── TwitchMock Tests ────────────────────────────────────────────────────────


class TestTwitchMock:
    def test_inject_message(self):
        received = []
        mock = TwitchMock(on_message=lambda msg: received.append(msg))
        msg = mock.inject("ViewerA", "hello")
        assert len(received) == 1
        assert received[0].display_name == "ViewerA"
        assert received[0].message_text == "hello"
        assert received[0].platform == "twitch"

    def test_messages_sent_counter(self):
        mock = TwitchMock()
        assert mock.messages_sent == 0
        mock.inject("A", "1")
        mock.inject("B", "2")
        assert mock.messages_sent == 2

    def test_custom_message_id(self):
        mock = TwitchMock()
        msg = mock.inject("A", "1", message_id="custom-id")
        assert msg.message_id == "custom-id"

    def test_run_messages(self):
        received = []
        mock = TwitchMock(on_message=lambda msg: received.append(msg))
        msgs = mock.run_messages([("A", "1"), ("B", "2"), ("C", "3")])
        assert len(received) == 3
        assert received[0].display_name == "A"
        assert received[2].message_text == "3"


# ─── Scenario Loading ────────────────────────────────────────────────────────


class TestScenarioLoading:
    def test_load_yaml_scenario(self, tmp_path):
        yaml_content = """
name: test_scenario
messages:
  - user: ViewerA
    text: "1"
  - user: ViewerB
    text: "hello"
"""
        path = tmp_path / "test.yaml"
        path.write_text(yaml_content, encoding="utf-8")
        scenario = load_scenario_yaml(str(path))
        assert scenario.name == "test_scenario"
        assert len(scenario.messages) == 2
        assert scenario.messages[0].user == "ViewerA"
        assert scenario.messages[0].text == "1"
        assert scenario.messages[1].text == "hello"

    def test_sim_message_auto_id(self):
        msg = SimMessage(user="A", text="1")
        assert msg.message_id != ""

    def test_sim_message_custom_id(self):
        msg = SimMessage(user="A", text="1", message_id="custom")
        assert msg.message_id == "custom"


# ─── Full Pipeline Integration ───────────────────────────────────────────────


class TestFullPipeline:
    def test_message_to_request(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg = make_chat_msg("Viewer", "1")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"
        assert request.target == "Streamer"
        assert request.source == "twitch"

    def test_all_event_numbers(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        for number, expected in EVENT_MAP.items():
            msg = make_chat_msg("Viewer", number)
            request = pipeline.process(msg)
            assert request is not None, f"Number {number} produced no request"
            assert request.action == expected

    def test_normal_text_ignored(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg = make_chat_msg("Viewer", "hola mundo")
        assert pipeline.process(msg) is None

    def test_invalid_number_ignored(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg = make_chat_msg("Viewer", "100")
        assert pipeline.process(msg) is None

    def test_prefix_command(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg = make_chat_msg("Viewer", "!zombie")
        request = pipeline.process(msg)
        assert request is not None
        assert request.action == "zombie"


# ─── Cooldown Integration ────────────────────────────────────────────────────


class TestCooldownIntegration:
    def test_same_user_cooldown_blocks(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg1 = make_chat_msg("ViewerA", "1")
        msg2 = make_chat_msg("ViewerA", "1")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is None

    def test_different_users_not_cooldown(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg1 = make_chat_msg("ViewerA", "1")
        msg2 = make_chat_msg("ViewerB", "1")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is not None

    def test_chickens_no_cooldown(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        for i in range(5):
            msg = make_chat_msg("ViewerA", "10")
            assert pipeline.process(msg) is not None

    def test_different_actions_independent(self, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        msg1 = make_chat_msg("ViewerA", "1")
        msg2 = make_chat_msg("ViewerA", "2")
        assert pipeline.process(msg1) is not None
        assert pipeline.process(msg2) is not None


# ─── Bridge + CoreMock Integration ───────────────────────────────────────────


class TestBridgeCoreMock:
    def test_connect_auth_send(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        request = BridgeRequest(action="zombie", target="Streamer", source="twitch", user="Test")
        response = client.send_and_wait(request)
        assert response.success is True
        assert response.action == "zombie"
        client.disconnect()

    def test_full_pipeline_through_core(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        msg = make_chat_msg("Viewer", "1")
        request = pipeline.process(msg)
        assert request is not None

        response = client.send_and_wait(request)
        assert response.success is True
        assert response.action == "zombie"
        client.disconnect()

    def test_all_10_events_through_core(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        for number, expected in EVENT_MAP.items():
            msg = make_chat_msg("Viewer", number)
            request = pipeline.process(msg)
            assert request is not None
            response = client.send_and_wait(request)
            assert response.success is True, f"Event {number} failed"
            assert response.action == expected

        client.disconnect()

    def test_core_receives_correct_requests(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        mock.clear_received_requests()
        msg = make_chat_msg("Viewer", "1")
        request = pipeline.process(msg)
        client.send_and_wait(request)
        time.sleep(0.1)

        received = mock.get_received_requests()
        assert len(received) == 1
        assert received[0]["action"] == "zombie"
        assert received[0]["target"] == "Streamer"
        client.disconnect()


# ─── Authentication Tests ────────────────────────────────────────────────────


class TestAuthIntegration:
    def test_correct_token(self, mock):
        config = Config({
            "minecraft": {"host": "127.0.0.1", "port": mock.port, "auth_token": "TEST_TOKEN"},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })
        client = MinecraftClient(config)
        client.connect()
        assert client.authenticate() is True
        client.disconnect()

    def test_wrong_token(self, mock_port):
        m = CoreMock(port=mock_port + 100, auth_token="REAL_SECRET")
        m.start()
        time.sleep(0.15)
        try:
            config = Config({
                "minecraft": {"host": "127.0.0.1", "port": mock_port + 100, "auth_token": "WRONG"},
                "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
                "commands": {"prefix": "!", "cooldowns": {}},
            })
            client = MinecraftClient(config)
            client.connect()
            assert client.authenticate() is False
            client.disconnect()
        finally:
            m.stop()

    def test_no_token_configured(self, mock):
        config = Config({
            "minecraft": {"host": "127.0.0.1", "port": mock.port, "auth_token": ""},
            "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
            "commands": {"prefix": "!", "cooldowns": {}},
        })
        client = MinecraftClient(config)
        client.connect()
        assert client.authenticate() is True
        client.disconnect()

    def test_request_before_auth(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        request = BridgeRequest(action="zombie", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is False
        client.disconnect()


# ─── Reconnection Tests ──────────────────────────────────────────────────────


class TestReconnection:
    def test_reconnect_after_restart(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        request = BridgeRequest(action="zombie", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is True

        mock.stop()
        time.sleep(0.3)
        mock.start()
        time.sleep(0.3)

        client.disconnect()
        client.connect()
        assert client.authenticate() is True
        request2 = BridgeRequest(action="spiders", target="Streamer")
        response2 = client.send_and_wait(request2)
        assert response2.success is True
        client.disconnect()


# ─── Core Error Simulation ───────────────────────────────────────────────────


class TestCoreErrors:
    def test_player_not_found(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        request = BridgeRequest(action="zombie", target="NonExistent")
        response = client.send_and_wait(request)
        assert response.success is False
        assert response.error == "PLAYER_NOT_FOUND"
        client.disconnect()

    def test_system_disabled(self, mock, config):
        mock.set_system_enabled(False)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        request = BridgeRequest(action="zombie", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is False
        assert response.error == "SYSTEM_DISABLED"
        mock.set_system_enabled(True)
        client.disconnect()

    def test_unknown_action(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        request = BridgeRequest(action="nonexistent", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is False
        assert response.error == "UNKNOWN_ACTION"
        client.disconnect()

    def test_bridge_continues_after_error(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        request1 = BridgeRequest(action="zombie", target="NonExistent")
        response1 = client.send_and_wait(request1)
        assert response1.success is False

        request2 = BridgeRequest(action="zombie", target="Streamer")
        response2 = client.send_and_wait(request2)
        assert response2.success is True
        client.disconnect()


# ─── Chickens Rapid Fire ─────────────────────────────────────────────────────


class TestChickensRapid:
    def test_chickens_no_cooldown(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        for i in range(5):
            msg = make_chat_msg("Viewer", "10")
            request = pipeline.process(msg)
            assert request is not None
            response = client.send_and_wait(request)
            assert response.success is True

        client.disconnect()


# ─── Multi-User Tests ────────────────────────────────────────────────────────


class TestMultiUser:
    def test_different_users_same_action(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        for user in ["Alice", "Bob", "Charlie", "Dave"]:
            msg = make_chat_msg(user, "1")
            request = pipeline.process(msg)
            assert request is not None
            response = client.send_and_wait(request)
            assert response.success is True

        client.disconnect()


# ─── Mixed Scenario Test ─────────────────────────────────────────────────────


class TestMixedScenario:
    def test_mixed_messages(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        messages = [
            ("ViewerA", "hola", None),
            ("ViewerB", "1", None),
            ("ViewerC", "5", None),
            ("ViewerA", "1", None),
            ("ViewerD", "10", None),
            ("ViewerE", "100", None),
            ("ViewerB", "2", None),
            ("ViewerF", "!zombie", None),
            ("ViewerA", "10", None),
        ]

        results = {"ignored": 0, "sent": 0, "cooldown": 0}
        for user, text, _ in messages:
            msg = make_chat_msg(user, text)
            request = pipeline.process(msg)
            if request is None:
                results["ignored"] += 1
            else:
                response = client.send_and_wait(request)
                if response.success:
                    results["sent"] += 1
                else:
                    results["cooldown"] += 1

        assert results["sent"] > 0
        assert results["ignored"] > 0
        client.disconnect()


# ─── Duplicate Message Test ──────────────────────────────────────────────────


class TestDeduplication:
    def test_same_message_id_once(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        msg1 = make_chat_msg("Viewer", "1", msg_id="dedup-001")
        msg2 = make_chat_msg("Viewer", "1", msg_id="dedup-001")

        request1 = pipeline.process(msg1)
        assert request1 is not None
        response1 = client.send_and_wait(request1)
        assert response1.success is True

        request2 = pipeline.process(msg2)
        assert request2 is None

        client.disconnect()


# ─── Flood Test ───────────────────────────────────────────────────────────────


class TestFlood:
    def test_rapid_messages(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        sent = 0
        cooldown_blocked = 0
        for i in range(30):
            action = EVENT_MAP[str((i % 10) + 1)]
            msg = make_chat_msg(f"User{i}", str((i % 10) + 1))
            request = pipeline.process(msg)
            if request is not None:
                response = client.send_and_wait(request)
                if response.success:
                    sent += 1
                else:
                    cooldown_blocked += 1

        assert sent > 0
        client.disconnect()


# ─── TwitchMock + Pipeline + CoreMock End-to-End ─────────────────────────────


class TestEndToEnd:
    def test_twitch_mock_full_flow(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        received_requests = []

        def on_request(req):
            received_requests.append(req)

        pipeline_callback = ChatPipeline(
            parser=parser, cooldowns=cooldowns,
            target_player="Streamer", on_request=on_request,
        )

        twitch = TwitchMock(on_message=lambda msg: pipeline_callback.process(msg))

        scenario = SimScenario(name="e2e", messages=[
            SimMessage(user="A", text="1"),
            SimMessage(user="B", text="2"),
            SimMessage(user="C", text="10"),
            SimMessage(user="A", text="10"),
            SimMessage(user="D", text="hola"),
        ])
        twitch.run_scenario(scenario)

        assert len(received_requests) == 4
        assert received_requests[0].action == "zombie"
        assert received_requests[1].action == "spiders"
        assert received_requests[2].action == "chickens"
        assert received_requests[3].action == "chickens"

        for req in received_requests:
            response = client.send_and_wait(req)
            assert response.success is True

        client.disconnect()

    def test_twitch_mock_with_errors(self, mock, config):
        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        twitch = TwitchMock(on_message=lambda msg: pipeline.process(msg))

        scenario = SimScenario(name="error", messages=[
            SimMessage(user="A", text="1"),
            SimMessage(user="B", text="1"),
        ])
        twitch.run_scenario(scenario)

        request = BridgeRequest(action="zombie", target="NonExistent")
        response = client.send_and_wait(request)
        assert response.success is False

        request2 = BridgeRequest(action="zombie", target="Streamer")
        response2 = client.send_and_wait(request2)
        assert response2.success is True
        client.disconnect()


# ─── Scenario File Test ──────────────────────────────────────────────────────


class TestScenarioFile:
    def test_load_and_run(self, mock, config, tmp_path):
        yaml_content = """
name: file_test
messages:
  - user: ViewerA
    text: "1"
  - user: ViewerB
    text: "10"
"""
        path = tmp_path / "test.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        scenario = load_scenario_yaml(str(path))
        assert scenario.name == "file_test"
        assert len(scenario.messages) == 2

        parser, cooldowns, pipeline = make_pipeline(config)
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()

        twitch = TwitchMock(on_message=lambda msg: pipeline.process(msg))
        results = twitch.run_scenario(scenario)
        assert len(results) == 2

        client.disconnect()


# ─── Stop / Shutdown Test ────────────────────────────────────────────────────


class TestShutdown:
    def test_clean_shutdown(self, mock, config):
        client = MinecraftClient(config)
        client.connect()
        client.authenticate()
        request = BridgeRequest(action="zombie", target="Streamer")
        response = client.send_and_wait(request)
        assert response.success is True
        client.disconnect()
        assert not client.connected
        assert not client.authenticated

    def test_mock_stop(self, mock_port):
        m = CoreMock(port=mock_port + 200)
        m.start()
        time.sleep(0.1)
        m.stop()
        time.sleep(0.1)
        assert not m._running
        assert m.get_client_count() == 0
