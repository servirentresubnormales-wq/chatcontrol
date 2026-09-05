"""Bridge state management."""
from __future__ import annotations
import threading

class BridgeState:
    """Thread-safe bridge state."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._twitch_user_id: str | None = None
        self._bridge_token: str | None = None
        self._bridge_instance_id: str | None = None
        self._linked: bool = False
        self._minecraft_connected: bool = False
    
    @property
    def twitch_user_id(self) -> str | None:
        with self._lock:
            return self._twitch_user_id
    
    @twitch_user_id.setter
    def twitch_user_id(self, value: str):
        with self._lock:
            self._twitch_user_id = value
    
    @property
    def bridge_token(self) -> str | None:
        with self._lock:
            return self._bridge_token
    
    @bridge_token.setter
    def bridge_token(self, value: str):
        with self._lock:
            self._bridge_token = value
    
    @property
    def bridge_instance_id(self) -> str | None:
        with self._lock:
            return self._bridge_instance_id
    
    @bridge_instance_id.setter
    def bridge_instance_id(self, value: str):
        with self._lock:
            self._bridge_instance_id = value
    
    @property
    def linked(self) -> bool:
        with self._lock:
            return self._linked
    
    @linked.setter
    def linked(self, value: bool):
        with self._lock:
            self._linked = value
    
    @property
    def minecraft_connected(self) -> bool:
        with self._lock:
            return self._minecraft_connected
    
    @minecraft_connected.setter
    def minecraft_connected(self, value: bool):
        with self._lock:
            self._minecraft_connected = value
    
    def is_configured(self) -> bool:
        with self._lock:
            return bool(self._twitch_user_id and self._bridge_token)
