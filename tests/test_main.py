"""Tests for aurumaide.__main__."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from aurumaide.__main__ import HARDCODED_DEFAULT_MODEL, build_parser, main


class TestBuildParser:
    def test_returns_parser(self):
        parser = build_parser()
        assert parser.prog == "aurumaide"

    def test_default_model(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.model is None

    def test_custom_model(self):
        parser = build_parser()
        args = parser.parse_args(["--model", "gemini-2.5-pro"])
        assert args.model == "gemini-2.5-pro"

    def test_model_with_equals(self):
        parser = build_parser()
        args = parser.parse_args(["--model=gemini-2.5-pro"])
        assert args.model == "gemini-2.5-pro"

    def test_one_shot_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--one-shot", "hello"])
        assert args.one_shot is True

    def test_one_shot_default_false(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.one_shot is False

    def test_file_argument(self):
        parser = build_parser()
        args = parser.parse_args(["--file", "query.txt"])
        assert args.file == "query.txt"

    def test_positional_arguments(self):
        parser = build_parser()
        args = parser.parse_args(["hello", "world"])
        assert args.arguments == ["hello", "world"]

    def test_no_positional_arguments(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.arguments == []


def _mock_config(chat_model: str = HARDCODED_DEFAULT_MODEL) -> MagicMock:
    """Return a mock Config whose gemini_chat_model returns *chat_model*."""
    cfg = MagicMock()
    cfg.gemini_chat_model = chat_model
    return cfg


class TestMain:
    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_positional_args_joined(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        main(["hello", "world"])
        mock_chat.assert_called_once_with(
            model=HARDCODED_DEFAULT_MODEL,
            query="hello world",
            one_shot=False,
        )

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_no_args_passes_none_query(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        main([])
        mock_chat.assert_called_once_with(
            model=HARDCODED_DEFAULT_MODEL,
            query=None,
            one_shot=False,
        )

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_model_option(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        main(["--model", "gemini-2.5-pro", "test"])
        mock_chat.assert_called_once_with(
            model="gemini-2.5-pro",
            query="test",
            one_shot=False,
        )

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_one_shot_flag(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        main(["--one-shot", "question"])
        mock_chat.assert_called_once_with(
            model=HARDCODED_DEFAULT_MODEL,
            query="question",
            one_shot=True,
        )

    @patch("aurumaide.__main__.get_config")
    @patch(
        "builtins.open",
        mock_open(read_data="  query from file  \n"),
    )
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_file_option(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        main(["--file", "query.txt"])
        mock_chat.assert_called_once_with(
            model=HARDCODED_DEFAULT_MODEL,
            query="query from file",
            one_shot=False,
        )

    def test_file_with_positional_args_errors(self):
        with pytest.raises(SystemExit, match="2"):
            main(["--file", "query.txt", "extra"])

    def test_one_shot_without_query_errors(self):
        with pytest.raises(SystemExit, match="2"):
            main(["--one-shot"])

    @patch(
        "builtins.open",
        mock_open(read_data="   \n  "),
    )
    def test_one_shot_with_empty_file_errors(self):
        with pytest.raises(SystemExit, match="2"):
            main(["--one-shot", "--file", "empty.txt"])

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_calls_initialize(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        main(["--one-shot", "q"])
        mock_init.assert_called_once()

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_returns_zero(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config()
        assert main(["--one-shot", "q"]) == 0

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_config_model_fallback(self, mock_init, mock_chat, mock_gc):
        mock_gc.return_value = _mock_config("custom-from-config")
        main(["--one-shot", "q"])
        mock_chat.assert_called_once_with(
            model="custom-from-config",
            query="q",
            one_shot=True,
        )

    @patch("aurumaide.__main__.get_config")
    @patch("aurumaide.__main__.chat")
    @patch("aurumaide.__main__.initialize")
    def test_hardcoded_fallback_when_config_empty(
        self, mock_init, mock_chat, mock_gc
    ):
        mock_gc.return_value = _mock_config("")
        main(["--one-shot", "q"])
        mock_chat.assert_called_once_with(
            model=HARDCODED_DEFAULT_MODEL,
            query="q",
            one_shot=True,
        )
