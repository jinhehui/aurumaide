"""MCP server exposing Google AI chat as tools."""

import logging
import os

from google import genai
from google.genai import types
from mcp.server.fastmcp import FastMCP

from ..utility.config import get_config
from ..utility.logger import ChatLogger, initialize

HARDCODED_DEFAULT_MODEL = "gemini-3-flash-preview"

mcp = FastMCP("aurumaide")


def _log(query: str, response: str) -> str:
    """Create a ChatLogger for the given query and response."""
    try:
        logger = ChatLogger(query)
        logger.add(response)
        logger.save()
    except Exception as exc:
        logging.error(f"❌ Failed to log chat content: {exc}")
    return response


@mcp.tool()
def google_ai(query: str) -> str:
    """Ask Google AI (Gemini) a question and get a natural-language answer.

    Use for general knowledge, current events, reasoning, or research.
    The query should be a natural-language question or instruction.
    Returns a markdown-formatted answer (not URLs or search-result snippets).
    """
    cfg = get_config()
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or cfg.gemini_api_key)
    model = cfg.gemini_chat_model or HARDCODED_DEFAULT_MODEL
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    response = client.models.generate_content(
        model=model,
        contents=query,
        config=types.GenerateContentConfig(tools=[grounding_tool])
    )
    return _log(query, response.text or "")


if __name__ == "__main__":
    initialize()
    mcp.run(transport="stdio")
