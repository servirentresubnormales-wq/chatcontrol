from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from core.exceptions import ConfigError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "minecraft": {
        "host": "127.0.0.1",
        "port": 8765,
        "auth_token": "",
    },
    "bridge": {
        "target_player": "Streamer",
        "reconnect_delay": 5,
        "request_timeout": 5,
    },
    "commands": {
        "prefix": "!",
        "cooldowns": {
            "zombie": 10,
            "spiders": 10,
            "slowness": 15,
            "blindness": 15,
            "creeper": 30,
            "storm": 60,
            "randomtp": 20,
            "explosion": 30,
            "random": 45,
            "chickens": 0,
            "give_item": 20,
            "summon_mob": 10,
            "apply_effect": 15,
        },
    },
    "twitch": {
        "enabled": False,
        "client_id": "",
        "client_secret": "",
        "access_token": "",
        "refresh_token": "",
        "broadcaster_id": "",
        "bot_user_id": "",
        "channel": "",
    },
    "events": {
        "1": "zombie",
        "2": "spiders",
        "3": "slowness",
        "4": "blindness",
        "5": "creeper",
        "6": "storm",
        "7": "random_teleport",
        "8": "explosion",
        "9": "random_event",
        "10": "chickens",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def host(self) -> str:
        return self._data["minecraft"]["host"]

    @property
    def port(self) -> int:
        return int(self._data["minecraft"]["port"])

    @property
    def auth_token(self) -> str:
        return self._data["minecraft"].get("auth_token", "")

    @property
    def target_player(self) -> str:
        return self._data["bridge"]["target_player"]

    @property
    def reconnect_delay(self) -> int:
        return int(self._data["bridge"]["reconnect_delay"])

    @property
    def request_timeout(self) -> int:
        return int(self._data["bridge"]["request_timeout"])

    @property
    def command_prefix(self) -> str:
        return self._data["commands"]["prefix"]

    def get_cooldown(self, action: str) -> int:
        return int(self._data["commands"]["cooldowns"].get(action, 0))

    def get_all_cooldowns(self) -> dict[str, int]:
        raw = self._data["commands"]["cooldowns"]
        return {k: int(v) for k, v in raw.items()}

    def get_event_number_map(self) -> dict[str, str]:
        return dict(self._data.get("events", {}))


def load_config(path: str | Path | None = None) -> Config:
    config_path = Path(path) if path else Path("config.yaml")

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {config_path}: {e}") from e
    else:
        logger.warning("Config file %s not found, using defaults", config_path)
        user_data = {}

    merged = _deep_merge(DEFAULT_CONFIG, user_data)
    return Config(merged)
