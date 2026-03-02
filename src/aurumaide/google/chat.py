"""Google Generative AI chat interface."""

import os

from google import genai
from google.genai.chats import Chat
from google.genai import types

from ..utility.config import get_config
from ..utility.logger import ChatLogger
from ..utility.output import ConsoleOutput, Output


def _answer(query: str, session: Chat, output: Output) -> None:
    """Stream a single query/response through *output*."""
    response = session.send_message_stream(query)
    output.logger = ChatLogger(query)

    for chunk in response:
        output.write(chunk.text)
    output.end()


def chat(
    model: str,
    query: str | None = None,
    one_shot: bool = False,
    output: Output | None = None,
) -> None:
    """Run a chat session using the given Google AI model.

    Args:
        model: Google AI model identifier (e.g. ``"gemini-3-flash-preview"``).
        query: Optional initial query. When *None*, goes straight to
            interactive input.
        one_shot: If *True*, answer the query and return immediately.
        output: Streaming output handler. Defaults to ``ConsoleOutput``.
    """
    client = genai.Client(
        api_key=os.getenv("GOOGLE_API_KEY") or get_config().gemini_api_key
    )
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    session = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(tools=[grounding_tool])
    )

    output = output or ConsoleOutput(
        begin_mark="\n--- 👇 Response ---\n",
        end_mark="\n----------------\n"
    )

    if query is not None:
        print(f"🚀 Sending request to {model}...")
        _answer(query, session, output)

    if one_shot:
        return

    while True:
        query = input("\n❓ Your question: ").strip()
        if not query:
            return
        _answer(query, session, output)
