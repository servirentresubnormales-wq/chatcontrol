from __future__ import annotations

import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import json
from dataclasses import dataclass
from typing import Any

from integrations.twitch.config import TwitchConfig
from integrations.twitch.exceptions import TwitchAuthError

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Detailed token validation result."""
    valid: bool
    login: str = ""
    user_id: str = ""
    client_id: str = ""
    scopes: list[str] | None = None
    expires_in: int = 0
    error: str = ""

    @property
    def is_expired(self) -> bool:
        return self.valid and self.expires_in <= 0


class TwitchAuth:
    """Manages Twitch OAuth tokens for EventSub WebSocket.

    Two types of tokens:
    - User access token: Used for EventSub WebSocket (requires user:read:chat scope)
    - App access token: Used for webhook subscriptions (client credentials flow)

    For this project, we use a User Access Token because EventSub WebSocket
    requires a user access token, NOT an app access token.
    """

    VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
    AUTHORIZE_URL = "https://id.twitch.tv/oauth2/authorize"

    REQUIRED_SCOPES = ["user:read:chat"]

    def __init__(self, config: TwitchConfig) -> None:
        self._config = config
        self._access_token = config.access_token
        self._refresh_token = config.refresh_token
        self._expires_at: float = 0.0
        self._scopes: list[str] = []
        self._login: str = ""
        self._user_id: str = ""
        self._client_id: str = ""

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    @property
    def client_id(self) -> str:
        return self._client_id or self._config.client_id

    @property
    def login(self) -> str:
        return self._login

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def scopes(self) -> list[str]:
        return list(self._scopes)

    @property
    def is_valid(self) -> bool:
        if not self._access_token:
            return False
        if self._expires_at > 0 and time.time() >= self._expires_at:
            return False
        return True

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        """Build Twitch OAuth authorization URL.

        Per Twitch docs:
        - response_type=code (Authorization Code Flow)
        - client_id: Registered app client ID
        - redirect_uri: Registered redirect URI
        - scope: Space-delimited list (URL encoded)
        - state: Random string for CSRF protection
        """
        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.REQUIRED_SCOPES),
            "state": state,
            "force_verify": "true",
        }
        return f"{self.AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Per Twitch docs:
        POST https://id.twitch.tv/oauth2/token
        Body: client_id, client_secret, code, grant_type=authorization_code, redirect_uri

        Returns dict with: access_token, refresh_token, expires_in, scope, token_type
        """
        if not self._config.client_secret:
            raise TwitchAuthError("Missing client_secret for code exchange")

        data = urllib.parse.urlencode({
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }).encode("utf-8")

        req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._access_token = result.get("access_token", "")
                self._refresh_token = result.get("refresh_token", "")
                expires_in = result.get("expires_in", 0)
                self._expires_at = time.time() + expires_in - 60
                logger.info("[INFO] Twitch tokens obtained via code exchange")
                return result
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise TwitchAuthError(
                f"Code exchange failed: HTTP {e.code} - {body_text}"
            ) from e
        except (OSError, KeyError) as e:
            raise TwitchAuthError(f"Code exchange error: {e}") from e

    def refresh_access_token(self) -> dict[str, Any]:
        """Refresh the access token using the refresh token.

        Per Twitch docs:
        POST https://id.twitch.tv/oauth2/token
        Body: grant_type=refresh_token, refresh_token, client_id, client_secret

        Returns dict with: access_token, refresh_token, expires_in, scope, token_type
        """
        if not self._refresh_token:
            raise TwitchAuthError("No refresh token available")

        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
        }).encode("utf-8")

        req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._access_token = result.get("access_token", "")
                self._refresh_token = result.get("refresh_token", self._refresh_token)
                expires_in = result.get("expires_in", 0)
                self._expires_at = time.time() + expires_in - 60
                logger.info("[INFO] Twitch access token refreshed")
                return result
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise TwitchAuthError(
                f"Token refresh failed: HTTP {e.code} - {body_text}"
            ) from e
        except (OSError, KeyError) as e:
            raise TwitchAuthError(f"Token refresh error: {e}") from e

    def validate_token(self) -> TokenInfo:
        """Validate the access token against Twitch API.

        Returns TokenInfo with detailed validation results.
        Never logs the full token.
        """
        if not self._access_token:
            return TokenInfo(valid=False, error="No access token configured")

        req = urllib.request.Request(self.VALIDATE_URL)
        req.add_header("Authorization", f"OAuth {self._access_token}")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                self._login = data.get("login", "")
                self._user_id = data.get("user_id", "")
                self._client_id = data.get("client_id", "")
                self._scopes = data.get("scopes", [])
                expires_in = data.get("expires_in", 3600)
                self._expires_at = time.time() + expires_in - 60

                client_id_match = self._client_id == self._config.client_id

                missing_scopes = [
                    s for s in self.REQUIRED_SCOPES
                    if s not in self._scopes
                ]

                logger.info(
                    "[INFO] Twitch token validated (login=%s, user_id=%s, scopes=%d, client_id_match=%s)",
                    self._login, self._user_id, len(self._scopes), client_id_match,
                )

                if missing_scopes:
                    logger.warning(
                        "[WARNING] Missing required scopes: %s",
                        ", ".join(missing_scopes),
                    )

                if not client_id_match:
                    logger.warning(
                        "[WARNING] Client ID mismatch: token has '%s', config has '%s'",
                        self._client_id, self._config.client_id,
                    )

                return TokenInfo(
                    valid=True,
                    login=self._login,
                    user_id=self._user_id,
                    client_id=self._client_id,
                    scopes=list(self._scopes),
                    expires_in=expires_in,
                )

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("message", error_msg)
            except Exception:
                pass

            if e.code == 401:
                return TokenInfo(
                    valid=False,
                    error=f"Invalid or expired token: {error_msg}",
                )
            return TokenInfo(
                valid=False,
                error=f"Validation failed: {error_msg}",
            )
        except OSError as e:
            return TokenInfo(
                valid=False,
                error=f"Network error: {e}",
            )

    def get_app_token(self) -> str:
        """Get app access token using client credentials (for webhook subscriptions).

        NOTE: EventSub WebSocket requires a USER access token, not an app token.
        This method is provided for completeness but should not be used for
        EventSub WebSocket connections.
        """
        if not self._config.client_id or not self._config.client_secret:
            raise TwitchAuthError("Missing client_id or client_secret for app token")

        data = urllib.parse.urlencode({
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "grant_type": "client_credentials",
        }).encode("utf-8")

        req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                logger.info("[INFO] Twitch app token obtained")
                return result["access_token"]
        except urllib.error.HTTPError as e:
            raise TwitchAuthError(f"App token request failed: HTTP {e.code}") from e
        except (OSError, KeyError) as e:
            raise TwitchAuthError(f"App token error: {e}") from e

    def has_scope(self, scope: str) -> bool:
        return scope in self._scopes

    def has_all_required_scopes(self) -> tuple[bool, list[str]]:
        """Check if token has all required scopes for EventSub chat messages.

        Returns (has_all, missing_scopes).
        """
        missing = [s for s in self.REQUIRED_SCOPES if s not in self._scopes]
        return len(missing) == 0, missing

    def get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Client-Id": self._config.client_id,
            "Content-Type": "application/json",
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic information about the auth state.

        Never includes the full access token.
        """
        return {
            "has_token": bool(self._access_token),
            "token_prefix": self._access_token[:8] + "..." if self._access_token else "",
            "client_id": self._config.client_id,
            "client_id_set": bool(self._config.client_id),
            "login": self._login,
            "user_id": self._user_id,
            "scopes": list(self._scopes),
            "expires_in": max(0, int(self._expires_at - time.time())) if self._expires_at else 0,
            "is_valid": self.is_valid,
        }
