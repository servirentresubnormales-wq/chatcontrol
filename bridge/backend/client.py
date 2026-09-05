"""HTTP client for ChatControl Backend API."""
from __future__ import annotations
import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)

class BackendClient:
    """Client for ChatControl Backend HTTP API."""
    
    def __init__(self, base_url: str, bridge_token: str, timeout: int = 5):
        self._base_url = base_url.rstrip("/")
        self._bridge_token = bridge_token
        self._timeout = timeout
    
    def complete_link(self, twitch_user_id: str, link_code: str, 
                      bridge_instance_id: str) -> dict[str, Any]:
        """POST /api/link/complete - Complete a link code."""
        url = f"{self._base_url}/api/link/complete"
        payload = {
            "twitch_user_id": twitch_user_id,
            "bridge_token": self._bridge_token,
            "link_code": link_code,
            "bridge_instance_id": bridge_instance_id,
        }
        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            return resp.json()
        except requests.RequestException as e:
            logger.error("[BACKEND] HTTP error: %s", e)
            return {"error": f"HTTP error: {e}"}
    
    def heartbeat(self, twitch_user_id: str, bridge_instance_id: str,
                  minecraft_connected: bool) -> dict[str, Any]:
        """POST /api/bridge/heartbeat - Send heartbeat."""
        url = f"{self._base_url}/api/bridge/heartbeat"
        payload = {
            "twitch_user_id": twitch_user_id,
            "bridge_token": self._bridge_token,
            "bridge_instance_id": bridge_instance_id,
            "minecraft_connected": minecraft_connected,
        }
        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            return resp.json()
        except requests.RequestException as e:
            logger.error("[BACKEND] Heartbeat error: %s", e)
            return {"error": f"Heartbeat error: {e}"}
    
    def revoke_link(self, twitch_user_id: str) -> dict[str, Any]:
        """POST /api/link/revoke-bridge - Revoke link (called from Core unlink flow)."""
        url = f"{self._base_url}/api/link/revoke-bridge"
        payload = {
            "twitch_user_id": twitch_user_id,
            "bridge_token": self._bridge_token,
        }
        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            return resp.json()
        except requests.RequestException as e:
            logger.error("[BACKEND] Revoke link error: %s", e)
            return {"error": f"HTTP error: {e}"}
