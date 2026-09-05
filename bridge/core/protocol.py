from __future__ import annotations

import hmac
import json
import logging
from typing import Any

from core.exceptions import ProtocolError
from core.models import PROTOCOL_VERSION, BridgeRequest, BridgeResponse

logger = logging.getLogger(__name__)


def serialize_request(request: BridgeRequest) -> str:
    return json.dumps(request.to_dict(), ensure_ascii=False)


def deserialize_response(raw: str) -> BridgeResponse:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Invalid JSON response: {e}") from e

    if not isinstance(data, dict):
        raise ProtocolError(f"Expected JSON object, got {type(data).__name__}")

    return BridgeResponse.from_dict(data)


def validate_request(request: BridgeRequest) -> list[str]:
    errors: list[str] = []
    if not request.action:
        errors.append("Missing required field: action")
    if request.protocol_version != PROTOCOL_VERSION:
        errors.append(
            f"Unsupported protocol_version: {request.protocol_version} "
            f"(expected {PROTOCOL_VERSION})"
        )
    return errors


def validate_response_fields(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "success" not in data:
        errors.append("Missing required field: success")
    if "message" not in data:
        errors.append("Missing required field: message")
    return errors


def serialize_auth_request(token: str) -> str:
    return json.dumps({
        "type": "auth",
        "token": token,
        "protocol_version": PROTOCOL_VERSION,
    }, ensure_ascii=False)


def deserialize_auth_response(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Invalid JSON auth response: {e}") from e

    if not isinstance(data, dict):
        raise ProtocolError(f"Expected JSON object, got {type(data).__name__}")

    if data.get("type") != "auth":
        raise ProtocolError(f"Expected auth response, got type: {data.get('type')}")

    return data


def compare_tokens(expected: str, actual: str) -> bool:
    return hmac.compare_digest(expected.encode("utf-8"), actual.encode("utf-8"))


def deserialize_link_request(raw: str) -> dict[str, Any]:
    """Deserialize a link_request message from Core."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Invalid JSON link request: {e}") from e
    if not isinstance(data, dict):
        raise ProtocolError(f"Expected JSON object, got {type(data).__name__}")
    if data.get("type") != "link_request":
        raise ProtocolError(f"Expected link_request, got type: {data.get('type')}")
    return data

def deserialize_unlink_request(raw: str) -> dict[str, Any]:
    """Deserialize an unlink_request message from Core."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Invalid JSON unlink request: {e}") from e
    if not isinstance(data, dict):
        raise ProtocolError(f"Expected JSON object, got {type(data).__name__}")
    if data.get("type") != "unlink_request":
        raise ProtocolError(f"Expected unlink_request, got type: {data.get('type')}")
    return data

def serialize_link_response(message_id: str, success: bool, message: str) -> str:
    """Serialize a link_response message to Core."""
    return json.dumps({
        "type": "link_response",
        "message_id": message_id,
        "success": success,
        "message": message,
        "protocol_version": PROTOCOL_VERSION,
    }, ensure_ascii=False)
