"""Initialization, directory management, and chat logging utilities."""

import logging
import os
from datetime import datetime
from os.path import dirname, realpath

from dotenv import load_dotenv


def get_home_dir() -> str:
    """Return the aurumaide home directory, creating it if needed.

    Resolution order:
        1. ``AURUMAIDE_HOME`` environment variable
        2. Nearest git repository root (walking up from this file)
        3. ``~/.aurumaide`` fallback
    """
    home = os.getenv("AURUMAIDE_HOME") or _find_repository_root()
    if not home:
        user_home = (
            os.getenv("HOME") or os.getenv("USERPROFILE") or os.path.abspath(".")
        )
        home = os.path.join(user_home, ".aurumaide")
    if not os.path.exists(home):
        os.makedirs(home)
    return home


def get_out_dir(name: str | None = None) -> str:
    """Return a subdirectory under the home dir, creating it if needed.

    Args:
        name: Subdirectory name. Defaults to ``"out"``.
    """
    out_dir = os.path.join(get_home_dir(), name or "out")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    return out_dir


def _find_repository_root() -> str | None:
    """Walk up from this module's parent directory to find a ``.git`` root."""
    directory = dirname(dirname(realpath(__file__)))
    while directory:
        if os.path.isdir(os.path.join(directory, ".git")):
            return directory
        parent = dirname(directory)
        if parent == directory:
            return None
        directory = parent
    return None


def get_timestamp(timespec: str = "milliseconds") -> str:
    """Return a filesystem-safe ISO timestamp (colons replaced by hyphens).

    Args:
        timespec: Precision passed to ``datetime.isoformat``.
    """
    return datetime.now().isoformat(timespec=timespec).replace(":", "-")


def save_output(base_name: str, text: str) -> str:
    """Save *text* to ``{out_dir}/{base_name}-{timestamp}.md``."""
    out_dir = get_out_dir()
    stamp = get_timestamp()
    path = os.path.join(out_dir, f"{base_name}-{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class ChatLogger:
    """Accumulates streaming chat chunks and persists them as markdown."""

    def __init__(self, user_query: str) -> None:
        self.query = user_query
        self.answers: list[str] = []
        self.last_saved_file: str | None = None

    def add(self, content: str) -> None:
        """Append a response chunk."""
        self.answers.append(content)

    def save(self) -> None:
        """Write the conversation to a timestamped file. No-op if empty."""
        if not self.answers:
            return
        text = f"User: {self.query}\n\nAssistant: " + "".join(self.answers)
        self.last_saved_file = save_output("chat", text)


def initialize(
    log_level: int = logging.INFO,
    log_file_base_name: str = "logger",
    log_file_dir: str | None = None,
) -> None:
    """Load ``.env`` and configure file logging."""
    load_dotenv()

    log_dir = log_file_dir or get_out_dir()
    stamp = get_timestamp()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(
                os.path.join(log_dir, f"{log_file_base_name}-{stamp}.log")
            ),
        ],
    )
    logging.getLogger().setLevel(log_level)
