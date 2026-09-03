from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    """Normalized chat message from any platform."""
    platform: str
    user_id: str
    username: str
    display_name: str
    message_id: str
    message_text: str
    channel_id: str
    channel_name: str
    timestamp: str = ""
    raw_metadata: dict[str, Any] = field(default_factory=dict)
