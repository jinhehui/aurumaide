"""Tests for aurumaide.google.chat."""

from unittest.mock import MagicMock, patch

from aurumaide.google.chat import _answer, chat


class _FakeChunk:
    """Mimics a streaming response chunk with a .text attribute."""

    def __init__(self, text: str) -> None:
        self.text = text


class TestAnswer:
    def test_streams_chunks_to_output(self):
        session = MagicMock()
        session.send_message_stream.return_value = [
            _FakeChunk("Hello "),
            _FakeChunk("world"),
        ]
        output = MagicMock()

        _answer("hi", session, output)

        session.send_message_stream.assert_called_once_with("hi")
        assert output.write.call_count == 2
        output.write.assert_any_call("Hello ")
        output.write.assert_any_call("world")
        output.end.assert_called_once()

    def test_sets_logger_on_output(self):
        session = MagicMock()
        session.send_message_stream.return_value = []
        output = MagicMock()

        _answer("query", session, output)

        assert output.logger is not None
        assert output.logger.query == "query"


class TestChat:
    @patch("aurumaide.google.chat.genai")
    def test_one_shot_with_query(self, mock_genai):
        mock_session = MagicMock()
        mock_session.send_message_stream.return_value = [_FakeChunk("answer")]
        mock_genai.Client.return_value.chats.create.return_value = mock_session
        output = MagicMock()

        chat(model="test-model", query="hello", one_shot=True, output=output)

        mock_genai.Client.assert_called_once()
        call_kwargs = mock_genai.Client.return_value.chats.create.call_args
        assert call_kwargs.kwargs["model"] == "test-model"
        assert "config" in call_kwargs.kwargs
        output.write.assert_called_once_with("answer")
        output.end.assert_called_once()

    @patch("aurumaide.google.chat.genai")
    def test_one_shot_without_query(self, mock_genai):
        mock_genai.Client.return_value.chats.create.return_value = MagicMock()
        output = MagicMock()

        chat(model="m", one_shot=True, output=output)

        output.write.assert_not_called()

    @patch("aurumaide.google.chat.genai")
    def test_defaults_to_console_output(self, mock_genai):
        mock_genai.Client.return_value.chats.create.return_value = MagicMock()

        with patch("aurumaide.google.chat.ConsoleOutput") as mock_console:
            chat(model="m", one_shot=True)
        mock_console.assert_called_once()

    @patch("aurumaide.google.chat.genai")
    def test_reads_api_key_from_env(self, mock_genai, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")
        mock_genai.Client.return_value.chats.create.return_value = MagicMock()

        chat(model="m", one_shot=True, output=MagicMock())

        mock_genai.Client.assert_called_once_with(api_key="test-key-123")

    @patch("aurumaide.google.chat.genai")
    @patch("builtins.input", side_effect=["question one", ""])
    def test_interactive_loop(self, mock_input, mock_genai):
        mock_session = MagicMock()
        mock_session.send_message_stream.return_value = [_FakeChunk("resp")]
        mock_genai.Client.return_value.chats.create.return_value = mock_session
        output = MagicMock()

        chat(model="m", output=output)

        # One answer from interactive input, then empty exits
        assert mock_session.send_message_stream.call_count == 1
        mock_session.send_message_stream.assert_called_with("question one")

    @patch("aurumaide.google.chat.genai")
    @patch("builtins.input", side_effect=[""])
    def test_interactive_exits_on_empty(self, mock_input, mock_genai):
        mock_genai.Client.return_value.chats.create.return_value = MagicMock()
        output = MagicMock()

        chat(model="m", output=output)

        output.write.assert_not_called()

    @patch("aurumaide.google.chat.get_config")
    @patch("aurumaide.google.chat.genai")
    def test_falls_back_to_config_api_key(self, mock_genai, mock_gc, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        cfg = MagicMock()
        cfg.gemini_api_key = "config-key-xyz"
        mock_gc.return_value = cfg
        mock_genai.Client.return_value.chats.create.return_value = MagicMock()

        chat(model="m", one_shot=True, output=MagicMock())

        mock_genai.Client.assert_called_once_with(api_key="config-key-xyz")

    @patch("aurumaide.google.chat.genai")
    @patch("builtins.input", side_effect=["q1", "q2", ""])
    def test_interactive_multiple_rounds(self, mock_input, mock_genai):
        mock_session = MagicMock()
        mock_session.send_message_stream.return_value = [_FakeChunk("r")]
        mock_genai.Client.return_value.chats.create.return_value = mock_session
        output = MagicMock()

        chat(model="m", output=output)

        assert mock_session.send_message_stream.call_count == 2

    @patch("aurumaide.google.chat.genai")
    @patch("builtins.input", side_effect=[""])
    def test_query_then_interactive(self, mock_input, mock_genai):
        mock_session = MagicMock()
        mock_session.send_message_stream.return_value = [_FakeChunk("r")]
        mock_genai.Client.return_value.chats.create.return_value = mock_session
        output = MagicMock()

        chat(model="m", query="initial", output=output)

        # Initial query + no interactive (empty input exits)
        assert mock_session.send_message_stream.call_count == 1
        mock_session.send_message_stream.assert_called_with("initial")
