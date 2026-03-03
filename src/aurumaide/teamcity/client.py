"""TeamCity REST API client using bearer token authentication.

Provides read/write access to TeamCity projects, builds, and build logs
via the TeamCity REST API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from aurumaide.utility.config import get_config

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Project:
    """A TeamCity project."""

    id: str
    name: str
    href: str = ""


@dataclass(frozen=True)
class Build:
    """A TeamCity build."""

    id: int
    number: str = ""
    state: str = ""
    status: str = ""
    branch: str = ""
    personal: bool = False
    build_type_id: str = ""
    start_date: str = ""
    finish_date: str = ""
    web_url: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TeamCityError(Exception):
    """Base exception for TeamCity operations."""


class TeamCityAPIError(TeamCityError):
    """Raised when a TeamCity REST API call fails."""

    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TeamCityClient:
    """TeamCity REST API client with bearer token authentication."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("TEAMCITY_BASE_URL", "")
            or get_config().teamcity_base_url
        ).rstrip("/")
        self.token = (
            token
            or os.environ.get("TEAMCITY_TOKEN", "")
            or get_config().teamcity_token
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        if not self.base_url:
            raise TeamCityError(
                "TEAMCITY_BASE_URL is required. "
                "Set it via env var or constructor."
            )
        if not self.token:
            raise TeamCityError(
                "TEAMCITY_TOKEN is required. "
                "Set it via env var or constructor."
            )

    # -- public methods -----------------------------------------------------

    def list_projects(self) -> list[Project]:
        """List all projects."""
        data = self._get("/app/rest/projects")
        projects: list[dict[str, Any]] = data.get("project", [])
        return [self._parse_project(p) for p in projects]

    def get_latest_build(self, build_type_id: str) -> Build | None:
        """Get the latest finished build for a build configuration.

        Returns ``None`` if no finished build exists.
        """
        locator = (
            f"buildType:{build_type_id},"
            "state:finished,"
            "branch:<default>,"
            "count:1"
        )
        data = self._get("/app/rest/builds", params={"locator": locator})
        builds: list[dict[str, Any]] = data.get("build", [])
        if not builds:
            return None
        return self._parse_build(builds[0])

    def start_build(
        self,
        build_type_id: str,
        branch: str,
        personal: bool = True,
    ) -> Build:
        """Trigger a new build and return it."""
        body: dict[str, Any] = {
            "personal": personal,
            "buildType": {"id": build_type_id},
            "branchName": branch,
        }
        data = self._post_json("/app/rest/buildQueue", body)
        return self._parse_build(data)

    def get_build(self, build_id: int) -> Build:
        """Get a single build by ID."""
        data = self._get(f"/app/rest/builds/id:{build_id}")
        return self._parse_build(data)

    def cancel_build(self, build_id: int, comment: str = "") -> None:
        """Cancel a running or queued build."""
        xml = (
            f'<buildCancelRequest comment="{comment}" '
            f'readdIntoQueue="false"/>'
        )
        self._post_xml(f"/app/rest/builds/id:{build_id}", xml)

    def download_build_log(self, build_id: int) -> str:
        """Download the full build log as plain text."""
        return self._get_text(f"/downloadBuildLog.html?buildId={build_id}")

    # -- private helpers ----------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Return common request headers."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Make a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                params=params,
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
        result: dict[str, Any] = resp.json()
        return result

    def _post_json(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST JSON and return parsed response."""
        url = f"{self.base_url}{path}"
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        try:
            resp = requests.post(
                url,
                headers=headers,
                json=data,
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
        result: dict[str, Any] = resp.json()
        return result

    def _post_xml(self, path: str, body: str) -> requests.Response:
        """POST XML and return the raw response."""
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/xml",
        }
        try:
            resp = requests.post(
                url,
                headers=headers,
                data=body,
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
        return resp

    def _get_text(self, path: str) -> str:
        """Make a GET request and return plain text."""
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "text/plain",
        }
        try:
            resp = requests.get(
                url,
                headers=headers,
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
        return resp.text

    @staticmethod
    def _parse_project(data: dict[str, Any]) -> Project:
        """Parse a project JSON dict into a Project."""
        return Project(
            id=data.get("id", ""),
            name=data.get("name", ""),
            href=data.get("href", ""),
        )

    @staticmethod
    def _parse_build(data: dict[str, Any]) -> Build:
        """Parse a build JSON dict into a Build."""
        return Build(
            id=int(data.get("id", 0)),
            number=data.get("number", ""),
            state=data.get("state", ""),
            status=data.get("status", ""),
            branch=data.get("branchName", ""),
            personal=bool(data.get("personal", False)),
            build_type_id=data.get("buildTypeId", ""),
            start_date=data.get("startDate", ""),
            finish_date=data.get("finishDate", ""),
            web_url=data.get("webUrl", ""),
        )
