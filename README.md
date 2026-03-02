# AurumAide

Personal AI assistant — **Aurum** (Latin for *gold*) + **Aide** (helper).

Powered by Google Generative AI.

## Prerequisites

- Python 3.12+
- A [Google AI API key](https://aistudio.google.com/apikey) set in a `.env` file or as an environment variable

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

pip install -e ".[dev]"
```

## Usage

```
aurumaide [options] [arguments...]
```

Positional arguments are joined by spaces to form the initial query.
Without a query the assistant starts in interactive mode.

### Options

| Option | Description |
|---|---|
| `--model MODEL` | Google AI model to use (default: `gemini-2.0-flash`) |
| `--one-shot` | Answer the query and exit (requires a query) |
| `--file FILE_PATH` | Read the query from a file (cannot be combined with positional arguments) |

### Examples

```bash
# Interactive chat
aurumaide

# Ask a question and continue chatting
aurumaide What is the meaning of life

# One-shot: get an answer and exit
aurumaide --one-shot Explain the Python GIL

# Use a specific model
aurumaide --model gemini-2.5-pro Tell me about quantum computing

# Read the query from a file
aurumaide --one-shot --file query.txt
```

## Development

```bash
# Run tests
pytest

# Lint & format
ruff check .
ruff format .

# Type checking
mypy src
```

## License

[MIT](LICENSE)
