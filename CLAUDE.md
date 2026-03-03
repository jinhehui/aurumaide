# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AurumAide is a personal AI assistant (Aurum = gold + Aide = helper) powered by Google Generative AI with MCP support and TeamCity integration. Python 3.12+, pre-alpha status.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest                          # all tests (verbose by default via addopts)
pytest tests/test_config.py     # single test file
pytest tests/test_config.py::TestConfig::test_method  # single test method

# Lint & format
ruff check .                    # lint
ruff check --fix .              # lint with auto-fix
ruff format .                   # format

# Type checking
mypy src                        # strict mode enabled
```

## Architecture

### Source Layout (`src/aurumaide/`)

- **`__main__.py`** — CLI entry point. `build_parser()` creates the argparse parser; `main()` resolves model from CLI > config > hardcoded default, then calls `chat()`.
- **`google/chat.py`** — Core chat function. Supports interactive and one-shot modes using `google-genai` SDK with streaming responses. Includes Google Search grounding.
- **`google/mcp.py`** — FastMCP server exposing a `google_ai(query)` tool for MCP clients. Runs via `python -m aurumaide.google.mcp` (stdio transport).
- **`utility/config.py`** — Singleton JSON config manager at `~/.aurumaide/config.json`. Auto-creates with defaults on first access. Sections: `openai`, `gemini`, `teamcity`.
- **`utility/logger.py`** — `ChatLogger` accumulates streaming chunks and saves as timestamped markdown. Also handles home directory resolution: `AURUMAIDE_HOME` env var → nearest `.git` root → `~/.aurumaide` fallback.
- **`utility/output.py`** — `Output` abstract protocol with `write()`/`end()`. `ConsoleOutput` handles streaming display and optional `ChatLogger` integration.
- **`teamcity/client.py`** — TeamCity REST API client using bearer token authentication. Frozen dataclasses for models (`Project`, `Build`). Custom exception hierarchy: `TeamCityError` → `TeamCityAPIError`.
- **`teamcity/token.py`** — TeamCity token manager using HTTP basic auth. Creates, lists, and deletes access tokens (`Token` dataclass).

### Key Patterns

- **Strict typing**: mypy strict mode, PEP 561 (`py.typed` marker), frozen dataclasses for data models.
- **Streaming output**: Chat responses stream chunk-by-chunk through `ConsoleOutput.write()` with optional logging.
- **Config cascade**: API keys and settings resolve from env vars → config file → hardcoded defaults.
- **Custom exception hierarchy**: `TeamCityError` base → `TeamCityAPIError(status_code)`.

### Environment Variables

- `GOOGLE_API_KEY` — Google Generative AI API key (required)
- `AURUMAIDE_HOME` — Override home/log directory
- `TEAMCITY_BASE_URL`, `TEAMCITY_TOKEN`, `TEAMCITY_USERNAME`, `TEAMCITY_PASSWORD` — TeamCity credentials

## Tool Configuration

- **ruff**: line-length 88, target py312, lints: E/W/F/I/UP/B/SIM
- **mypy**: strict mode, py312
- **pytest**: testpaths=`tests/`, addopts=`-v`
- **build**: hatchling, wheel packages from `src/aurumaide`
