"""Sentinel Hub authentication service."""

from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import config


class SentinelHubAuth:
    """Manages Sentinel Hub OAuth2.0 authentication."""

    def __init__(self, base_url: str = "https://services.sentinel-hub.com"):
        self.base_url = base_url
        self.client_id = config.SENTINEL_HUB_CLIENT_ID
        self.client_secret = config.SENTINEL_HUB_CLIENT_SECRET
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    def get_token(self) -> str:
        """
        Get a valid access token.

        Returns unexpired token, otherwise fetches a new one.

        Returns:
            Valid OAuth2.0 access token
        """
        if self._token and self._token_expires_at:
            if datetime.now(UTC) < self._token_expires_at:
                return self._token

        self._token = self._fetch_new_token()
        return self._token

    def _fetch_new_token(self) -> str:
        """
        Authenticate and Fetch a new access token from sentinel hub api

        Returns:
            New access token
        """
        auth_creds = httpx.BasicAuth(
            username=self.client_id, password=self.client_secret
        )
        token_data = {
            "grant_type": "client_credentials",
        }
        with httpx.Client(
            base_url=self.base_url,
            auth=auth_creds,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as client:
            response = client.post(
                "/auth/realms/main/protocol/openid-connect/token", data=token_data
            )
            response.raise_for_status()

        data = response.json()

        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 300)

        return data["access_token"]


sentinel_auth = SentinelHubAuth()
