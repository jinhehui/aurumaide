"""Tests for aurumaide.google.mcp."""

from unittest.mock import MagicMock, patch

from aurumaide.google.mcp import HARDCODED_DEFAULT_MODEL, _log, google_ai


class TestLog:
    @patch("aurumaide.google.mcp.ChatLogger")
    def test_saves_query_and_response(self, mock_cls):
        logger = MagicMock()
        mock_cls.return_value = logger

        result = _log("my query", "my response")

        mock_cls.assert_called_once_with("my query")
        logger.add.assert_called_once_with("my response")
        logger.save.assert_called_once()
        assert result == "my response"

    @patch("aurumaide.google.mcp.ChatLogger")
    def test_returns_response_on_logger_error(self, mock_cls):
        mock_cls.side_effect = RuntimeError("disk full")

        result = _log("q", "answer")

        assert result == "answer"

    @patch("aurumaide.google.mcp.ChatLogger")
    def test_returns_response_on_save_error(self, mock_cls):
        logger = MagicMock()
        logger.save.side_effect = OSError("write failed")
        mock_cls.return_value = logger

        result = _log("q", "answer")

        assert result == "answer"


class TestGoogleAi:
    @patch("aurumaide.google.mcp._log", side_effect=lambda q, r: r)
    @patch("aurumaide.google.mcp.genai")
    @patch("aurumaide.google.mcp.get_config")
    def test_returns_response_text(
        self, mock_gc, mock_genai, mock_log, monkeypatch
    ):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        cfg = MagicMock()
        cfg.gemini_chat_model = ""
        cfg.gemini_api_key = "fake-key"
        mock_gc.return_value = cfg

        mock_response = MagicMock()
        mock_response.text = "Paris is the capital of France."
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        result = google_ai("What is the capital of France?")

        assert result == "Paris is the capital of France."

    @patch("aurumaide.google.mcp._log", side_effect=lambda q, r: r)
    @patch("aurumaide.google.mcp.genai")
    @patch("aurumaide.google.mcp.get_config")
    def test_uses_hardcoded_model_when_config_empty(
        self, mock_gc, mock_genai, mock_log, monkeypatch
    ):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        cfg = MagicMock()
        cfg.gemini_chat_model = ""
        cfg.gemini_api_key = "k"
        mock_gc.return_value = cfg

        mock_genai.Client.return_value.models.generate_content.return_value = (
            MagicMock(text="")
        )

        google_ai("q")

        call_kwargs = (
            mock_genai.Client.return_value.models.generate_content.call_args
        )
        assert call_kwargs.kwargs["model"] == HARDCODED_DEFAULT_MODEL

    @patch("aurumaide.google.mcp._log", side_effect=lambda q, r: r)
    @patch("aurumaide.google.mcp.genai")
    @patch("aurumaide.google.mcp.get_config")
    def test_uses_config_model(
        self, mock_gc, mock_genai, mock_log, monkeypatch
    ):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        cfg = MagicMock()
        cfg.gemini_chat_model = "custom-model"
        cfg.gemini_api_key = "k"
        mock_gc.return_value = cfg

        mock_genai.Client.return_value.models.generate_content.return_value = (
            MagicMock(text="")
        )

        google_ai("q")

        call_kwargs = (
            mock_genai.Client.return_value.models.generate_content.call_args
        )
        assert call_kwargs.kwargs["model"] == "custom-model"

    @patch("aurumaide.google.mcp._log", side_effect=lambda q, r: r)
    @patch("aurumaide.google.mcp.genai")
    @patch("aurumaide.google.mcp.get_config")
    def test_uses_env_api_key_over_config(
        self, mock_gc, mock_genai, mock_log, monkeypatch
    ):
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        cfg = MagicMock()
        cfg.gemini_chat_model = "m"
        cfg.gemini_api_key = "config-key"
        mock_gc.return_value = cfg

        mock_genai.Client.return_value.models.generate_content.return_value = (
            MagicMock(text="")
        )

        google_ai("q")

        mock_genai.Client.assert_called_once_with(api_key="env-key")

    @patch("aurumaide.google.mcp._log", side_effect=lambda q, r: r)
    @patch("aurumaide.google.mcp.genai")
    @patch("aurumaide.google.mcp.get_config")
    def test_falls_back_to_config_api_key(
        self, mock_gc, mock_genai, mock_log, monkeypatch
    ):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        cfg = MagicMock()
        cfg.gemini_chat_model = "m"
        cfg.gemini_api_key = "config-key"
        mock_gc.return_value = cfg

        mock_genai.Client.return_value.models.generate_content.return_value = (
            MagicMock(text="")
        )

        google_ai("q")

        mock_genai.Client.assert_called_once_with(api_key="config-key")

    @patch("aurumaide.google.mcp._log", side_effect=lambda q, r: r)
    @patch("aurumaide.google.mcp.genai")
    @patch("aurumaide.google.mcp.get_config")
    def test_passes_query_and_response_to_log(
        self, mock_gc, mock_genai, mock_log, monkeypatch
    ):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        cfg = MagicMock()
        cfg.gemini_chat_model = "m"
        cfg.gemini_api_key = "k"
        mock_gc.return_value = cfg

        mock_genai.Client.return_value.models.generate_content.return_value = (
            MagicMock(text="answer")
        )

        google_ai("question")

        mock_log.assert_called_once_with("question", "answer")
