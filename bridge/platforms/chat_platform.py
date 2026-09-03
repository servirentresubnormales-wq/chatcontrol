from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from platforms.models import ChatMessage


class ChatPlatform(ABC):
    """Abstract base class for chat platform integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform identifier (e.g. 'twitch')."""
        ...

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Whether the platform connection is active."""
        ...

    @abstractmethod
    def start(self) -> None:
        """Start the platform connection."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the platform connection."""
        ...

    @abstractmethod
    def set_on_message(self, callback: Callable[[ChatMessage], None]) -> None:
        """Set the callback for incoming chat messages."""
        ...
