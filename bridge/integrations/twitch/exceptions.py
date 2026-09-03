from __future__ import annotations


class TwitchError(Exception):
    """Base exception for Twitch integration errors."""
    pass


class TwitchAuthError(TwitchError):
    """Authentication with Twitch API failed."""
    pass


class TwitchConnectionError(TwitchError):
    """WebSocket connection to Twitch EventSub failed."""
    pass


class TwitchSubscriptionError(TwitchError):
    """EventSub subscription creation failed."""
    pass


class TwitchEventError(TwitchError):
    """Error processing a Twitch event."""
    pass
