from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CooldownEntry:
    expires_at: float
    action: str
    key: str


class CooldownManager:
    NO_COOLDOWN_ACTIONS = {"chickens"}

    def __init__(self, default_cooldowns: dict[str, int] | None = None) -> None:
        self._cooldowns: dict[str, int] = default_cooldowns or {}
        self._active: dict[str, CooldownEntry] = {}
        self._custom_durations: dict[str, int] = {}
        self._lock = threading.Lock()

    def set_cooldown(self, action: str, seconds: int) -> None:
        with self._lock:
            self._cooldowns[action] = seconds

    def get_cooldown_duration(self, action: str) -> int:
        with self._lock:
            if action in self._custom_durations:
                return self._custom_durations[action]
            return self._cooldowns.get(action, 0)

    def set_custom_duration(self, action: str, seconds: int) -> None:
        with self._lock:
            self._custom_durations[action] = seconds

    def is_on_cooldown(self, action: str, user: str | None = None, platform: str | None = None) -> bool:
        if action in self.NO_COOLDOWN_ACTIONS:
            return False

        now = time.monotonic()
        key = self._make_key(action, user, platform)
        with self._lock:
            entry = self._active.get(key)
        return entry is not None and entry.expires_at > now

    def get_remaining(self, action: str, user: str | None = None, platform: str | None = None) -> float:
        if action in self.NO_COOLDOWN_ACTIONS:
            return 0.0

        now = time.monotonic()
        key = self._make_key(action, user, platform)
        with self._lock:
            entry = self._active.get(key)
        if entry and entry.expires_at > now:
            return entry.expires_at - now
        return 0.0

    def apply_cooldown(self, action: str, user: str | None = None, platform: str | None = None) -> None:
        if action in self.NO_COOLDOWN_ACTIONS:
            return

        duration = self.get_cooldown_duration(action)
        if duration <= 0:
            return

        now = time.monotonic()
        expires_at = now + duration

        key = self._make_key(action, user, platform)
        with self._lock:
            self._active[key] = CooldownEntry(
                expires_at=expires_at,
                action=action,
                key=key,
            )
        logger.debug(
            "[COOLDOWN] Applied %ds cooldown for %s (key=%s)",
            duration,
            action,
            key,
        )

    def clear_cooldown(self, action: str, user: str | None = None, platform: str | None = None) -> None:
        key = self._make_key(action, user, platform)
        with self._lock:
            self._active.pop(key, None)

    def clear_all(self) -> None:
        with self._lock:
            self._active.clear()

    def cleanup_expired(self) -> int:
        now = time.monotonic()
        with self._lock:
            expired = [k for k, v in self._active.items() if v.expires_at <= now]
            for k in expired:
                del self._active[k]
        return len(expired)

    @staticmethod
    def _make_key(action: str, user: str | None, platform: str | None) -> str:
        if user and platform:
            return f"action:{action}:user:{user}:platform:{platform}"
        if user:
            return f"action:{action}:user:{user}"
        if platform:
            return f"action:{action}:platform:{platform}"
        return f"action:{action}"
