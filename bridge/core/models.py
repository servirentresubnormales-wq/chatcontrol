from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


PROTOCOL_VERSION = 1


@dataclass
class BridgeRequest:
    action: str
    target: str | None = None
    source: str | None = None
    user: str | None = None
    params: dict[str, Any] | None = None
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    protocol_version: int = PROTOCOL_VERSION
    auth_token: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "action": self.action,
            "protocol_version": self.protocol_version,
            "message_id": self.message_id,
        }
        if self.target is not None:
            d["target"] = self.target
        if self.source is not None:
            d["source"] = self.source
        if self.user is not None:
            d["user"] = self.user
        if self.params:
            d["params"] = self.params
        if self.auth_token is not None:
            d["auth_token"] = self.auth_token
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BridgeRequest:
        target = data.get("target") or data.get("player")
        return cls(
            action=data.get("action", ""),
            target=target,
            source=data.get("source"),
            user=data.get("user"),
            params=data.get("params"),
            message_id=data.get("message_id", uuid.uuid4().hex),
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
            auth_token=data.get("auth_token"),
            metadata=data.get("metadata"),
        )


@dataclass
class BridgeResponse:
    success: bool
    action: str | None = None
    target: str | None = None
    source: str | None = None
    user: str | None = None
    message: str = ""
    error: str | None = None
    execution_time_ms: int | None = None
    protocol_version: int = PROTOCOL_VERSION
    message_id: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
            "protocol_version": self.protocol_version,
        }
        if self.action is not None:
            d["action"] = self.action
        if self.target is not None:
            d["target"] = self.target
        if self.source is not None:
            d["source"] = self.source
        if self.user is not None:
            d["user"] = self.user
        if self.error is not None:
            d["error"] = self.error
        if self.execution_time_ms is not None:
            d["execution_time_ms"] = self.execution_time_ms
        if self.message_id is not None:
            d["message_id"] = self.message_id
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BridgeResponse:
        return cls(
            success=data.get("success", False),
            action=data.get("action"),
            target=data.get("target"),
            source=data.get("source"),
            user=data.get("user"),
            message=data.get("message", ""),
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms"),
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
            message_id=data.get("message_id"),
            metadata=data.get("metadata"),
        )
