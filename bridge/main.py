#!/usr/bin/env python3
"""ChatControl Bridge — Base entry point."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
import threading
import queue
from typing import NoReturn

from core.config import load_config
from core.models import BridgeRequest
from chat.command_parser import CommandParser
from cooldowns.manager import CooldownManager
from minecraft.client import MinecraftClient
from minecraft.command_builder import build_action
from platforms.models import ChatMessage
from platforms.pipeline import ChatPipeline
from integrations.twitch.config import TwitchConfig
from integrations.twitch.platform import TwitchPlatform
from integrations.twitch.auth import TwitchAuth

logger = logging.getLogger("chatcontrol")

ACTION_QUEUE_MAX_SIZE = 100
ACTION_QUEUE_TIMEOUT = 5.0


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "[%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stdout)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("websocket").setLevel(logging.WARNING)


def run_bridge(config_path: str | None, mock: bool, verbose: bool) -> NoReturn:
    setup_logging(verbose)
    config = load_config(config_path)
    twitch_config = TwitchConfig.from_dict(config._data)

    parser = CommandParser(
        prefix=config.command_prefix,
        event_number_map=config.get_event_number_map(),
    )
    cooldowns = CooldownManager(config.get_all_cooldowns())

    logger.info("ChatControl Bridge starting...")
    logger.info("Target: %s", config.target_player)
    logger.info("Commands prefix: %s", config.command_prefix)
    logger.info("Available commands: %s", ", ".join(parser.get_available_commands()))

    if twitch_config.enabled:
        logger.info("Twitch integration: ENABLED (channel=%s)", twitch_config.channel)
    else:
        logger.info("Twitch integration: DISABLED")

    if mock:
        logger.info("Running in MOCK mode (no Minecraft connection)")
        run_mock_loop(parser, cooldowns, config, twitch_config)
    else:
        run_live_loop(parser, cooldowns, config, twitch_config)


def _process_chat_message(
    chat_msg: ChatMessage,
    pipeline: ChatPipeline,
    mc_client: MinecraftClient | None,
    action_queue: queue.Queue[BridgeRequest] | None = None,
) -> None:
    request = pipeline.process(chat_msg)
    if request is None:
        return

    if mc_client and mc_client.connected:
        response = mc_client.send_and_wait(request)
        if not response.success:
            logger.warning("[WARNING] %s: %s", response.error, response.message)
        else:
            logger.info("[OK] %s", response.message)
    elif action_queue is not None:
        try:
            action_queue.put_nowait(request)
            logger.debug("[QUEUE] Action queued: %s", request.action)
        except queue.Full:
            logger.warning(
                "[WARNING] Action queue full, dropping: %s from %s",
                request.action, chat_msg.display_name,
            )
    else:
        logger.warning("[WARNING] Minecraft Core unavailable, action not sent: %s", request.action)


def run_mock_loop(
    parser: CommandParser,
    cooldowns: CooldownManager,
    config,
    twitch_config: TwitchConfig,
) -> NoReturn:
    pipeline = ChatPipeline(
        parser=parser,
        cooldowns=cooldowns,
        target_player=config.target_player,
    )

    twitch_platform = None
    if twitch_config.enabled:
        twitch_platform = TwitchPlatform(twitch_config)
        twitch_platform.set_on_message(
            lambda msg: _process_chat_message(msg, pipeline, None)
        )
        twitch_platform.start()

    logger.info("Type commands (prefix: %s). Type 'quit' to exit.", config.command_prefix)
    try:
        while True:
            try:
                line = input(f"{config.command_prefix}> ").strip()
            except (EOFError, KeyboardInterrupt):
                logger.info("Shutting down...")
                break

            if line.lower() in ("quit", "exit", "q"):
                logger.info("Shutting down...")
                break

            if not line:
                continue

            parsed = parser.parse(line)
            if parsed is None:
                if not line.startswith(config.command_prefix):
                    logger.info("Commands must start with '%s'", config.command_prefix)
                continue

            if not parsed.valid:
                logger.warning("[WARNING] %s", parsed.error)
                continue

            if cooldowns.is_on_cooldown(parsed.action):
                remaining = cooldowns.get_remaining(parsed.action)
                logger.warning(
                    "[WARNING] Command '%s' on cooldown (%.1fs remaining)",
                    parsed.command,
                    remaining,
                )
                continue

            request = build_action(
                action=parsed.action,
                target=config.target_player,
                source="bridge",
                user="console",
                params=parsed.params if parsed.params else None,
            )

            logger.info("[MOCK] Would send: %s", request.to_dict())
            cooldowns.apply_cooldown(parsed.action)
    finally:
        if twitch_platform:
            twitch_platform.stop()

    sys.exit(0)


def run_live_loop(
    parser: CommandParser,
    cooldowns: CooldownManager,
    config,
    twitch_config: TwitchConfig,
) -> NoReturn:
    mc_client = MinecraftClient(config)
    twitch_platform = None
    running = True
    action_queue: queue.Queue[BridgeRequest] = queue.Queue(maxsize=ACTION_QUEUE_MAX_SIZE)

    def handle_signal(sig, frame):
        nonlocal running
        running = False
        logger.info("Received signal %s, shutting down...", sig)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    pipeline = ChatPipeline(
        parser=parser,
        cooldowns=cooldowns,
        target_player=config.target_player,
    )

    if twitch_config.enabled:
        twitch_platform = TwitchPlatform(twitch_config)
        twitch_platform.set_on_message(
            lambda msg: _process_chat_message(msg, pipeline, mc_client, action_queue)
        )
        twitch_platform.start()

    def _process_queue():
        while running:
            try:
                request = action_queue.get(timeout=ACTION_QUEUE_TIMEOUT)
            except queue.Empty:
                continue

            if mc_client.connected and mc_client.authenticated:
                response = mc_client.send_and_wait(request)
                if not response.success:
                    logger.warning("[WARNING] %s: %s", response.error, response.message)
                else:
                    logger.info("[OK] %s", response.message)
            else:
                logger.warning("[WARNING] Minecraft Core offline, re-queuing: %s", request.action)
                try:
                    action_queue.put_nowait(request)
                except queue.Full:
                    logger.error("[ERROR] Queue full, dropping: %s", request.action)
                time.sleep(1)

    queue_thread = threading.Thread(target=_process_queue, name="ActionQueue", daemon=True)
    queue_thread.start()

    try:
        while running:
            try:
                mc_client.connect()
                if not mc_client.authenticate():
                    logger.error("[ERROR] Authentication failed. Retrying in %ds...", config.reconnect_delay)
                    mc_client.disconnect()
                    time.sleep(config.reconnect_delay)
                    continue
            except Exception as e:
                logger.error("[ERROR] Cannot connect: %s. Retrying in %ds...", e, config.reconnect_delay)
                time.sleep(config.reconnect_delay)
                continue

            logger.info("Connected. Waiting for commands...")
            logger.info("Type commands (prefix: %s). Type 'quit' to exit.", config.command_prefix)

            while running:
                try:
                    line = input(f"{config.command_prefix}> ").strip()
                except (EOFError, KeyboardInterrupt):
                    running = False
                    break

                if line.lower() in ("quit", "exit", "q"):
                    running = False
                    break

                if not line:
                    continue

                parsed = parser.parse(line)
                if parsed is None:
                    if not line.startswith(config.command_prefix):
                        logger.info("Commands must start with '%s'", config.command_prefix)
                    continue

                if not parsed.valid:
                    logger.warning("[WARNING] %s", parsed.error)
                    continue

                if cooldowns.is_on_cooldown(parsed.action):
                    remaining = cooldowns.get_remaining(parsed.action)
                    logger.warning(
                        "[WARNING] Command '%s' on cooldown (%.1fs remaining)",
                        parsed.command,
                        remaining,
                    )
                    continue

                request = build_action(
                    action=parsed.action,
                    target=config.target_player,
                    source="bridge",
                    user="console",
                    params=parsed.params if parsed.params else None,
                )

                response = mc_client.send_and_wait(request)
                if not response.success:
                    logger.warning("[WARNING] %s: %s", response.error, response.message)
                else:
                    logger.info("[OK] %s", response.message)

                cooldowns.apply_cooldown(parsed.action)

                if not mc_client.connected:
                    logger.warning("[WARNING] Connection lost. Reconnecting...")
                    break
    finally:
        if twitch_platform:
            twitch_platform.stop()
        mc_client.disconnect()

    logger.info("ChatControl Bridge stopped.")
    sys.exit(0)


def run_check_twitch(config_path: str | None) -> None:
    """Diagnostic mode for Twitch integration."""
    setup_logging(False)
    config = load_config(config_path)
    twitch_config = TwitchConfig.from_dict(config._data)

    print()
    print("ChatControl Twitch Diagnostic")
    print("=" * 40)

    print()
    print("[STEP] Configuration")
    print("-" * 40)
    twitch_config.log_diagnostics()

    if not twitch_config.enabled:
        print()
        print("[INFO] Twitch is disabled in config. Nothing else to check.")
        print()
        return

    if not twitch_config.validate():
        print()
        print("[STEP] Token Validation")
        print("-" * 40)
        platform = TwitchPlatform(twitch_config)
        results = platform.run_diagnostics()

        if results["token_valid"]:
            token_info = results["token_info"]
            print(f"  [OK] Token valid")
            print(f"       Login: {token_info['login']}")
            print(f"       User ID: {token_info['user_id']}")
            print(f"       Client ID: {token_info['client_id']}")
            print(f"       Expires in: {token_info['expires_in']}s")
            print(f"       Scopes: {', '.join(token_info['scopes'])}")
        else:
            print(f"  [FAIL] Token validation failed")
            for err in results["errors"]:
                print(f"         {err}")

        print()
        print("[STEP] Scopes Check")
        print("-" * 40)
        if results["scopes_ok"]:
            print("  [OK] All required scopes present")
        else:
            print(f"  [FAIL] Missing scopes: {', '.join(results['missing_scopes'])}")
            print("         Re-authorize with user:read:chat scope.")

        print()
        print("[STEP] EventSub Readiness")
        print("-" * 40)
        if results["ready"]:
            print(f"  [OK] Broadcaster ID: {results['broadcaster_id']}")
            print(f"  [OK] WebSocket URL: {results['websocket_url']}")
            print()
            print("Ready for EventSub connection.")
        else:
            print("  [FAIL] Not ready for EventSub")
            for err in results["errors"]:
                print(f"         {err}")
    else:
        print()
        print("[FAIL] Configuration has errors. Fix them before proceeding.")

    print()


def run_twitch_login(config_path: str | None) -> None:
    """OAuth Authorization Code Flow for Twitch.

    Steps:
    1. Start local HTTP server on port 3000
    2. Open browser to Twitch authorization URL
    3. User authorizes the application
    4. Twitch redirects to localhost:3000 with authorization code
    5. Exchange code for access token + refresh token
    6. Save tokens to config.yaml
    """
    import secrets
    import webbrowser
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs

    setup_logging(False)
    config = load_config(config_path)
    twitch_config = TwitchConfig.from_dict(config._data)

    print()
    print("ChatControl Twitch OAuth Login")
    print("=" * 40)

    if not twitch_config.client_id:
        print("[FAIL] twitch.client_id is missing.")
        print("       Set it in config.yaml before running --twitch-login.")
        print()
        return

    if not twitch_config.client_secret:
        print("[FAIL] twitch.client_secret is missing.")
        print("       Set it in config.yaml before running --twitch-login.")
        print()
        return

    redirect_uri = "http://localhost:3000"
    state = secrets.token_urlsafe(32)

    auth = TwitchAuth(twitch_config)
    auth_url = auth.get_authorize_url(redirect_uri, state)

    print()
    print("[STEP 1] Open this URL in your browser:")
    print()
    print(f"  {auth_url}")
    print()
    print("[STEP 2] Log in with your Twitch account")
    print("[STEP 3] Click 'Authorize' to grant access")
    print()
    print("Waiting for authorization callback on http://localhost:3000 ...")
    print()

    auth_code = None
    auth_state = None

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, auth_state
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if "code" in params:
                auth_code = params["code"][0]
                auth_state = params.get("state", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this window.</p>")
            elif "error" in params:
                error = params["error"][0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h1>Authorization failed: {error}</h1>".encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress server logs

    server = HTTPServer(("localhost", 3000), OAuthHandler)
    server.timeout = 120  # 2 minutes to complete auth

    try:
        webbrowser.open(auth_url)
        server.handle_request()
    except KeyboardInterrupt:
        print("\n[INFO] Cancelled by user.")
        return
    finally:
        server.server_close()

    if not auth_code:
        print("[FAIL] No authorization code received.")
        print()
        return

    if auth_state != state:
        print("[FAIL] State mismatch - possible CSRF attack.")
        print()
        return

    print("[STEP 4] Exchanging authorization code for tokens...")

    try:
        result = auth.exchange_code(auth_code, redirect_uri)
    except Exception as e:
        print(f"[FAIL] Token exchange failed: {e}")
        print()
        return

    access_token = result.get("access_token", "")
    refresh_token = result.get("refresh_token", "")
    expires_in = result.get("expires_in", 0)
    scopes = result.get("scope", [])

    if not access_token:
        print("[FAIL] No access token received.")
        print()
        return

    print()
    print("[STEP 5] Tokens obtained successfully!")
    print(f"         Access Token: {access_token[:8]}...")
    print(f"         Expires in: {expires_in}s")
    print(f"         Scopes: {', '.join(scopes)}")
    print()

    # Validate the token to get user info
    token_info = auth.validate_token()
    if token_info.valid:
        print("[STEP 6] Token validated:")
        print(f"         Login: {token_info.login}")
        print(f"         User ID: {token_info.user_id}")
    else:
        print(f"[WARNING] Token validation failed: {token_info.error}")

    # Update config.yaml
    print()
    print("[STEP 7] Saving tokens to config.yaml...")

    config_file = config_path or "config.yaml"
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_content = f.read()

        import re
        config_content = re.sub(
            r"access_token:.*",
            f"access_token: \"{access_token}\"",
            config_content,
        )
        if refresh_token:
            config_content = re.sub(
                r"refresh_token:.*",
                f"refresh_token: \"{refresh_token}\"",
                config_content,
            )
        if token_info.valid:
            config_content = re.sub(
                r"broadcaster_id:.*",
                f"broadcaster_id: \"{token_info.user_id}\"",
                config_content,
            )

        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config_content)

        print(f"  [OK] Tokens saved to {config_file}")
    except Exception as e:
        print(f"  [WARNING] Could not save to config: {e}")
        print("           Manually update config.yaml with:")
        print(f'           access_token: "{access_token}"')
        if refresh_token:
            print(f'           refresh_token: "{refresh_token}"')

    print()
    print("Run 'python main.py --check-twitch' to verify the configuration.")
    print()


def run_twitch_test_loop(
    parser: CommandParser,
    cooldowns: CooldownManager,
    config,
    twitch_config: TwitchConfig,
) -> NoReturn:
    """Twitch test mode: real Twitch, no Minecraft.

    Connects to real Twitch EventSub, receives real messages,
    processes through ChatPipeline, but does NOT send to Minecraft.
    """
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False
        logger.info("Received signal %s, shutting down...", sig)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    pipeline = ChatPipeline(
        parser=parser,
        cooldowns=cooldowns,
        target_player=config.target_player,
    )

    def _on_test_message(chat_msg: ChatMessage) -> None:
        """Process a real Twitch message in test mode."""
        # Show user info
        badge_info = ""
        if chat_msg.raw_metadata.get("badges_flags"):
            flags = chat_msg.raw_metadata["badges_flags"]
            badge_str = ", ".join(
                k.replace("is_", "") for k, v in flags.items()
                if v and k.startswith("is_")
            )
            badge_info = f" [{badge_str}]" if badge_str else ""

        logger.info(
            "[TWITCH] %s%s (ID: %s): %s",
            chat_msg.display_name,
            badge_info,
            chat_msg.user_id,
            chat_msg.message_text,
        )

        # Process through pipeline
        parsed = parser.parse(chat_msg.message_text)
        if parsed is None:
            return

        if not parsed.valid:
            logger.warning("[WARNING] %s", parsed.error)
            return

        # Check cooldown
        if cooldowns.is_on_cooldown(
            parsed.action, user=chat_msg.username, platform=chat_msg.platform
        ):
            remaining = cooldowns.get_remaining(
                parsed.action, user=chat_msg.username, platform=chat_msg.platform
            )
            logger.warning(
                "[COOLDOWN] %s on cooldown (%.1fs remaining)",
                parsed.command,
                remaining,
            )
            return

        # Build request (but don't send)
        request = build_action(
            action=parsed.action,
            target=config.target_player,
            source=chat_msg.platform,
            user=chat_msg.display_name,
            params=parsed.params if parsed.params else None,
        )

        # Apply cooldown
        cooldowns.apply_cooldown(
            parsed.action, user=chat_msg.username, platform=chat_msg.platform
        )

        # Log what would happen
        logger.info("[EVENT] Action: %s", request.action)
        logger.info("[TARGET] %s", request.target)
        logger.info("[MODE] TEST — Minecraft action NOT executed")

    twitch_platform = None
    if twitch_config.enabled:
        twitch_platform = TwitchPlatform(twitch_config)
        twitch_platform.set_on_message(_on_test_message)
        twitch_platform.start()
        logger.info("[INFO] Twitch test mode started — listening for real messages")
        logger.info("[INFO] Press CTRL+C to stop")
    else:
        logger.error("[ERROR] Twitch is disabled in config. Enable it first.")
        sys.exit(1)

    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if twitch_platform:
            twitch_platform.stop()

    logger.info("[INFO] Twitch test mode stopped.")
    sys.exit(0)


def run_check_minecraft(config_path: str | None) -> None:
    """Diagnose Minecraft Core connection: TCP, protocol, auth."""
    import socket as _socket

    setup_logging(False)
    config = load_config(config_path)

    print()
    print("ChatControl Minecraft Core Diagnostic")
    print("=" * 50)

    host = config.host
    port = config.port
    token = config.auth_token
    timeout = config.request_timeout

    print()
    print("[STEP] Configuration")
    print("-" * 50)
    print(f"  Host:              {host}")
    print(f"  Port:              {port}")
    print(f"  Auth configured:   {'yes' if token else 'no (disabled)'}")
    print(f"  Timeout:           {timeout}s")
    print(f"  Target player:     {config.target_player}")

    print()
    print("[STEP] DNS Resolution")
    print("-" * 50)
    try:
        ip = _socket.getaddrinfo(host, port)[0][4][0]
        print(f"  [OK] {host} -> {ip}")
    except _socket.gaierror as e:
        print(f"  [FAIL] Cannot resolve {host}: {e}")
        print()
        print("=" * 50)
        print("  Minecraft Core is NOT reachable")
        print("=" * 50)
        print()
        return

    print()
    print("[STEP] TCP Connection")
    print("-" * 50)
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        print(f"  [OK] Connected to {host}:{port}")
    except _socket.timeout:
        print(f"  [FAIL] Connection timed out after {timeout}s")
        print(f"         Host {host}:{port} is not responding")
        print()
        print("=" * 50)
        print("  Minecraft Core is NOT reachable")
        print("=" * 50)
        print()
        return
    except ConnectionRefusedError:
        print(f"  [FAIL] Connection refused")
        print(f"         No service listening on {host}:{port}")
        print()
        print("=" * 50)
        print("  Minecraft Core is NOT reachable")
        print("=" * 50)
        print()
        return
    except OSError as e:
        print(f"  [FAIL] Connection error: {e}")
        print()
        print("=" * 50)
        print("  Minecraft Core is NOT reachable")
        print("=" * 50)
        print()
        return

    print()
    print("[STEP] Protocol Version")
    print("-" * 50)
    from core.models import PROTOCOL_VERSION
    print(f"  [OK] Bridge protocol version: {PROTOCOL_VERSION}")

    print()
    print("[STEP] Authentication")
    print("-" * 50)
    if not token:
        print("  [OK] Authentication disabled (no token configured)")
        print("       Skipping auth handshake")
    else:
        from core.protocol import serialize_auth_request, deserialize_auth_response
        try:
            auth_msg = serialize_auth_request(token) + "\n"
            sock.sendall(auth_msg.encode("utf-8"))

            response = b""
            while b"\n" not in response:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            if not response:
                print("  [FAIL] Connection closed by Core during auth")
                sock.close()
                print()
                print("=" * 50)
                print("  Minecraft Core is NOT ready")
                print("=" * 50)
                print()
                return

            raw = response.decode("utf-8").strip()
            auth_resp = deserialize_auth_response(raw)

            if auth_resp.get("success"):
                print("  [OK] Authentication successful")
            else:
                error = auth_resp.get("error", "UNKNOWN")
                message = auth_resp.get("message", "Unknown error")
                if error == "UNAUTHORIZED":
                    print(f"  [FAIL] Authentication failed: Invalid token")
                    print(f"         Core rejected the token")
                elif error == "INVALID_PROTOCOL":
                    print(f"  [FAIL] Protocol mismatch: {message}")
                    print(f"         Bridge v{PROTOCOL_VERSION} vs Core")
                else:
                    print(f"  [FAIL] Authentication error: {error}")
                    print(f"         {message}")
                sock.close()
                print()
                print("=" * 50)
                print("  Minecraft Core is NOT ready")
                print("=" * 50)
                print()
                return
        except Exception as e:
            print(f"  [FAIL] Auth handshake error: {e}")
            sock.close()
            print()
            print("=" * 50)
            print("  Minecraft Core is NOT ready")
            print("=" * 50)
            print()
            return

    sock.close()

    print()
    print("[STEP] Core Ready")
    print("-" * 50)
    print("  [OK] Core connection verified")

    print()
    print("=" * 50)
    print("  Minecraft Core is READY")
    print("=" * 50)
    print()
    print("  Next steps:")
    print("  1. Start Minecraft server with ChatControl mod")
    print("  2. Ensure a player named '{}' is online".format(config.target_player))
    print("  3. Start the Bridge: python main.py")
    print()


def run_simulate_stream(config_path: str | None, scenario_path: str | None, verbose: bool) -> None:
    """Full stream simulation: TwitchMock → Bridge → CoreMock."""
    from mocks.core_mock import CoreMock
    from mocks.twitch_mock import TwitchMock, load_scenario_yaml, SimScenario, SimMessage

    setup_logging(verbose)
    config = load_config(config_path)

    parser = CommandParser(
        prefix=config.command_prefix,
        event_number_map=config.get_event_number_map(),
    )
    cooldowns = CooldownManager(config.get_all_cooldowns())

    mock_port = 19876
    mock = CoreMock(
        port=mock_port,
        auth_token=config.auth_token or "SIM_TOKEN",
        auth_enabled=True,
    )
    config._data["minecraft"]["port"] = mock_port
    config._data["minecraft"]["auth_token"] = config.auth_token or "SIM_TOKEN"

    mock.start()
    time.sleep(0.2)

    mc_client = MinecraftClient(config)
    mc_client.connect()
    if not mc_client.authenticate():
        logger.error("[SIM] Authentication failed")
        mock.stop()
        return

    pipeline = ChatPipeline(
        parser=parser,
        cooldowns=cooldowns,
        target_player=config.target_player,
    )

    stats = {
        "messages": 0,
        "commands_detected": 0,
        "commands_ignored": 0,
        "actions_sent": 0,
        "cooldown_blocked": 0,
        "core_errors": 0,
        "auth_failures": 0,
    }

    def on_message(chat_msg: ChatMessage) -> None:
        stats["messages"] += 1
        logger.info("[TWITCH] %s: %s", chat_msg.display_name, chat_msg.message_text)

        parsed = parser.parse(chat_msg.message_text)
        if parsed is None:
            stats["commands_ignored"] += 1
            logger.info("[PARSE] ignored (not a command)")
            return

        if not parsed.valid:
            stats["commands_ignored"] += 1
            logger.info("[PARSE] invalid: %s", parsed.error)
            return

        stats["commands_detected"] += 1
        logger.info("[PARSE] action=%s", parsed.action)

        if cooldowns.is_on_cooldown(parsed.action, user=chat_msg.username, platform=chat_msg.platform):
            stats["cooldown_blocked"] += 1
            remaining = cooldowns.get_remaining(parsed.action, user=chat_msg.username, platform=chat_msg.platform)
            logger.info("[COOLDOWN] BLOCKED (%.1fs remaining)", remaining)
            return

        logger.info("[COOLDOWN] allowed")

        request = pipeline.process(chat_msg)
        if request is None:
            stats["commands_ignored"] += 1
            return

        logger.info("[BRIDGE] sending %s to Core", request.action)
        response = mc_client.send_and_wait(request)
        if response.success:
            stats["actions_sent"] += 1
            logger.info("[CORE] %s -> SUCCESS", request.action)
        else:
            stats["core_errors"] += 1
            logger.info("[CORE] %s -> ERROR: %s", request.action, response.error)

    twitch_mock = TwitchMock(on_message=on_message)

    print()
    print("=" * 50)
    print("  CHATCONTROL STREAM SIMULATION")
    print("=" * 50)
    print()

    if scenario_path:
        logger.info("[SIM] Loading scenario: %s", scenario_path)
        if scenario_path.endswith(".yaml") or scenario_path.endswith(".yml"):
            scenario = load_scenario_yaml(scenario_path)
        else:
            from mocks.twitch_mock import load_scenario_pipe
            scenario = load_scenario_pipe(scenario_path)
        logger.info("[SIM] Running scenario: %s (%d messages)", scenario.name, len(scenario.messages))
        twitch_mock.run_scenario(scenario, delay=0.05)
    else:
        logger.info("[SIM] Interactive mode. Type messages as 'user: text'")
        logger.info("[SIM] Type 'quit' to stop.")
        try:
            while True:
                try:
                    line = input("chat> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if line.lower() in ("quit", "exit", "q"):
                    break
                if not line:
                    continue
                parts = line.split(":", 1)
                if len(parts) == 2:
                    user = parts[0].strip()
                    text = parts[1].strip()
                else:
                    user = "Viewer"
                    text = line
                twitch_mock.inject(user, text)
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass

    mc_client.disconnect()
    mock.stop()

    print()
    print("-" * 50)
    print("  SIMULATION SUMMARY")
    print("-" * 50)
    print(f"  Messages processed:      {stats['messages']}")
    print(f"  Commands detected:       {stats['commands_detected']}")
    print(f"  Commands ignored:        {stats['commands_ignored']}")
    print(f"  Actions sent:            {stats['actions_sent']}")
    print(f"  Cooldown blocked:        {stats['cooldown_blocked']}")
    print(f"  Core errors:             {stats['core_errors']}")
    print(f"  Auth failures:           {stats['auth_failures']}")
    print("-" * 50)
    passed = stats["actions_sent"] > 0 and stats["auth_failures"] == 0
    print(f"  Simulation:              {'PASSED' if passed else 'FAILED'}")
    print("=" * 50)
    print()


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="ChatControl Bridge")
    arg_parser.add_argument("-c", "--config", default=None, help="Path to config.yaml")
    arg_parser.add_argument("--mock", action="store_true", help="Run in mock mode (no Minecraft)")
    arg_parser.add_argument("--check-twitch", action="store_true", help="Run Twitch diagnostics")
    arg_parser.add_argument("--twitch-login", action="store_true", help="Authorize Twitch account via OAuth")
    arg_parser.add_argument("--twitch-test", action="store_true", help="Test Twitch connection (no Minecraft)")
    arg_parser.add_argument("--simulate-stream", action="store_true", help="Run full stream simulation with CoreMock")
    arg_parser.add_argument("--check-minecraft", action="store_true", help="Diagnose Minecraft Core connection")
    arg_parser.add_argument("--scenario", default=None, help="Path to scenario YAML file for simulation")
    arg_parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = arg_parser.parse_args()

    if args.twitch_login:
        run_twitch_login(args.config)
        sys.exit(0)

    if args.check_twitch:
        run_check_twitch(args.config)
        sys.exit(0)

    if args.twitch_test:
        setup_logging(args.verbose)
        config = load_config(args.config)
        twitch_config = TwitchConfig.from_dict(config._data)
        parser = CommandParser(
            prefix=config.command_prefix,
            event_number_map=config.get_event_number_map(),
        )
        cooldowns = CooldownManager(config.get_all_cooldowns())
        run_twitch_test_loop(parser, cooldowns, config, twitch_config)

    if args.simulate_stream:
        run_simulate_stream(args.config, args.scenario, args.verbose)
        sys.exit(0)

    if args.check_minecraft:
        run_check_minecraft(args.config)
        sys.exit(0)

    run_bridge(args.config, args.mock, args.verbose)


if __name__ == "__main__":
    main()
