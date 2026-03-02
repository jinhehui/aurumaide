"""Configuration manager for aurumaide.

Reads and auto-creates ``~/.aurumaide/config.json`` with per-service settings.
Provides a singleton ``get_config()`` accessor so every consumer shares the
same instance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _default_config_path() -> str:
    """Return the default config file path under the user's home directory."""
    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or "~"
    return str(Path(home).expanduser() / ".aurumaide" / "config.json")


class Config:
    """Reads per-service settings from a JSON config file."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or _default_config_path()
        self._data: dict[str, Any] = {}
        self._load()

    # -- public properties ---------------------------------------------------

    @property
    def openai_api_key(self) -> str:
        return self._get("openai", "apiKey")

    @property
    def gemini_api_key(self) -> str:
        return self._get("gemini", "apiKey")

    @property
    def gemini_chat_model(self) -> str:
        return self._get("gemini", "chatModel")

    @property
    def teamcity_token(self) -> str:
        return self._get("teamcity", "token")

    @property
    def teamcity_base_url(self) -> str:
        return self._get("teamcity", "baseUrl")

    # -- private helpers -----------------------------------------------------

    def _load(self) -> None:
        """Read JSON from disk, creating the default file first if needed."""
        if not os.path.exists(self.path):
            self._create_default()
        with open(self.path, encoding="utf-8") as f:
            self._data = json.load(f)

    def _create_default(self) -> None:
        """Write the default config JSON, seeding env-var values."""
        data: dict[str, Any] = {
            "openai": {
                "apiKey": os.environ.get("OPENAI_API_KEY", ""),
            },
            "gemini": {
                "apiKey": os.environ.get("GOOGLE_API_KEY", ""),
                "chatModel": "gemini-3-flash-preview",
            },
            "teamcity": {
                "token": "",
                "baseUrl": "",
            },
        }
        parent = os.path.dirname(self.path)
        os.makedirs(parent, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _get(self, section: str, key: str) -> str:
        """Safe getter — returns ``""`` for any missing section or key."""
        try:
            value: str = self._data[section][key]
            return value
        except (KeyError, TypeError):
            return ""


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_config: Config | None = None


def get_config(path: str | None = None) -> Config:
    """Return (or create) the module-level Config singleton."""
    global _config
    if _config is None:
        _config = Config(path)
    return _config


def reset_config() -> None:
    """Clear the singleton — intended for test teardown."""
    global _config
    _config = None
