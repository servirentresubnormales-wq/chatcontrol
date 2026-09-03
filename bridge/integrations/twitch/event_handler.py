from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any

from platforms.models import ChatMessage

logger = logging.getLogger(__name__)


class MessageDeduplicator:
    """Tracks processed message IDs to prevent duplicate processing.

    Thread-safe implementation using a lock for concurrent access.
    Uses OrderedDict for O(1) lookup and ordered eviction.
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 600) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._messages: OrderedDict[str, float] = OrderedDict()
        self._lock: Any = None
        self._init_lock()

    def _init_lock(self) -> None:
        import threading
        self._lock = threading.Lock()

    def is_duplicate(self, message_id: str) -> bool:
        if not message_id:
            return False

        with self._lock:
            self._cleanup()

            if message_id in self._messages:
                logger.debug("[DEDUP] Duplicate message: %s", message_id)
                return True

            self._messages[message_id] = time.monotonic()
            return False

    def _cleanup(self) -> None:
        now = time.monotonic()
        while self._messages:
            msg_id, ts = next(iter(self._messages.items()))
            if now - ts > self._ttl:
                self._messages.popitem(last=False)
            else:
                break

        while len(self._messages) > self._max_size:
            self._messages.popitem(last=False)


def _extract_badges(raw_badges: list[dict[str, Any]]) -> dict[str, bool]:
    """Extract role flags from Twitch badge objects.

    Badge objects from channel.chat.message event have format:
    {"set_id": "moderator", "id": "1", "info": ""}

    Returns dict with is_broadcaster, is_moderator, is_vip, is_subscriber, etc.
    """
    badge_sets = {b.get("set_id", "") for b in raw_badges if isinstance(b, dict)}

    return {
        "is_broadcaster": "broadcaster" in badge_sets,
        "is_moderator": "moderator" in badge_sets,
        "is_vip": "vip" in badge_sets,
        "is_subscriber": "subscriber" in badge_sets,
        "is_artist": "artist" in badge_sets,
        "is_turbo": "turbo" in badge_sets,
        "is_premium": "premium" in badge_sets,
        "badge_count": len(raw_badges),
    }


class TwitchEventHandler:
    """Processes raw Twitch EventSub events into ChatMessage objects.

    Handles channel.chat.message events and extracts:
    - User identity (chatter_user_id, chatter_user_name, chatter_user_login)
    - Message content (message.text, message.fragments)
    - Badges/roles (broadcaster, moderator, vip, subscriber)
    - Color (hex color of chatter name)
    - Shared chat source info (if applicable)
    """

    def __init__(self) -> None:
        self._deduplicator = MessageDeduplicator()

    def handle_notification(
        self, subscription_type: str, event: dict[str, Any]
    ) -> ChatMessage | None:
        if subscription_type != "channel.chat.message":
            logger.debug("[TWITCH] Ignoring event type: %s", subscription_type)
            return None

        message_id = event.get("message_id", "")
        if self._deduplicator.is_duplicate(message_id):
            return None

        message_text = ""
        message_fragments = []
        message_data = event.get("message")
        if isinstance(message_data, dict):
            message_text = message_data.get("text", "")
            message_fragments = message_data.get("fragments", [])
        elif isinstance(message_data, str):
            message_text = message_data

        if not message_text:
            return None

        chatter_user_id = event.get("chatter_user_id", "")
        chatter_user_name = event.get("chatter_user_name", "")
        chatter_user_login = event.get("chatter_user_login", "")
        broadcaster_user_id = event.get("broadcaster_user_id", "")
        broadcaster_user_name = event.get("broadcaster_user_name", "")
        broadcaster_user_login = event.get("broadcaster_user_login", "")
        color = event.get("color", "")
        raw_badges = event.get("badges", [])
        message_type = event.get("message_type", "")
        cheer = event.get("cheer")
        reply = event.get("reply")
        channel_points_custom_reward_id = event.get("channel_points_custom_reward_id")

        badges = _extract_badges(raw_badges)

        source_broadcaster_id = event.get("source_broadcaster_user_id")
        source_broadcaster_login = event.get("source_broadcaster_user_login")

        msg = ChatMessage(
            platform="twitch",
            user_id=chatter_user_id,
            username=chatter_user_login or chatter_user_name,
            display_name=chatter_user_name or chatter_user_login,
            message_id=message_id,
            message_text=message_text,
            channel_id=broadcaster_user_id,
            channel_name=broadcaster_user_name,
            raw_metadata={
                "badges": raw_badges,
                "badges_flags": badges,
                "color": color,
                "message_type": message_type,
                "broadcaster_user_login": broadcaster_user_login,
                "cheer": cheer,
                "reply": reply,
                "channel_points_custom_reward_id": channel_points_custom_reward_id,
                "fragments": message_fragments,
                "source_broadcaster_user_id": source_broadcaster_id,
                "source_broadcaster_user_login": source_broadcaster_login,
            },
        )

        badge_str = ", ".join(
            k.replace("is_", "") for k, v in badges.items()
            if v and k.startswith("is_")
        )
        badge_info = f" [{badge_str}]" if badge_str else ""

        logger.info(
            "[INFO] Chat message from %s%s: %s",
            msg.display_name,
            badge_info,
            msg.message_text[:50],
        )
        return msg
