"""TeamCity token manager using HTTP basic auth.

Creates, lists, and deletes access tokens via the TeamCity REST API.
Uses basic auth (username/password) — intended to bootstrap bearer tokens
that ``TeamCityClient`` then consumes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from aurumaide.teamcity.client import TeamCityAPIError, TeamCityError
from aurumaide.utility.config import get_config

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    """A TeamCity access token."""

    name: str
    value: str = ""
    creation_time: str = ""
    expiration_time: str = ""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class TeamCityTokenManager:
    """Manage TeamCity access tokens via basic auth."""

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("TEAMCITY_BASE_URL", "")
            or get_config().teamcity_base_url
        ).rstrip("/")
        self.username = username or os.environ.get("TEAMCITY_USERNAME", "")
        self.password = password or os.environ.get("TEAMCITY_PASSWORD", "")
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        if not self.base_url:
            raise TeamCityError(
                "TEAMCITY_BASE_URL is required. "
                "Set it via env var or constructor."
            )
        if not self.username:
            raise TeamCityError(
                "TEAMCITY_USERNAME is required. "
                "Set it via env var or constructor."
            )
        if not self.password:
            raise TeamCityError(
                "TEAMCITY_PASSWORD is required. "
                "Set it via env var or constructor."
            )

    # -- public methods -----------------------------------------------------

    def list_tokens(self) -> list[Token]:
        """List all access tokens for the current user."""
        url = f"{self.base_url}/httpAuth/app/rest/users/current/tokens"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                auth=self._auth(),
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise TeamCityAPIError(f"Network error: {exc}") from exc

        if not resp.ok:
            raise TeamCityAPIError(
                f"TeamCity API error: {resp.status_code} {resp.text}",
                status_code=resp.status_code,
            )
        data: dict[str, Any] = resp.json()
        tokens: list[dict[str, Any]] = data.get("token", [])
        return [self._parse_token(t) for t in tokens]

    def create_token(
        self, name: str, expiration_months: int = 24
    ) -> Token:
        """Create a new access token.

        The returned ``Token`` is the only time the ``value`` field is
        available — it cannot be retrieved later.
        """
        expiration = datetime.now(UTC) + timedelta(
            days=expiration_months * 30
        )
        expiration_str = expiration.strftime("%Y%m%dT%H%M%S+0000")

        url = (
            f"{self.base_url}/httpAuth/app/rest/users/current/tokens/{name}"
        )
        body = {"expirationTime": expiration_str}
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                auth=self._auth(),
                json=body,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise TeamCityAPIError(f"Network error: {exc}") from exc

        if not resp.ok:
            raise TeamCityAPIError(
                f"TeamCity API error: {resp.status_code} {resp.text}",
                status_code=resp.status_code,
            )
        data: dict[str, Any] = resp.json()
        return self._parse_token(data)

    def delete_token(self, name: str) -> None:
        """Delete an access token by name."""
        url = (
            f"{self.base_url}/httpAuth/app/rest/users/current/tokens/{name}"
        )
        try:
            resp = requests.delete(
                url,
                headers=self._headers(),
                auth=self._auth(),
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise TeamCityAPIError(f"Network error: {exc}") from exc

        if not resp.ok:
            raise TeamCityAPIError(
                f"TeamCity API error: {resp.status_code} {resp.text}",
                status_code=resp.status_code,
            )

    # -- private helpers ----------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Return common request headers."""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _auth(self) -> tuple[str, str]:
        """Return basic auth tuple."""
        return (self.username, self.password)

    @staticmethod
    def _parse_token(data: dict[str, Any]) -> Token:
        """Parse a token JSON dict into a Token."""
        return Token(
            name=data.get("name", ""),
            value=data.get("value", ""),
            creation_time=data.get("creationTime", ""),
            expiration_time=data.get("expirationTime", ""),
        )
