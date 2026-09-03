from __future__ import annotations

import uuid
from typing import Any

from core.models import BridgeRequest


def build_action(
    action: str,
    target: str | None = None,
    source: str | None = "bridge",
    user: str | None = None,
    params: dict[str, Any] | None = None,
    message_id: str | None = None,
    auth_token: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BridgeRequest:
    return BridgeRequest(
        action=action,
        target=target,
        source=source,
        user=user,
        params=params or {},
        message_id=message_id or uuid.uuid4().hex,
        auth_token=auth_token,
        metadata=metadata,
    )


ACTION_PARAM_DEFAULTS: dict[str, dict[str, Any]] = {
    "zombie": {"radius": 4},
    "spiders": {"amount": 4, "radius": 5},
    "slowness": {"duration": 200, "amplifier": 1},
    "blindness": {"duration": 160, "amplifier": 0},
    "creeper": {"radius": 4},
    "storm": {"duration": 600, "thunder": True},
    "randomtp": {"radius": 30, "max-attempts": 20},
    "explosion": {"radius": 3.0, "fire": False, "destroy-blocks": False},
    "random": {},
    "chickens": {"amount": 1, "radius": 4},
    "give_item": {"item": "minecraft:diamond", "count": 1},
    "summon_mob": {"mob": "minecraft:zombie", "count": 1},
    "apply_effect": {"effect": "minecraft:speed", "duration": 200, "amplifier": 0},
}


def build_action_with_defaults(
    action: str,
    target: str | None = None,
    source: str | None = "bridge",
    user: str | None = None,
    overrides: dict[str, Any] | None = None,
    **kwargs: Any,
) -> BridgeRequest:
    base_params = ACTION_PARAM_DEFAULTS.get(action, {}).copy()
    if overrides:
        base_params.update(overrides)
    base_params.update(kwargs)
    return build_action(
        action=action,
        target=target,
        source=source,
        user=user,
        params=base_params if base_params else None,
    )
