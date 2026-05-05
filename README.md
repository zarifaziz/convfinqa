# ConvFinQA

An LLM-driven pipeline that answers conversational questions over financial documents from the [ConvFinQA](https://github.com/czyssrs/ConvFinQA) dataset.

## What it does

1. **Load** — parse cleaned ConvFinQA records (text paragraphs + tables + multi-turn Q&A).
2. **Answer** — render each record into a prompt and call Claude with a tool-use loop; the model returns a typed numeric or boolean answer via the `submit_answer` tool.
3. **Evaluate** — score predictions against gold answers with absolute/relative tolerance, then break results down by turn index, question type, gold format, and conditional accuracy (P(correct | previous correct)).

Outputs go to a timestamped `runs/<UTC>/` directory: per-turn predictions, summary metrics, and the full transcript of every model call for later error analysis.

## Tech Stack

- **Python 3.12** with [uv](https://docs.astral.sh/uv/) for dependency management
- **Anthropic SDK** (Claude) for LLM calls, with tool use for structured answer extraction
- **Pydantic** / **pydantic-settings** for typed domain models and config
- **Typer** for the CLI, **Rich** for terminal output, **Loguru** for structured logging
- **Pytest** for tests, **Ruff** + **Mypy** for lint/type checks

## Getting Started

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An Anthropic API key

### Setup

```bash
# install uv
brew install uv

# install dependencies
uv sync

# configure environment
cp .env.example .env
# add ANTHROPIC_API_KEY=...
```

### Run an evaluation

```bash
# score a 50-record sample on the train split
uv run main eval --n 50 --split train

# score a single record
uv run main eval --record-id <record_id>

# full dev split (held-out measurement)
uv run main eval --split dev
```

Each run writes to `runs/<UTC-timestamp>/` with `predictions.jsonl`, `summary.json`, and per-record transcripts.

### Inspect or chat with a single record

```bash
# replay one record's full dialogue, pretty-print predicted vs gold per turn
uv run main inspect "Double_MAS/2012/page_92.pdf"

# free-form REPL over a record (history preserved across turns; `exit` to leave)
uv run main chat "Double_MAS/2012/page_92.pdf"
```

### Inspect failures

```bash
uv run main dump-failures runs/<run-dir>
```

Produces a markdown file of every miss, with the question, gold answer, model answer, and the tool-call trace — the primary input to manual error analysis.

### Run tests

```bash
uv run pytest
```

## Project Structure

```
zarifaziz/
├── src/
│   ├── domain/           # Pydantic models: Record, Conversation, Answer
│   ├── services/         # Pipeline logic: Answerer, Evaluator, LLM client
│   ├── repository/       # Dataset loaders (JSON → domain objects)
│   ├── prompts/          # System prompt + record→prompt rendering
│   ├── tools/            # Anthropic tool-use schemas (submit_answer)
│   ├── eval/             # Metric and breakdown functions
│   ├── cli/              # Typer entrypoints (eval, dump-failures)
│   ├── settings.py       # pydantic-settings config (.env)
│   └── logger.py         # Loguru + run-dir scaffolding
├── tests/                # Pytest suite (parsers, metrics, tool wiring)
├── data/                 # Cleaned ConvFinQA dataset
├── runs/                 # Timestamped evaluation outputs
├── docs/                 # Design notes (model selection, decisions)
├── plans/                # Phase-by-phase build plan
├── REPORT.md             # Findings, error analysis, limitations
└── pyproject.toml
```

## Configuration

Set `ANTHROPIC__API_KEY` in `.env`. Everything else (model, pricing, tolerances, paths) has sensible defaults in [`src/settings.py`](src/settings.py) and only needs overriding if you want to change behavior.

## Report

See [`REPORT.md`](REPORT.md) for the full write-up: approach, evaluation methodology, error taxonomy from manual analysis, and limitations.
