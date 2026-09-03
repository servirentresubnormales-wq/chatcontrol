#!/usr/bin/env python3
"""ChatControl Integration Test Runner.

Starts a CoreMock, connects via MinecraftClient, and runs a full
Twitch → Bridge → TCP → Auth → Core Mock integration test.

Usage:
    python tests/run_integration.py
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")

from core.config import Config
from core.models import BridgeRequest
from core.protocol import serialize_request
from minecraft.client import MinecraftClient
from mocks.core_mock import CoreMock

MOCK_PORT = 19876
AUTH_TOKEN = "INTEGRATION_TEST_TOKEN"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

EVENT_MAP = {
    "1": "zombie", "2": "spiders", "3": "slowness", "4": "blindness",
    "5": "creeper", "6": "storm", "7": "random_teleport", "8": "explosion",
    "9": "random_event", "10": "chickens",
}


def make_config(port: int = MOCK_PORT, token: str = AUTH_TOKEN) -> Config:
    return Config({
        "minecraft": {"host": "127.0.0.1", "port": port, "auth_token": token},
        "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
        "commands": {"prefix": "!", "cooldowns": {}},
    })


def test_auth_correct_token(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    result = client.authenticate()
    client.disconnect()
    return result is True


def test_auth_wrong_token(mock: CoreMock) -> bool:
    config = Config({
        "minecraft": {"host": "127.0.0.1", "port": MOCK_PORT, "auth_token": "WRONG_TOKEN"},
        "bridge": {"target_player": "Streamer", "reconnect_delay": 1, "request_timeout": 5},
        "commands": {"prefix": "!", "cooldowns": {}},
    })
    client = MinecraftClient(config)
    client.connect()
    result = client.authenticate()
    client.disconnect()
    return result is False


def test_action_before_auth(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    request = BridgeRequest(action="zombie", target="Streamer")
    response = client.send_and_wait(request)
    client.disconnect()
    return response.success is False and response.error in ("NOT_AUTHENTICATED", "UNAUTHORIZED")


def test_send_action(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    client.authenticate()
    request = BridgeRequest(action="zombie", target="Streamer", source="twitch", user="IntegrationTest")
    response = client.send_and_wait(request)
    client.disconnect()
    return response.success is True and response.action == "zombie"


def test_player_not_found(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    client.authenticate()
    request = BridgeRequest(action="zombie", target="NonExistentPlayer")
    response = client.send_and_wait(request)
    client.disconnect()
    return response.success is False and response.error == "PLAYER_NOT_FOUND"


def test_reconnect(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    client.authenticate()
    request = BridgeRequest(action="zombie", target="Streamer")
    response = client.send_and_wait(request)
    if not response.success:
        client.disconnect()
        return False

    mock.stop()
    time.sleep(0.3)
    mock.start()
    time.sleep(0.3)

    client.disconnect()
    client.connect()
    result = client.authenticate()
    if not result:
        client.disconnect()
        return False

    request2 = BridgeRequest(action="spiders", target="Streamer")
    response2 = client.send_and_wait(request2)
    client.disconnect()
    return response2.success is True


def test_event_numbers(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    client.authenticate()

    for number, expected in EVENT_MAP.items():
        request = BridgeRequest(action=expected, target="Streamer", source="twitch", user="EventTest")
        response = client.send_and_wait(request)
        if not response.success or response.action != expected:
            client.disconnect()
            return False

    client.disconnect()
    return True


def test_chickens_rapid(mock: CoreMock) -> bool:
    config = make_config()
    client = MinecraftClient(config)
    client.connect()
    client.authenticate()

    for i in range(5):
        request = BridgeRequest(action="chickens", target="Streamer", source="twitch", user="ChickensTest")
        response = client.send_and_wait(request)
        if not response.success:
            client.disconnect()
            return False

    client.disconnect()
    return True


def main() -> int:
    print()
    print("=" * 50)
    print("  ChatControl Integration Test")
    print("=" * 50)
    print()

    mock = CoreMock(port=MOCK_PORT, auth_token=AUTH_TOKEN, auth_enabled=True)
    mock.start()
    time.sleep(0.2)

    results = []

    def run(name: str, fn) -> None:
        try:
            ok = fn()
            status = PASS if ok else FAIL
            results.append((name, ok))
            print(f"  [{status}] {name}")
        except Exception as e:
            results.append((name, False))
            print(f"  [{FAIL}] {name} — {e}")

    run("AUTH PASS — correct token", lambda: test_auth_correct_token(mock))
    run("AUTH FAIL — wrong token", lambda: test_auth_wrong_token(mock))
    run("REJECT  — action before auth", lambda: test_action_before_auth(mock))
    run("REQUEST — zombie action", lambda: test_send_action(mock))
    run("ERROR   — player not found", lambda: test_player_not_found(mock))
    run("RECONNECT — server restart", lambda: test_reconnect(mock))
    run("EVENTS  — all 10 event numbers", lambda: test_event_numbers(mock))
    run("CHICKENS — rapid fire 5x", lambda: test_chickens_rapid(mock))

    mock.stop()

    print()
    print("-" * 50)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    if passed == total:
        print(f"  ALL {total} TESTS PASSED")
    else:
        print(f"  {passed}/{total} tests passed")
        for name, ok in results:
            if not ok:
                print(f"    FAILED: {name}")
    print("-" * 50)
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
