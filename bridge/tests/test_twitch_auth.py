import pytest
from unittest.mock import patch, MagicMock
from integrations.twitch.auth import TwitchAuth, TokenInfo
from integrations.twitch.config import TwitchConfig
from integrations.twitch.exceptions import TwitchAuthError


class TestTokenInfo:
    def test_valid_token(self):
        info = TokenInfo(valid=True, login="test", user_id="123", expires_in=3600)
        assert info.valid is True
        assert info.is_expired is False

    def test_expired_token(self):
        info = TokenInfo(valid=True, login="test", user_id="123", expires_in=-100)
        assert info.is_expired is True

    def test_invalid_token(self):
        info = TokenInfo(valid=False, error="bad token")
        assert info.valid is False
        assert info.is_expired is False


class TestTwitchAuth:
    def setup_method(self):
        self.config = TwitchConfig(
            enabled=True,
            client_id="test_client_id",
            client_secret="test_secret",
            access_token="test_token",
            broadcaster_id="12345",
            channel="TestChannel",
        )
        self.auth = TwitchAuth(self.config)

    def test_access_token(self):
        assert self.auth.access_token == "test_token"

    def test_client_id(self):
        assert self.auth.client_id == "test_client_id"

    def test_is_valid_with_token(self):
        assert self.auth.is_valid is True

    def test_is_valid_no_token(self):
        config = TwitchConfig(enabled=True, client_id="id")
        auth = TwitchAuth(config)
        assert auth.is_valid is False

    def test_is_valid_token_not_expired(self):
        import time
        config = TwitchConfig(enabled=True, client_id="id", access_token="tok")
        auth = TwitchAuth(config)
        auth._expires_at = time.time() + 3600
        assert auth.is_valid is True

    def test_is_valid_token_expired(self):
        import time
        config = TwitchConfig(enabled=True, client_id="id", access_token="tok")
        auth = TwitchAuth(config)
        auth._expires_at = time.time() - 100
        assert auth.is_valid is False

    def test_is_valid_token_not_validated(self):
        config = TwitchConfig(enabled=True, client_id="id", access_token="tok")
        auth = TwitchAuth(config)
        assert auth._expires_at == 0.0
        assert auth.is_valid is True

    def test_get_headers(self):
        headers = self.auth.get_headers()
        assert "Authorization" in headers
        assert "Bearer test_token" in headers["Authorization"]
        assert headers["Client-Id"] == "test_client_id"

    def test_has_scope(self):
        self.auth._scopes = ["user:read:chat", "user:read:follows"]
        assert self.auth.has_scope("user:read:chat") is True
        assert self.auth.has_scope("missing_scope") is False

    def test_has_all_required_scopes(self):
        self.auth._scopes = ["user:read:chat"]
        has_all, missing = self.auth.has_all_required_scopes()
        assert has_all is True
        assert missing == []

    def test_has_all_required_scopes_missing(self):
        self.auth._scopes = []
        has_all, missing = self.auth.has_all_required_scopes()
        assert has_all is False
        assert "user:read:chat" in missing

    def test_validate_token_no_token(self):
        config = TwitchConfig(enabled=True, client_id="id")
        auth = TwitchAuth(config)
        result = auth.validate_token()
        assert result.valid is False
        assert "No access token" in result.error

    @patch("integrations.twitch.auth.urllib.request.urlopen")
    def test_validate_token_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"login":"test","user_id":"999","client_id":"test_client_id","scopes":["user:read:chat"],"expires_in":3600}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.auth.validate_token()
        assert result.valid is True
        assert result.login == "test"
        assert result.user_id == "999"
        assert result.client_id == "test_client_id"
        assert "user:read:chat" in result.scopes
        assert result.expires_in == 3600

    @patch("integrations.twitch.auth.urllib.request.urlopen")
    def test_validate_token_401(self, mock_urlopen):
        import urllib.error
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"message":"invalid access token"}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=mock_resp
        )
        result = self.auth.validate_token()
        assert result.valid is False
        assert "Invalid or expired" in result.error

    @patch("integrations.twitch.auth.urllib.request.urlopen")
    def test_validate_token_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("Connection refused")
        result = self.auth.validate_token()
        assert result.valid is False
        assert "Network error" in result.error

    @patch("integrations.twitch.auth.urllib.request.urlopen")
    def test_validate_token_wrong_client_id(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"login":"test","user_id":"999","client_id":"different_id","scopes":["user:read:chat"],"expires_in":3600}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.auth.validate_token()
        assert result.valid is True
        assert result.client_id == "different_id"

    def test_get_diagnostics(self):
        self.auth._login = "testuser"
        self.auth._user_id = "12345"
        self.auth._scopes = ["user:read:chat"]
        self.auth._expires_at = 9999999999.0

        diag = self.auth.get_diagnostics()
        assert diag["has_token"] is True
        assert diag["token_prefix"] == "test_tok..."
        assert diag["client_id"] == "test_client_id"
        assert diag["login"] == "testuser"
        assert diag["user_id"] == "12345"
        assert "user:read:chat" in diag["scopes"]
        assert diag["is_valid"] is True

    def test_get_diagnostics_no_token(self):
        config = TwitchConfig(enabled=True, client_id="id")
        auth = TwitchAuth(config)
        diag = auth.get_diagnostics()
        assert diag["has_token"] is False
        assert diag["token_prefix"] == ""
