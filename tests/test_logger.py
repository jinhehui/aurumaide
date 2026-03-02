"""Tests for aurumaide.utility.logger."""

import logging
import os
from unittest.mock import patch

from aurumaide.utility.logger import (
    ChatLogger,
    _find_repository_root,
    get_home_dir,
    get_out_dir,
    get_timestamp,
    initialize,
    save_output,
)

# ── get_home_dir ─────────────────────────────────────────────────────────


class TestGetHomeDir:
    def test_uses_aurumaide_home_env(self, tmp_path, monkeypatch):
        target = str(tmp_path / "custom_home")
        monkeypatch.setenv("AURUMAIDE_HOME", target)
        result = get_home_dir()
        assert result == target
        assert os.path.isdir(target)

    def test_creates_dir_if_missing(self, tmp_path, monkeypatch):
        target = str(tmp_path / "new_dir")
        monkeypatch.setenv("AURUMAIDE_HOME", target)
        assert not os.path.exists(target)
        get_home_dir()
        assert os.path.isdir(target)

    def test_falls_back_to_repo_root(self, monkeypatch):
        monkeypatch.delenv("AURUMAIDE_HOME", raising=False)
        with patch(
            "aurumaide.utility.logger._find_repository_root",
            return_value="/fake/repo",
        ), patch("os.path.exists", return_value=True):
            assert get_home_dir() == "/fake/repo"

    def test_falls_back_to_user_home(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AURUMAIDE_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("USERPROFILE", raising=False)
        with patch(
            "aurumaide.utility.logger._find_repository_root", return_value=None
        ):
            result = get_home_dir()
        assert result == str(tmp_path / ".aurumaide")
        assert os.path.isdir(result)

    def test_falls_back_to_userprofile(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AURUMAIDE_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        with patch(
            "aurumaide.utility.logger._find_repository_root", return_value=None
        ):
            result = get_home_dir()
        assert result == str(tmp_path / ".aurumaide")

    def test_falls_back_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AURUMAIDE_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.delenv("USERPROFILE", raising=False)
        with (
            patch(
                "aurumaide.utility.logger._find_repository_root",
                return_value=None,
            ),
            patch("os.path.abspath", return_value=str(tmp_path)),
        ):
            result = get_home_dir()
        assert result == str(tmp_path / ".aurumaide")


# ── get_out_dir ──────────────────────────────────────────────────────────


class TestGetOutDir:
    def test_default_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        result = get_out_dir()
        assert result == str(tmp_path / "out")
        assert os.path.isdir(result)

    def test_custom_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        result = get_out_dir("logs")
        assert result == str(tmp_path / "logs")
        assert os.path.isdir(result)

    def test_existing_dir_not_recreated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        out = tmp_path / "out"
        out.mkdir()
        marker = out / "marker.txt"
        marker.write_text("exists")
        get_out_dir()
        assert marker.read_text() == "exists"


# ── _find_repository_root ───────────────────────────────────────────────


class TestFindRepositoryRoot:
    def test_finds_git_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        fake_module = tmp_path / "src" / "pkg"
        fake_module.mkdir(parents=True)
        with patch(
            "aurumaide.utility.logger.realpath",
            return_value=str(fake_module / "mod.py"),
        ):
            result = _find_repository_root()
        assert result == str(tmp_path)

    def test_returns_none_without_git(self, tmp_path):
        fake_module = tmp_path / "src" / "pkg"
        fake_module.mkdir(parents=True)
        with patch(
            "aurumaide.utility.logger.realpath",
            return_value=str(fake_module / "mod.py"),
        ):
            result = _find_repository_root()
        assert result is None


# ── get_timestamp ────────────────────────────────────────────────────────


class TestGetTimestamp:
    def test_no_colons(self):
        assert ":" not in get_timestamp()

    def test_default_milliseconds(self):
        ts = get_timestamp()
        # Millisecond timestamps have a dot followed by 3 digits
        assert "." in ts

    def test_seconds_precision(self):
        ts = get_timestamp("seconds")
        # Seconds precision has no dot
        assert "." not in ts

    def test_contains_date_separator(self):
        ts = get_timestamp()
        assert "T" in ts


# ── save_output ──────────────────────────────────────────────────────────


class TestSaveOutput:
    def test_creates_file_with_content(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        save_output("test", "hello world")
        out_dir = tmp_path / "out"
        files = list(out_dir.glob("test-*.md"))
        assert len(files) == 1
        assert files[0].read_text(encoding="utf-8") == "hello world"

    def test_file_name_pattern(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        save_output("summary", "content")
        files = list((tmp_path / "out").glob("summary-*.md"))
        assert len(files) == 1
        assert files[0].name.startswith("summary-")
        assert files[0].name.endswith(".md")

    def test_utf8_content(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        text = "Unicode test: \u4f60\u597d \u00e9\u00e8\u00ea"
        save_output("utf8", text)
        files = list((tmp_path / "out").glob("utf8-*.md"))
        assert files[0].read_text(encoding="utf-8") == text

    def test_returns_file_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        path = save_output("ret", "data")
        assert os.path.isfile(path)
        assert path.endswith(".md")


# ── ChatLogger ───────────────────────────────────────────────────────────


class TestChatLogger:
    def test_init(self):
        logger = ChatLogger("test query")
        assert logger.query == "test query"
        assert logger.answers == []
        assert logger.last_saved_file is None

    def test_add(self):
        logger = ChatLogger("q")
        logger.add("chunk1")
        logger.add("chunk2")
        assert logger.answers == ["chunk1", "chunk2"]

    def test_save_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        logger = ChatLogger("What is AI?")
        logger.add("AI is ")
        logger.add("artificial intelligence.")
        logger.save()

        files = list((tmp_path / "out").glob("chat-*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert content == (
            "User: What is AI?\n\n"
            "Assistant: AI is artificial intelligence."
        )

    def test_save_sets_last_saved_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        logger = ChatLogger("q")
        logger.add("answer")
        logger.save()
        assert logger.last_saved_file is not None
        assert os.path.isfile(logger.last_saved_file)

    def test_save_noop_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        logger = ChatLogger("q")
        logger.save()
        assert logger.last_saved_file is None
        out_dir = tmp_path / "out"
        assert not out_dir.exists() or list(out_dir.glob("*.md")) == []


# ── initialize ───────────────────────────────────────────────────────────


class TestInitialize:
    def test_calls_load_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        with patch("aurumaide.utility.logger.load_dotenv") as mock_dotenv:
            # Reset root logger handlers to allow basicConfig to work
            root = logging.getLogger()
            root.handlers.clear()
            initialize()
        mock_dotenv.assert_called_once()

    def test_creates_log_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        root = logging.getLogger()
        root.handlers.clear()
        with patch("aurumaide.utility.logger.load_dotenv"):
            initialize(log_file_dir=str(tmp_path))
        log_files = list(tmp_path.glob("logger-*.log"))
        assert len(log_files) >= 1

    def test_custom_base_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        root = logging.getLogger()
        root.handlers.clear()
        with patch("aurumaide.utility.logger.load_dotenv"):
            initialize(
                log_file_base_name="app",
                log_file_dir=str(tmp_path),
            )
        log_files = list(tmp_path.glob("app-*.log"))
        assert len(log_files) >= 1

    def test_sets_log_level(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AURUMAIDE_HOME", str(tmp_path))
        root = logging.getLogger()
        root.handlers.clear()
        with patch("aurumaide.utility.logger.load_dotenv"):
            initialize(
                log_level=logging.DEBUG,
                log_file_dir=str(tmp_path),
            )
        assert logging.getLogger().level == logging.DEBUG
