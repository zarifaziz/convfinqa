# ConvFinQA Report

## Method

End-to-end pipeline: load → render → prompt → forced tool-use → parse → score. One LLM provider (Anthropic, `claude-sonnet-4-6`), one tool (`submit_answer`), full conversation replay. The document goes only in the system prompt; prior turns replay as `(user, q) → (assistant, tool_use) → (user, [tool_result, next_question])` triples. No fine-tuning, no custom retrieval, no agent loop. The 2022 paper's DSL is treated as eval metadata, not a generation target.

The model receives a markdown rendering of the table plus the pre/post narrative; cells pass through verbatim ("do nothing" cleaning policy — see [docs/decisions.md](docs/decisions.md)). Forced `tool_choice` collapses output parsing to schema validation: the response either carries a `submit_answer` block matching the Pydantic schema or surfaces a hard error.

Architecture: `domain / services / repository` layering. `LLMClient` and `DatasetRepository` are `Protocol`s; the concrete `AnthropicClient` and `JsonDatasetRepository` are the only production adapters. Tests substitute a `_FakeLLMClient`, no API key required. Predictions and per-call audit trails persist to `runs/<UTC-timestamp>/{predictions.jsonl, transcripts.jsonl, transcripts.md, summary.json}`.

## Eval methodology

Four metrics on the dev split, each reported with sample sizes alongside the rate:

- **Per-turn execution accuracy** — fraction of turns where `compare_answer` returned True. The standard ConvFinQA metric; reported for comparability with the literature.
- **Per-conversation accuracy** — fraction of records where every turn was correct. Surfaces compounding: 85% per-turn compounds to ~52% per-conversation on a 4-turn dialogue. The customer-facing number.
- **Conditional accuracy** `P(turn_i correct | turn_{i-1} correct)`, reported as a per-index curve. Disambiguates cascade failure (later turn wrong because earlier turn propagated) from intrinsic late-turn difficulty (model degrades on long context). These warrant different fixes; without conditional, the per-turn-index curve is not actionable.
- **Per-turn-index accuracy curve** — accuracy at each turn position. Plot data for the late-turn-collapse analysis.

Three breakdowns surface the dataset's known difficulty axes:

- **Type I vs Type II** (from `features.has_type2_question`): the paper (sec 5.3, 6.3) calls Type II the harder subset.
- **Numeric vs boolean** (from gold type): ~44/14k turns are boolean ("yes"/"no"); a different reasoning path that would otherwise hide in the aggregate.
- **`has_duplicate_columns` / `has_non_numeric_values`**: validates the "do nothing" cleaning policy by checking accuracy on records the dataset card flags as residue cases.

`compare_answer` uses hybrid tolerance `max(tol_abs, tol_rel * |gold|)` with `tol_abs=1e-4`, `tol_rel=5e-3`. Rationale and trigger to revisit are in [docs/decisions.md](docs/decisions.md).

Cost reporting (token totals, USD estimate, mean latency by turn index, mean input tokens by turn index) ships in `summary.json` for every run. Pricing source: Sonnet 4.6 list price, $3/MTok input, $15/MTok output, configured via `AnthropicSettings`.

## Intermediary findings (n=50 dev sample, seed=1002385739)

| Metric | Value |
|---|---|
| Per-turn accuracy | 80.9% (157/194) |
| Per-conversation accuracy | 70.0% (35/50) |
| Per-turn-index curve | t0=82%, t1=84%, t2=80.5%, t3=75.8%, t4=81.2%, t5=75% |
| Conditional `P(t_i \| t_{i-1})` | t1=97.6%, t2=85.3%, t3=84.6%, t4=92.3%, t5=66.7% |

**The conditional curve is essentially flat at ~85% across t1–t4.** Combined with the per-turn-index curve also being roughly flat (75–84% across all positions), this is evidence that **cascade failure is not the dominant bottleneck** at this sample size. The drop in per-turn accuracy with position is largely the expected `1 - (1-p)^k` compounding, not a model-degradation effect on long context. This finding shapes future work: time spent on context summarization or retrieval would not target the actual failure mode.

**Cost (extrapolated from n=50)**: ~$0.009 per turn, full dev (~1500 turns) ≈ $13–14, ~75 minutes wall sequential. Mean input tokens grow from ~2.1k at t0 to ~3k+ at later turns as prior history replays — the lever for prompt caching as a future optimization.

## Error analysis (preliminary, eyeballed on n=50)

Three failure clusters surfaced; phase 4 will quantify them on the full-dev predictions.

1. **Sign-from-cleaning artifact.** Records where the cleaned table stored parenthesised numbers as negatives (PNC commitment percentages, PM/2015 cash flows). The model faithfully reads the negative value, but `executed_answers` carries the positive magnitude. A dataset cleaning policy mismatch, not a model error. Visible on `Single_PM/2018/page_31.pdf-2`, `Double_PM/2015/page_127.pdf`, `Single_AAP/2011/page_28.pdf-1`.
2. **Dialogue order misresolution.** Hybrid Type II conversations occasionally swap the answers for two adjacent questions about different years (`Double_ETR/2002/page_86.pdf` swaps 2001 and 2002 net income). The model has the right cells but maps them to the wrong question. A real reasoning error.
3. **Unit / scale confusion at extraction.** Off-by-10× errors on percent-vs-decimal questions (`Single_GS/2012/page_165` predicts 202.34 when gold is 20.234). The system prompt's unit guidance helps but doesn't eliminate this class.

## Limitations

- **Dev is the only held-out split in the shipped JSON.** The 434-record test split advertised in the dataset card is absent. Dev was used both as the evaluation set and (lightly) as the prompt-iteration set; the headline number is "best-effort on dev," not a true held-out estimate. See `docs/decisions.md` "Dev as held-out".
- **n=50 numbers come with ±~10pt CIs at 95% for rates near 0.8.** The full-dev run is the headline; n=50 was a smoke check, not the report number.
- **Some failures are dataset cleaning artifacts** (cluster 1 above), not model errors. Reporting raw accuracy charges these against the model unfairly. Phase 4 will distinguish.
- **No prompt caching.** Mean input tokens grow ~50% from t0 to t5; a stable system block would be cacheable. Not implemented in v1.

## Future work

Ordered by ROI given the actual failure modes observed:

1. **Prompt caching on the system block.** The doc + instructions are stable across turns of one record; today they're re-tokenized on every call. The token-by-turn-idx evidence in `summary.json` is the empirical justification.
2. **Dataset-cleaning audit on flagged records.** Sign-from-cleaning is a systemic upstream issue. Either treat as out-of-scope (document and exclude), or invert the sign per cell where pre/post-text language indicates a negative-as-magnitude convention.
3. **Tighter gold-format inference in `compare_answer`** — the metric currently dispatches on `isinstance(gold, str)`; a few boolean records have non-string golds. Phase 4 may surface enough of these to warrant a tighter rule.
4. **Targeted few-shot for hybrid Type II** if cluster 2 (dialogue order misresolution) dominates phase-4 error analysis. One or two in-context examples of "the question references the *earlier* year" would likely close it. Not added preemptively — error analysis first.
5. **`calculate(expression)` tool with a return loop** if arithmetic errors materially exceed extraction errors. Currently `calc_consistent` (model's reported answer matches eval of its own calculation string) appears high by eyeball; will verify in phase 4 before adding tool surface.

What this report deliberately does **not** propose: fine-tuning, custom retrieval, multi-provider comparison, agentic planning. ConvFinQA documents are short (~675 tokens median) and reasoning is shallow (median 2–3 ops). The interesting engineering is honest evaluation, not architectural maximalism.

## Reproducing the run

```
uv run pytest                                 # 45 tests
uv run main --n 50 --seed 1002385739          # the smoke run reported above
uv run main                                   # full dev (~75 min, ~$13)
uv run main --verbose                         # adds the per-row table
```

Outputs land in `runs/<UTC-timestamp>/`. `predictions.jsonl` is the per-turn detail; `summary.json` is the aggregate; `transcripts.{jsonl,md}` is the per-call audit trail.

## AI tool usage

Built with Claude Code as a pair-programming assistant, under explicit project-level conventions in `CLAUDE.md` and `CLAUDE.local.md`. The conventions are load-bearing: TDD, small reviewable changes, no AI-tells in checked-in content, no docstrings on the obvious. Sub-agents were used for parallel research (Anthropic API contract validation, metrics-math audit, code review) and for exploratory fan-out, but every line of code in `src/` was reviewed before commit. Plans in `plans/` were drafted collaboratively and edited; decisions in `docs/decisions.md` are the durable record of the calls made.
