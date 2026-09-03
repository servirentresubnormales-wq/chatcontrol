from __future__ import annotations

import logging
from typing import Callable

from platforms.models import ChatMessage
from chat.command_parser import CommandParser
from cooldowns.manager import CooldownManager
from minecraft.command_builder import build_action
from core.models import BridgeRequest

logger = logging.getLogger(__name__)


class ChatPipeline:
    """Platform-independent pipeline: ChatMessage → Command → Cooldown → Request."""

    def __init__(
        self,
        parser: CommandParser,
        cooldowns: CooldownManager,
        target_player: str,
        on_request: Callable[[BridgeRequest], None] | None = None,
    ) -> None:
        self._parser = parser
        self._cooldowns = cooldowns
        self._target_player = target_player
        self._on_request = on_request

    def process(self, message: ChatMessage) -> BridgeRequest | None:
        parsed = self._parser.parse(message.message_text)
        if parsed is None:
            return None

        if not parsed.valid:
            logger.warning("[WARNING] %s", parsed.error)
            return None

        if self._cooldowns.is_on_cooldown(
            parsed.action, user=message.username, platform=message.platform
        ):
            remaining = self._cooldowns.get_remaining(
                parsed.action, user=message.username, platform=message.platform
            )
            logger.warning(
                "[WARNING] Command '%s' from %s on cooldown (%.1fs remaining)",
                parsed.command,
                message.display_name,
                remaining,
            )
            return None

        request = build_action(
            action=parsed.action,
            target=self._target_player,
            source=message.platform,
            user=message.display_name,
            params=parsed.params if parsed.params else None,
        )

        self._cooldowns.apply_cooldown(
            parsed.action, user=message.username, platform=message.platform
        )

        if self._on_request:
            self._on_request(request)

        return request
