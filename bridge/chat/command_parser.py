from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


EVENT_NUMBER_MAP: dict[str, str] = {
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
}


COMMAND_MAP: dict[str, str] = {
    "zombie": "zombie",
    "spiders": "spiders",
    "slowness": "slowness",
    "blindness": "blindness",
    "creeper": "creeper",
    "storm": "storm",
    "randomtp": "random_teleport",
    "randomtp2": "random_teleport",
    "explosion": "explosion",
    "boom": "explosion",
    "random": "random_event",
    "randomevent": "random_event",
    "pollos": "chickens",
    "chickens": "chickens",
    "pollo": "chickens",
    "give": "give_item",
    "item": "give_item",
    "summon": "summon_mob",
    "mob": "summon_mob",
    "effect": "apply_effect",
    "efecto": "apply_effect",
}


@dataclass
class ParsedCommand:
    command: str
    action: str
    raw_args: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    valid: bool = True
    error: str | None = None


class CommandParser:
    def __init__(
        self,
        prefix: str = "!",
        command_map: dict[str, str] | None = None,
        event_number_map: dict[str, str] | None = None,
    ) -> None:
        self._prefix = prefix
        self._command_map = command_map if command_map is not None else COMMAND_MAP.copy()
        self._event_number_map = event_number_map if event_number_map is not None else EVENT_NUMBER_MAP.copy()

    @property
    def prefix(self) -> str:
        return self._prefix

    def parse(self, text: str) -> ParsedCommand | None:
        text = text.strip()
        if not text:
            return None

        if text in self._event_number_map:
            action = self._event_number_map[text]
            return ParsedCommand(
                command=text,
                action=action,
                raw_args="",
                params={},
                valid=True,
            )

        if not text.startswith(self._prefix):
            return None

        without_prefix = text[len(self._prefix):]
        parts = without_prefix.split(None, 1)
        if not parts:
            return None

        command_name = parts[0].lower()
        raw_args = parts[1] if len(parts) > 1 else ""

        action = self._command_map.get(command_name)
        if action is None:
            return ParsedCommand(
                command=command_name,
                action="",
                raw_args=raw_args,
                valid=False,
                error=f"Unknown command: {command_name}",
            )

        params = self._parse_args(action, raw_args)

        return ParsedCommand(
            command=command_name,
            action=action,
            raw_args=raw_args,
            params=params,
            valid=True,
        )

    def _parse_args(self, action: str, raw_args: str) -> dict[str, Any]:
        if not raw_args.strip():
            return {}

        params: dict[str, Any] = {}
        tokens = raw_args.split()

        if action in ("slowness", "blindness", "apply_effect"):
            if len(tokens) >= 1:
                try:
                    params["duration"] = int(tokens[0])
                except ValueError:
                    pass
            if len(tokens) >= 2:
                try:
                    params["amplifier"] = int(tokens[1])
                except ValueError:
                    pass

        elif action in ("zombie", "creeper", "explosion"):
            if len(tokens) >= 1:
                try:
                    params["radius"] = float(tokens[0])
                except ValueError:
                    pass

        elif action in ("spiders", "chickens"):
            if len(tokens) >= 1:
                try:
                    params["amount"] = int(tokens[0])
                except ValueError:
                    pass
            if len(tokens) >= 2:
                try:
                    params["radius"] = int(tokens[1])
                except ValueError:
                    pass

        elif action == "storm":
            if len(tokens) >= 1:
                try:
                    params["duration"] = int(tokens[0])
                except ValueError:
                    pass
            if len(tokens) >= 2:
                params["thunder"] = tokens[1].lower() in ("true", "1", "yes", "si", "sí")

        elif action == "random_teleport":
            if len(tokens) >= 1:
                try:
                    params["radius"] = int(tokens[0])
                except ValueError:
                    pass

        return params

    def register_command(self, command_name: str, action: str) -> None:
        self._command_map[command_name.lower()] = action

    def get_available_commands(self) -> list[str]:
        commands = set(self._command_map.keys())
        commands.update(self._event_number_map.keys())
        return sorted(commands)

    def get_action_for_command(self, command_name: str) -> str | None:
        if command_name in self._event_number_map:
            return self._event_number_map[command_name]
        return self._command_map.get(command_name.lower())
