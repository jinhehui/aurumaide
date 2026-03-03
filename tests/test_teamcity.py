"""Tests for aurumaide.teamcity.client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests as requests_lib

from aurumaide.teamcity.client import (
    Build,
    Project,
    TeamCityAPIError,
    TeamCityClient,
    TeamCityError,
)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class TestProject:
    def test_construction(self):
        p = Project(id="Proj1", name="My Project", href="/app/rest/projects/id:Proj1")
        assert p.id == "Proj1"
        assert p.name == "My Project"
        assert p.href == "/app/rest/projects/id:Proj1"

    def test_defaults(self):
        p = Project(id="P", name="N")
        assert p.href == ""

    def test_frozen(self):
        p = Project(id="P", name="N")
        with pytest.raises(AttributeError):
            p.id = "X"  # type: ignore[misc]


class TestBuild:
    def test_construction(self):
        b = Build(
            id=123,
            number="456",
            state="finished",
            status="SUCCESS",
            branch="main",
            personal=True,
            build_type_id="MyBuild",
            start_date="20250101T120000+0000",
            finish_date="20250101T121000+0000",
            web_url="https://tc.example.com/build/123",
        )
        assert b.id == 123
        assert b.number == "456"
        assert b.state == "finished"
        assert b.status == "SUCCESS"
        assert b.branch == "main"
        assert b.personal is True
        assert b.build_type_id == "MyBuild"
        assert b.start_date == "20250101T120000+0000"
        assert b.finish_date == "20250101T121000+0000"
        assert b.web_url == "https://tc.example.com/build/123"

    def test_defaults(self):
        b = Build(id=1)
        assert b.number == ""
        assert b.state == ""
        assert b.status == ""
        assert b.branch == ""
        assert b.personal is False
        assert b.build_type_id == ""
        assert b.start_date == ""
        assert b.finish_date == ""
        assert b.web_url == ""

    def test_frozen(self):
        b = Build(id=1)
        with pytest.raises(AttributeError):
            b.id = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(TeamCityAPIError, TeamCityError)
        assert issubclass(TeamCityError, Exception)

    def test_api_error_attributes(self):
        err = TeamCityAPIError("bad request", status_code=400)
        assert str(err) == "bad request"
        assert err.status_code == 400

    def test_api_error_defaults(self):
        err = TeamCityAPIError("fail")
        assert err.status_code == 0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

BASE_URL = "https://tc.example.com"
TOKEN = "test-token-abc"


def _make_client(
    base_url: str = BASE_URL,
    token: str = TOKEN,
    timeout: int = 30,
) -> TeamCityClient:
    """Return a TeamCityClient with known params."""
    return TeamCityClient(base_url=base_url, token=token, timeout=timeout)


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_explicit_params(self):
        client = _make_client()
        assert client.base_url == BASE_URL
        assert client.token == TOKEN
        assert client.timeout == 30

    def test_strips_trailing_slash(self):
        client = _make_client(base_url="https://tc.example.com/")
        assert client.base_url == "https://tc.example.com"

    def test_env_var_fallback(self):
        with patch.dict(
            "os.environ",
            {
                "TEAMCITY_BASE_URL": "https://env-tc.example.com",
                "TEAMCITY_TOKEN": "env-token",
            },
        ):
            client = TeamCityClient()
            assert client.base_url == "https://env-tc.example.com"
            assert client.token == "env-token"

    @patch("aurumaide.teamcity.client.get_config")
    def test_config_fallback(self, mock_gc):
        cfg = MagicMock()
        cfg.teamcity_base_url = "https://cfg-tc.example.com"
        cfg.teamcity_token = "cfg-token"
        mock_gc.return_value = cfg
        with patch.dict("os.environ", {}, clear=True):
            client = TeamCityClient()
        assert client.base_url == "https://cfg-tc.example.com"
        assert client.token == "cfg-token"

    @patch("aurumaide.teamcity.client.get_config")
    def test_missing_base_url_raises(self, mock_gc):
        cfg = MagicMock()
        cfg.teamcity_base_url = ""
        cfg.teamcity_token = ""
        mock_gc.return_value = cfg
        with patch.dict("os.environ", {}, clear=True), pytest.raises(
            TeamCityError, match="TEAMCITY_BASE_URL"
        ):
            TeamCityClient(token="tok")

    @patch("aurumaide.teamcity.client.get_config")
    def test_missing_token_raises(self, mock_gc):
        cfg = MagicMock()
        cfg.teamcity_base_url = ""
        cfg.teamcity_token = ""
        mock_gc.return_value = cfg
        with patch.dict("os.environ", {}, clear=True), pytest.raises(
            TeamCityError, match="TEAMCITY_TOKEN"
        ):
            TeamCityClient(base_url="https://tc.example.com")


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------

SAMPLE_PROJECT = {
    "id": "MyProject",
    "name": "My Project",
    "href": "/app/rest/projects/id:MyProject",
}


class TestListProjects:
    @patch("aurumaide.teamcity.client.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"project": [SAMPLE_PROJECT]}
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.list_projects()

        assert len(result) == 1
        assert result[0].id == "MyProject"
        assert result[0].name == "My Project"
        assert result[0].href == "/app/rest/projects/id:MyProject"

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == f"{BASE_URL}/app/rest/projects"
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {TOKEN}"

    @patch("aurumaide.teamcity.client.requests.get")
    def test_empty(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"project": []}
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.list_projects()

        assert result == []

    @patch("aurumaide.teamcity.client.requests.get")
    def test_http_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(TeamCityAPIError) as exc_info:
            client.list_projects()
        assert exc_info.value.status_code == 403

    @patch("aurumaide.teamcity.client.requests.get")
    def test_network_error(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("Connection refused")

        client = _make_client()
        with pytest.raises(TeamCityAPIError, match="Network error"):
            client.list_projects()


# ---------------------------------------------------------------------------
# get_latest_build
# ---------------------------------------------------------------------------

SAMPLE_BUILD = {
    "id": 789,
    "number": "42",
    "state": "finished",
    "status": "SUCCESS",
    "branchName": "main",
    "personal": False,
    "buildTypeId": "MyBuild",
    "startDate": "20250101T120000+0000",
    "finishDate": "20250101T121000+0000",
    "webUrl": "https://tc.example.com/build/789",
}


class TestGetLatestBuild:
    @patch("aurumaide.teamcity.client.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"build": [SAMPLE_BUILD]}
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.get_latest_build("MyBuild")

        assert result is not None
        assert result.id == 789
        assert result.number == "42"
        assert result.state == "finished"
        assert result.status == "SUCCESS"
        assert result.branch == "main"
        assert result.personal is False
        assert result.build_type_id == "MyBuild"
        assert result.web_url == "https://tc.example.com/build/789"

        # Verify locator params
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert "buildType:MyBuild" in params["locator"]
        assert "state:finished" in params["locator"]
        assert "branch:<default>" in params["locator"]
        assert "count:1" in params["locator"]

    @patch("aurumaide.teamcity.client.requests.get")
    def test_none_when_empty(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"build": []}
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.get_latest_build("NoBuild")

        assert result is None

    @patch("aurumaide.teamcity.client.requests.get")
    def test_none_when_missing_key(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.get_latest_build("NoBuild")

        assert result is None


# ---------------------------------------------------------------------------
# start_build
# ---------------------------------------------------------------------------


class TestStartBuild:
    @patch("aurumaide.teamcity.client.requests.post")
    def test_success(self, mock_post):
        response_build = {
            "id": 800,
            "number": "",
            "state": "queued",
            "status": "UNKNOWN",
            "branchName": "feature/x",
            "personal": True,
            "buildTypeId": "MyBuild",
        }
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = response_build
        mock_post.return_value = mock_resp

        client = _make_client()
        result = client.start_build("MyBuild", "feature/x", personal=True)

        assert result.id == 800
        assert result.state == "queued"
        assert result.personal is True
        assert result.branch == "feature/x"

        # Verify JSON body
        call_args = mock_post.call_args
        assert call_args[0][0] == f"{BASE_URL}/app/rest/buildQueue"
        json_body = call_args[1]["json"]
        assert json_body["personal"] is True
        assert json_body["buildType"]["id"] == "MyBuild"
        assert json_body["branchName"] == "feature/x"

    @patch("aurumaide.teamcity.client.requests.post")
    def test_not_personal(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "id": 801,
            "personal": False,
            "buildTypeId": "MyBuild",
        }
        mock_post.return_value = mock_resp

        client = _make_client()
        result = client.start_build("MyBuild", "main", personal=False)

        assert result.personal is False
        json_body = mock_post.call_args[1]["json"]
        assert json_body["personal"] is False

    @patch("aurumaide.teamcity.client.requests.post")
    def test_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        client = _make_client()
        with pytest.raises(TeamCityAPIError) as exc_info:
            client.start_build("MyBuild", "main")
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# get_build
# ---------------------------------------------------------------------------


class TestGetBuild:
    @patch("aurumaide.teamcity.client.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = SAMPLE_BUILD
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.get_build(789)

        assert result.id == 789
        assert result.status == "SUCCESS"

        call_args = mock_get.call_args
        assert call_args[0][0] == f"{BASE_URL}/app/rest/builds/id:789"

    @patch("aurumaide.teamcity.client.requests.get")
    def test_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mock_get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(TeamCityAPIError) as exc_info:
            client.get_build(99999)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# cancel_build
# ---------------------------------------------------------------------------


class TestCancelBuild:
    @patch("aurumaide.teamcity.client.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_post.return_value = mock_resp

        client = _make_client()
        result = client.cancel_build(789, comment="No longer needed")

        assert result is None

        call_args = mock_post.call_args
        assert call_args[0][0] == f"{BASE_URL}/app/rest/builds/id:789"
        body = call_args[1]["data"]
        assert 'comment="No longer needed"' in body
        assert 'readdIntoQueue="false"' in body
        assert call_args[1]["headers"]["Content-Type"] == "application/xml"

    @patch("aurumaide.teamcity.client.requests.post")
    def test_empty_comment(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_post.return_value = mock_resp

        client = _make_client()
        client.cancel_build(789)

        body = mock_post.call_args[1]["data"]
        assert 'comment=""' in body

    @patch("aurumaide.teamcity.client.requests.post")
    def test_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 409
        mock_resp.text = "Conflict"
        mock_post.return_value = mock_resp

        client = _make_client()
        with pytest.raises(TeamCityAPIError) as exc_info:
            client.cancel_build(789)
        assert exc_info.value.status_code == 409

    @patch("aurumaide.teamcity.client.requests.post")
    def test_network_error(self, mock_post):
        mock_post.side_effect = requests_lib.ConnectionError("Connection refused")

        client = _make_client()
        with pytest.raises(TeamCityAPIError, match="Network error"):
            client.cancel_build(789)


# ---------------------------------------------------------------------------
# download_build_log
# ---------------------------------------------------------------------------


class TestDownloadBuildLog:
    @patch("aurumaide.teamcity.client.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.text = "[12:00:00] Build started\n[12:01:00] Build finished"
        mock_get.return_value = mock_resp

        client = _make_client()
        result = client.download_build_log(789)

        assert "Build started" in result
        assert "Build finished" in result

        call_args = mock_get.call_args
        assert call_args[0][0] == f"{BASE_URL}/downloadBuildLog.html?buildId=789"
        assert call_args[1]["headers"]["Accept"] == "text/plain"

    @patch("aurumaide.teamcity.client.requests.get")
    def test_http_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mock_get.return_value = mock_resp

        client = _make_client()
        with pytest.raises(TeamCityAPIError) as exc_info:
            client.download_build_log(99999)
        assert exc_info.value.status_code == 404

    @patch("aurumaide.teamcity.client.requests.get")
    def test_network_error(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("Connection refused")

        client = _make_client()
        with pytest.raises(TeamCityAPIError, match="Network error"):
            client.download_build_log(789)


# ---------------------------------------------------------------------------
# _parse_project / _parse_build
# ---------------------------------------------------------------------------


class TestParsers:
    def test_parse_project(self):
        p = TeamCityClient._parse_project(SAMPLE_PROJECT)
        assert p.id == "MyProject"
        assert p.name == "My Project"
        assert p.href == "/app/rest/projects/id:MyProject"

    def test_parse_project_minimal(self):
        p = TeamCityClient._parse_project({})
        assert p.id == ""
        assert p.name == ""
        assert p.href == ""

    def test_parse_build(self):
        b = TeamCityClient._parse_build(SAMPLE_BUILD)
        assert b.id == 789
        assert b.number == "42"
        assert b.state == "finished"
        assert b.status == "SUCCESS"
        assert b.branch == "main"
        assert b.personal is False
        assert b.build_type_id == "MyBuild"
        assert b.start_date == "20250101T120000+0000"
        assert b.finish_date == "20250101T121000+0000"
        assert b.web_url == "https://tc.example.com/build/789"

    def test_parse_build_minimal(self):
        b = TeamCityClient._parse_build({})
        assert b.id == 0
        assert b.number == ""
        assert b.state == ""
        assert b.status == ""
        assert b.branch == ""
        assert b.personal is False
        assert b.build_type_id == ""
        assert b.start_date == ""
        assert b.finish_date == ""
        assert b.web_url == ""
