"""Tests for aurumaide.utility.output."""

from unittest.mock import MagicMock, call, patch

from aurumaide.utility.logger import ChatLogger
from aurumaide.utility.output import ConsoleOutput


class TestConsoleOutput:
    def test_write_prints_chunk(self):
        out = ConsoleOutput()
        with patch("builtins.print") as mock_print:
            out.write("hello")
        mock_print.assert_any_call("hello", end="", flush=True)

    def test_write_prints_begin_mark_on_first_call(self):
        out = ConsoleOutput(begin_mark=">>> ")
        with patch("builtins.print") as mock_print:
            out.write("first")
        assert mock_print.call_args_list == [
            call(">>> ", end="", flush=True),
            call("first", end="", flush=True),
        ]

    def test_write_begin_mark_only_once(self):
        out = ConsoleOutput(begin_mark=">>> ")
        with patch("builtins.print") as mock_print:
            out.write("first")
            out.write("second")
        # begin_mark printed once, then two chunks
        assert mock_print.call_args_list == [
            call(">>> ", end="", flush=True),
            call("first", end="", flush=True),
            call("second", end="", flush=True),
        ]

    def test_write_logs_when_logger_set(self):
        logger = MagicMock(spec=ChatLogger)
        out = ConsoleOutput(logger=logger)
        with patch("builtins.print"):
            out.write("data")
        logger.add.assert_called_once_with("data")

    def test_write_no_log_without_logger(self):
        out = ConsoleOutput()
        with patch("builtins.print"):
            out.write("data")
        # No error — just verifies it doesn't crash

    def test_end_prints_end_mark(self):
        out = ConsoleOutput(end_mark="\n---")
        with patch("builtins.print") as mock_print:
            out.write("x")
            mock_print.reset_mock()
            out.end()
        mock_print.assert_called_once_with("\n---", end="", flush=True)

    def test_end_resets_started(self):
        out = ConsoleOutput()
        with patch("builtins.print"):
            out.write("x")
            assert out.started is True
            out.end()
            assert out.started is False

    def test_end_saves_and_clears_logger(self):
        logger = MagicMock(spec=ChatLogger)
        logger.last_saved_file = "/fake/path/chat.md"
        out = ConsoleOutput(logger=logger)
        with patch("builtins.print"):
            out.write("data")
            out.end()
        logger.save.assert_called_once()
        assert out.logger is None

    def test_end_prints_saved_path(self):
        logger = MagicMock(spec=ChatLogger)
        logger.last_saved_file = "/fake/path/chat.md"
        out = ConsoleOutput(logger=logger)
        with patch("builtins.print") as mock_print:
            out.write("data")
            out.end()
        mock_print.assert_any_call(
            "\U0001f4be Conversation saved to /fake/path/chat.md"
        )

    def test_end_no_print_when_save_empty(self):
        logger = MagicMock(spec=ChatLogger)
        logger.last_saved_file = None
        out = ConsoleOutput(logger=logger)
        with patch("builtins.print") as mock_print:
            out.write("data")
            out.end()
        for c in mock_print.call_args_list:
            assert "\U0001f4be" not in str(c)

    def test_end_noop_when_not_started(self):
        logger = MagicMock(spec=ChatLogger)
        out = ConsoleOutput(logger=logger)
        with patch("builtins.print") as mock_print:
            out.end()
        mock_print.assert_not_called()
        logger.save.assert_not_called()

    def test_end_without_logger(self):
        out = ConsoleOutput()
        with patch("builtins.print"):
            out.write("x")
            out.end()  # Should not raise
        assert out.started is False
