import os
import secrets
import time
import urllib.parse
from typing import Optional

import requests


TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
TWITCH_API_BASE = "https://api.twitch.tv/helix"

REQUIRED_SCOPES = ["user:read:login"]


class TwitchOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(REQUIRED_SCOPES),
            "state": state,
            "force_verify": "false",
        }
        return f"{TWITCH_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> Optional[dict]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        try:
            resp = requests.post(TWITCH_TOKEN_URL, data=data, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None

    def validate_token(self, access_token: str) -> Optional[dict]:
        headers = {"Authorization": f"OAuth {access_token}"}
        try:
            resp = requests.get(TWITCH_VALIDATE_URL, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None

    def get_user_info(self, access_token: str) -> Optional[dict]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id,
        }
        try:
            resp = requests.get(f"{TWITCH_API_BASE}/users", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    user = data[0]
                    return {
                        "user_id": user["id"],
                        "login": user["login"],
                        "display_name": user["display_name"],
                    }
            return None
        except requests.RequestException:
            return None

    def refresh_token(self, refresh_token: str) -> Optional[dict]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        try:
            resp = requests.post(TWITCH_TOKEN_URL, data=data, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None


def generate_state() -> str:
    return secrets.token_urlsafe(32)
