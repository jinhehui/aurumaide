"""Tests for aurumaide.teamcity.token."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests as requests_lib

from aurumaide.teamcity.client import TeamCityAPIError, TeamCityError
from aurumaide.teamcity.token import TeamCityTokenManager, Token

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class TestToken:
    def test_construction(self):
        t = Token(
            name="my-token",
            value="secret123",
            creation_time="20250101T120000+0000",
            expiration_time="20270101T120000+0000",
        )
        assert t.name == "my-token"
        assert t.value == "secret123"
        assert t.creation_time == "20250101T120000+0000"
        assert t.expiration_time == "20270101T120000+0000"

    def test_defaults(self):
        t = Token(name="tok")
        assert t.value == ""
        assert t.creation_time == ""
        assert t.expiration_time == ""

    def test_frozen(self):
        t = Token(name="tok")
        with pytest.raises(AttributeError):
            t.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

BASE_URL = "https://tc.example.com"
USERNAME = "admin"
PASSWORD = "s3cret"


def _make_manager(
    base_url: str = BASE_URL,
    username: str = USERNAME,
    password: str = PASSWORD,
    timeout: int = 30,
) -> TeamCityTokenManager:
    """Return a TeamCityTokenManager with known params."""
    return TeamCityTokenManager(
        base_url=base_url,
        username=username,
        password=password,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestTokenManagerInit:
    def test_explicit_params(self):
        mgr = _make_manager()
        assert mgr.base_url == BASE_URL
        assert mgr.username == USERNAME
        assert mgr.password == PASSWORD
        assert mgr.timeout == 30

    def test_strips_trailing_slash(self):
        mgr = _make_manager(base_url="https://tc.example.com/")
        assert mgr.base_url == "https://tc.example.com"

    def test_env_var_fallback(self):
        with patch.dict(
            "os.environ",
            {
                "TEAMCITY_BASE_URL": "https://env-tc.example.com",
                "TEAMCITY_USERNAME": "env-user",
                "TEAMCITY_PASSWORD": "env-pass",
            },
        ):
            mgr = TeamCityTokenManager()
            assert mgr.base_url == "https://env-tc.example.com"
            assert mgr.username == "env-user"
            assert mgr.password == "env-pass"

    @patch("aurumaide.teamcity.token.get_config")
    def test_config_fallback_base_url(self, mock_gc):
        cfg = MagicMock()
        cfg.teamcity_base_url = "https://cfg-tc.example.com"
        mock_gc.return_value = cfg
        with patch.dict("os.environ", {}, clear=True):
            mgr = TeamCityTokenManager(username="u", password="p")
        assert mgr.base_url == "https://cfg-tc.example.com"

    @patch("aurumaide.teamcity.token.get_config")
    def test_missing_base_url_raises(self, mock_gc):
        cfg = MagicMock()
        cfg.teamcity_base_url = ""
        mock_gc.return_value = cfg
        with patch.dict("os.environ", {}, clear=True), pytest.raises(
            TeamCityError, match="TEAMCITY_BASE_URL"
        ):
            TeamCityTokenManager(username="u", password="p")

    def test_missing_username_raises(self):
        with patch.dict("os.environ", {}, clear=True), pytest.raises(
            TeamCityError, match="TEAMCITY_USERNAME"
        ):
            TeamCityTokenManager(base_url="https://tc.example.com", password="p")

    def test_missing_password_raises(self):
        with patch.dict("os.environ", {}, clear=True), pytest.raises(
            TeamCityError, match="TEAMCITY_PASSWORD"
        ):
            TeamCityTokenManager(base_url="https://tc.example.com", username="u")


# ---------------------------------------------------------------------------
# list_tokens
# ---------------------------------------------------------------------------

SAMPLE_TOKEN = {
    "name": "my-token",
    "creationTime": "20250101T120000+0000",
    "expirationTime": "20270101T120000+0000",
}


class TestListTokens:
    @patch("aurumaide.teamcity.token.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"token": [SAMPLE_TOKEN]}
        mock_get.return_value = mock_resp

        mgr = _make_manager()
        result = mgr.list_tokens()

        assert len(result) == 1
        assert result[0].name == "my-token"
        assert result[0].value == ""
        assert result[0].creation_time == "20250101T120000+0000"
        assert result[0].expiration_time == "20270101T120000+0000"

        call_args = mock_get.call_args
        assert call_args[0][0] == (
            f"{BASE_URL}/httpAuth/app/rest/users/current/tokens"
        )
        assert call_args[1]["auth"] == (USERNAME, PASSWORD)

    @patch("aurumaide.teamcity.token.requests.get")
    def test_empty(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"token": []}
        mock_get.return_value = mock_resp

        mgr = _make_manager()
        result = mgr.list_tokens()

        assert result == []

    @patch("aurumaide.teamcity.token.requests.get")
    def test_http_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_get.return_value = mock_resp

        mgr = _make_manager()
        with pytest.raises(TeamCityAPIError) as exc_info:
            mgr.list_tokens()
        assert exc_info.value.status_code == 401

    @patch("aurumaide.teamcity.token.requests.get")
    def test_network_error(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("Connection refused")

        mgr = _make_manager()
        with pytest.raises(TeamCityAPIError, match="Network error"):
            mgr.list_tokens()


# ---------------------------------------------------------------------------
# create_token
# ---------------------------------------------------------------------------


class TestCreateToken:
    @patch("aurumaide.teamcity.token.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "name": "new-token",
            "value": "secret-value-abc",
            "creationTime": "20260222T100000+0000",
            "expirationTime": "20280222T100000+0000",
        }
        mock_post.return_value = mock_resp

        mgr = _make_manager()
        result = mgr.create_token("new-token")

        assert result.name == "new-token"
        assert result.value == "secret-value-abc"
        assert result.creation_time == "20260222T100000+0000"
        assert result.expiration_time == "20280222T100000+0000"

        call_args = mock_post.call_args
        assert call_args[0][0] == (
            f"{BASE_URL}/httpAuth/app/rest/users/current/tokens/new-token"
        )
        assert call_args[1]["auth"] == (USERNAME, PASSWORD)

    @patch("aurumaide.teamcity.token.requests.post")
    def test_url_contains_token_name(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"name": "custom-name", "value": "v"}
        mock_post.return_value = mock_resp

        mgr = _make_manager()
        mgr.create_token("custom-name")

        url = mock_post.call_args[0][0]
        assert url.endswith("/custom-name")

    @patch("aurumaide.teamcity.token.requests.post")
    def test_body_has_expiration_time(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"name": "tok", "value": "v"}
        mock_post.return_value = mock_resp

        mgr = _make_manager()
        mgr.create_token("tok", expiration_months=12)

        json_body = mock_post.call_args[1]["json"]
        assert "expirationTime" in json_body
        assert json_body["expirationTime"].endswith("+0000")

    @patch("aurumaide.teamcity.token.requests.post")
    def test_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_post.return_value = mock_resp

        mgr = _make_manager()
        with pytest.raises(TeamCityAPIError) as exc_info:
            mgr.create_token("bad-token")
        assert exc_info.value.status_code == 400

    @patch("aurumaide.teamcity.token.requests.post")
    def test_network_error(self, mock_post):
        mock_post.side_effect = requests_lib.ConnectionError("Connection refused")

        mgr = _make_manager()
        with pytest.raises(TeamCityAPIError, match="Network error"):
            mgr.create_token("tok")


# ---------------------------------------------------------------------------
# delete_token
# ---------------------------------------------------------------------------


class TestDeleteToken:
    @patch("aurumaide.teamcity.token.requests.delete")
    def test_success(self, mock_delete):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_delete.return_value = mock_resp

        mgr = _make_manager()
        result = mgr.delete_token("old-token")

        assert result is None

        call_args = mock_delete.call_args
        assert call_args[0][0] == (
            f"{BASE_URL}/httpAuth/app/rest/users/current/tokens/old-token"
        )
        assert call_args[1]["auth"] == (USERNAME, PASSWORD)

    @patch("aurumaide.teamcity.token.requests.delete")
    def test_http_error(self, mock_delete):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mock_delete.return_value = mock_resp

        mgr = _make_manager()
        with pytest.raises(TeamCityAPIError) as exc_info:
            mgr.delete_token("nonexistent")
        assert exc_info.value.status_code == 404

    @patch("aurumaide.teamcity.token.requests.delete")
    def test_network_error(self, mock_delete):
        mock_delete.side_effect = requests_lib.ConnectionError("Connection refused")

        mgr = _make_manager()
        with pytest.raises(TeamCityAPIError, match="Network error"):
            mgr.delete_token("tok")
