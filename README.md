# ConvFinQA: Conversational Financial QA with Frontier LLMs

> A single system prompt, one tool definition, and Claude Sonnet 4.6 score **83.5%** per-turn on the ConvFinQA dev split — **+14.6 points** over the 2022 SOTA pipeline (FinQANet, 68.9%), with no retriever, no DSL, and no fine-tuning.

## TL;DR

[ConvFinQA](https://github.com/czyssrs/ConvFinQA) (Chen et al., 2022) is a benchmark of multi-turn question answering over financial documents — narrative text plus tables, with conversational follow-ups that depend on earlier turns. The 2022 state of the art reached it with a custom retriever, a domain-specific-language generator, and a fine-tuned encoder.

This repo replaces that whole pipeline with one Claude call per turn: render the document into the system prompt, replay the full conversation history, and force a typed `submit_answer` tool. On the 421-record dev split it scores **83.5% per-turn** and **73.6% per-conversation** for **$19.04** and 72 minutes of wall time. The complexity in the original paper was scaffolding for weaker models.

## Background

- **The benchmark.** ConvFinQA tests numerical reasoning over financial filings across a conversation: a model must read a table + surrounding text, then answer a chain of questions where later turns reference earlier answers ("what was the change?", "and as a percentage?").
- **Original SOTA.** The paper's best system, FinQANet, was a *retriever → DSL generator → executor* pipeline with a fine-tuned encoder, reaching **68.9%** execution accuracy on dev. Human experts score **89.4%** (paper, n=200).
- **Hypothesis.** A 2026 frontier LLM with long context and native tool-use might skip the retriever, the DSL, and the fine-tuning entirely — and still win.

## What this repo does

One LLM provider (Anthropic, `claude-sonnet-4-6`), one tool (`submit_answer`), full conversation replay. For each turn:

1. **Render** the document (markdown table + verbatim cells + narrative) into the system prompt — no retriever, because the median document is only ~675 tokens and fits whole.
2. **Replay** prior turns as `(user question) → (assistant tool_use) → (tool_result, next question)` triples, so each turn sees the real dialogue history.
3. **Force tool-use** via `tool_choice`, collapsing output parsing to Pydantic schema validation: the model returns a typed numeric or boolean answer, or it fails loudly.
4. **Score** against gold with hybrid absolute/relative tolerance, then break results down by turn index, question type, gold format, and conditional accuracy.

No fine-tuning, no custom retrieval, no agent loop. The 2022 paper's DSL is treated as eval metadata, not a generation target.

## Results

Dev split (421 records, 1490 turns), `claude-sonnet-4-6`, seed `1002385739`:

| Metric | This repo | Baseline |
|---|---|---|
| **Per-turn accuracy** | **83.5%** (1244/1490) | FinQANet 68.9% · human expert 89.4% |
| **Per-conversation accuracy** | **73.6%** (310/421) | — |
| Type I (single composition) | 85.7% | — |
| Type II (multi-question) | 78.1% | — |
| Cost / wall time | $19.04 · 72 min | — |

Eval setups differ — this run replays the model's *own* prior predictions as history (deployment-realistic), whereas the paper's exact protocol isn't fully specified — so the headline isn't a perfectly controlled comparison. See [REPORT.md](REPORT.md#evaluation-methodology) for the caveats.

## Key findings

- **The paper's "late turns are harder" claim does not reproduce.** Conditional accuracy `P(turn correct | previous correct)` is flat at ~92% from t1 to t5. The drop in per-conversation accuracy with length is independent-error *compounding*, not long-context degradation — long-context training engineered the effect out.
- **Cascade, not degradation, is the residual failure mode.** And at ~3.5 turns per dialogue it's smaller than expected. Time spent on context summarisation or sliding-window prompting would miss the real headroom.
- **Three error clusters dominate the misses**, each needing a different fix: upstream cleaned-table / gold misalignment (data-side), sign-vs-magnitude on financial cell conventions (model-side), and column / row selection on multi-column tables (renderer-side). `has_duplicate_columns` records are the worst slice at 67.2%.
- **Train-side prompt tuning regressed on dev** (-0.8pt). The few-shot examples that helped on train didn't transfer — a reminder that prompt iteration overfits like anything else.

## Quickstart

```bash
# install uv
brew install uv

# install dependencies
uv sync

# configure environment
cp .env.example .env
# add ANTHROPIC_API_KEY=...
```

```bash
# score a 50-record sample on the train split
uv run main eval --n 50 --split train

# full dev split (held-out measurement)
uv run main eval --split dev

# replay one record's dialogue, predicted vs gold per turn
uv run main inspect "Double_MAS/2012/page_92.pdf"

# free-form REPL over a record
uv run main chat "Double_MAS/2012/page_92.pdf"

# dump every miss to markdown for error analysis
uv run main dump-failures runs/<run-dir>

# run tests
uv run pytest
```

Each eval writes to `runs/<UTC-timestamp>/` with `predictions.jsonl`, `summary.json`, and per-record transcripts.

## Project structure

```
├── src/
│   ├── domain/       # Pydantic models: Record, Conversation, Answer
│   ├── services/     # Pipeline: AnswerService, Evaluator, LLM client
│   ├── repository/   # Dataset loaders (JSON → domain objects)
│   ├── prompts/      # System prompt + record→prompt rendering
│   ├── tools/        # Anthropic tool-use schemas (submit_answer)
│   ├── eval/         # Metric and breakdown functions
│   ├── cli/          # Typer subcommands: eval, inspect, chat, scripts
│   └── settings.py   # pydantic-settings config (.env)
├── tests/            # Pytest suite (parsers, metrics, tool wiring)
├── data/             # Cleaned ConvFinQA dataset
├── figures/          # Charts referenced from REPORT.md
├── runs/             # Timestamped evaluation outputs
├── docs/             # Design notes (model selection, decisions)
└── REPORT.md         # Findings, error analysis, limitations
```

## Report

[**REPORT.md**](REPORT.md) is the full write-up: method, evaluation methodology, the paper-rebuttal analysis, the four-cluster error taxonomy from manual review, and limitations. Design rationale lives in [`docs/decisions.md`](docs/decisions.md) and [`docs/model_selection.md`](docs/model_selection.md).

## Citation

```bibtex
@inproceedings{chen2022convfinqa,
  title={ConvFinQA: Exploring the Chain of Numerical Reasoning in Conversational Finance Question Answering},
  author={Chen, Zhiyu and Li, Shiyang and Smiley, Charese and Ma, Zhiqiang and Shah, Sameena and Wang, William Yang},
  booktitle={Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing},
  year={2022}
}
```
