from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from platforms.models import ChatMessage

logger = logging.getLogger(__name__)


@dataclass
class SimMessage:
    user: str
    text: str
    message_id: str = ""
    delay: float = 0.0

    def __post_init__(self) -> None:
        if not self.message_id:
            self.message_id = uuid.uuid4().hex


@dataclass
class SimScenario:
    name: str = "unnamed"
    messages: list[SimMessage] = field(default_factory=list)


def load_scenario_yaml(path: str) -> SimScenario:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    name = data.get("name", "unnamed")
    messages = []
    for msg_data in data.get("messages", []):
        messages.append(SimMessage(
            user=msg_data.get("user", "Viewer"),
            text=str(msg_data.get("text", "")),
            message_id=msg_data.get("message_id", ""),
            delay=float(msg_data.get("delay", 0.0)),
        ))
    return SimScenario(name=name, messages=messages)


def load_scenario_pipe(path: str) -> SimScenario:
    messages = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                user = parts[0].strip()
                text = parts[1].strip()
            else:
                user = "Viewer"
                text = parts[0].strip()
            messages.append(SimMessage(user=user, text=text, message_id=f"pipe-{line_no}"))
    return SimScenario(name="pipe", messages=messages)


class TwitchMock:
    def __init__(self, on_message: Callable[[ChatMessage], None] | None = None) -> None:
        self._on_message = on_message
        self._messages_sent = 0

    @property
    def messages_sent(self) -> int:
        return self._messages_sent

    def set_on_message(self, callback: Callable[[ChatMessage], None]) -> None:
        self._on_message = callback

    def inject(self, user: str, text: str, message_id: str | None = None) -> ChatMessage:
        msg = ChatMessage(
            platform="twitch",
            user_id=f"sim-{user.lower()}",
            username=user.lower(),
            display_name=user,
            message_id=message_id or uuid.uuid4().hex,
            message_text=text,
            channel_id="sim-channel",
            channel_name="SimChannel",
        )
        self._messages_sent += 1
        if self._on_message:
            self._on_message(msg)
        return msg

    def run_scenario(self, scenario: SimScenario, delay: float = 0.0) -> list[ChatMessage]:
        results = []
        for sim_msg in scenario.messages:
            if sim_msg.delay > 0:
                time.sleep(sim_msg.delay)
            elif delay > 0:
                time.sleep(delay)
            msg = self.inject(sim_msg.user, sim_msg.text, sim_msg.message_id)
            results.append(msg)
        return results

    def run_messages(self, messages: list[tuple[str, str]], delay: float = 0.0) -> list[ChatMessage]:
        results = []
        for user, text in messages:
            if delay > 0:
                time.sleep(delay)
            msg = self.inject(user, text)
            results.append(msg)
        return results
