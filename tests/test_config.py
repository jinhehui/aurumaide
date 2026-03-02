"""Tests for aurumaide.utility.config."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from aurumaide.utility.config import Config, get_config, reset_config

# ---------------------------------------------------------------------------
# Config path
# ---------------------------------------------------------------------------


class TestGetConfigPath:
    def test_default_path_uses_home(self):
        with patch.dict("os.environ", {"HOME": "/fake/home"}, clear=True):
            cfg = Config.__new__(Config)
            cfg.path = None
            # Just verify the module function computes the right path
            from aurumaide.utility.config import _default_config_path

            path = _default_config_path()
            assert path.endswith(".aurumaide/config.json") or path.endswith(
                ".aurumaide\\config.json"
            )

    def test_custom_path(self, tmp_path: Path):
        config_file = tmp_path / "custom.json"
        config_file.write_text(json.dumps({"gemini": {"apiKey": "k"}}))
        cfg = Config(path=str(config_file))
        assert cfg.path == str(config_file)


# ---------------------------------------------------------------------------
# Config creation
# ---------------------------------------------------------------------------


class TestConfigCreation:
    def test_creates_default_file(self, tmp_path: Path):
        config_file = tmp_path / "sub" / "config.json"
        with patch.dict("os.environ", {}, clear=True):
            cfg = Config(path=str(config_file))

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["openai"]["apiKey"] == ""
        assert data["gemini"]["apiKey"] == ""
        assert data["gemini"]["chatModel"] == "gemini-3-flash-preview"
        assert data["teamcity"]["token"] == ""
        assert data["teamcity"]["baseUrl"] == ""
        # Verify the instance also loaded the data
        assert cfg.gemini_chat_model == "gemini-3-flash-preview"

    def test_seeds_env_vars_at_creation(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "oai-key", "GOOGLE_API_KEY": "gem-key"},
            clear=True,
        ):
            cfg = Config(path=str(config_file))

        data = json.loads(config_file.read_text())
        assert data["openai"]["apiKey"] == "oai-key"
        assert data["gemini"]["apiKey"] == "gem-key"
        assert cfg.openai_api_key == "oai-key"
        assert cfg.gemini_api_key == "gem-key"

    def test_reads_existing_file(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"gemini": {"apiKey": "existing", "chatModel": "custom-m"}})
        )
        cfg = Config(path=str(config_file))
        assert cfg.gemini_api_key == "existing"
        assert cfg.gemini_chat_model == "custom-m"

    def test_does_not_overwrite_existing(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        original = {"gemini": {"apiKey": "keep-me"}}
        config_file.write_text(json.dumps(original))

        with patch.dict(
            "os.environ", {"GOOGLE_API_KEY": "new-value"}, clear=True
        ):
            cfg = Config(path=str(config_file))

        # File on disk must be untouched
        data = json.loads(config_file.read_text())
        assert data == original
        assert cfg.gemini_api_key == "keep-me"


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestConfigProperties:
    def test_defaults(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        with patch.dict("os.environ", {}, clear=True):
            cfg = Config(path=str(config_file))

        assert cfg.openai_api_key == ""
        assert cfg.gemini_api_key == ""
        assert cfg.gemini_chat_model == "gemini-3-flash-preview"
        assert cfg.teamcity_token == ""
        assert cfg.teamcity_base_url == ""

    def test_missing_section(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({}))
        cfg = Config(path=str(config_file))
        assert cfg.gemini_api_key == ""
        assert cfg.teamcity_token == ""

    def test_missing_key(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"gemini": {}}))
        cfg = Config(path=str(config_file))
        assert cfg.gemini_api_key == ""
        assert cfg.gemini_chat_model == ""


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_returns_same_instance(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        with patch.dict("os.environ", {}, clear=True):
            a = get_config(path=str(config_file))
            b = get_config()
        assert a is b

    def test_reset_clears_singleton(self, tmp_path: Path):
        config_file = tmp_path / "config.json"
        with patch.dict("os.environ", {}, clear=True):
            a = get_config(path=str(config_file))
        reset_config()
        config_file2 = tmp_path / "config2.json"
        with patch.dict("os.environ", {}, clear=True):
            b = get_config(path=str(config_file2))
        assert a is not b
