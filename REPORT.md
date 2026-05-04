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

Eval is **free-running**, not teacher-forced: each turn sees the model's own prior predictions in the replayed history, not the gold answers. This is stricter than the FinQA / ConvFinQA paper baselines, which inject gold prior turns — so the headline number is not directly comparable to the 45–69% Exe Acc figures in [dataset.md](dataset.md#L65-L70). Free-running is the deployment-shaped metric; teacher-forced would isolate per-turn skill but hide compounding.

`compare_answer` uses hybrid tolerance `max(tol_abs, tol_rel * |gold|)` with `tol_abs=1e-4`, `tol_rel=5e-3`. Rationale and trigger to revisit are in [docs/decisions.md](docs/decisions.md).

Cost reporting (token totals, USD estimate, mean latency by turn index, mean input tokens by turn index) ships in `summary.json` for every run. Pricing source: Sonnet 4.6 list price, $3/MTok input, $15/MTok output, configured via `AnthropicSettings`.

## Dev measurement manifest

Append-only. Dev is the held-out measurement set; the table below records every prompt version measured against it. Iteration is driven by **train** failure analysis between rows; dev failures are not consulted to choose interventions. Hard cap at v2.

| Version | Prompt git tag | Seed | Per-turn | Per-conv | USD | Wall | Notes |
|---|---|---|---|---|---|---|---|
| v0 | `prompt-v0` | 1002385739 | _pending_ | _pending_ | _pending_ | _pending_ | Baseline, full dev (421 records) |
| v1 | `prompt-v1` | 1002385739 | _pending_ | _pending_ | _pending_ | _pending_ | After Phase 2.5 train iteration |
| v2 | `prompt-v2` | 1002385739 | _pending_ | _pending_ | _pending_ | _pending_ | Optional second iteration cycle |

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

1. **Magnitude-vs-signed reasoning on financial sign conventions** (model failure, ~7 turns / n=194 in the n=50 smoke set ≈ 3.6% accuracy headroom). The cleaner deterministically maps parens → negative, faithful to one common 10-K convention; the other (parens-as-display, with the question framing implying magnitude) is the model's job to resolve from semantics. Concrete: `Single_PM/2018/page_31.pdf-2` t0 — *"what was the weighted average discount rate for postretirement plans in 2018?"*, cell `-3.97`, gold `3.97`. `Double_PM/2015/page_127.pdf` t0 — column header `( losses ) earnings 2015`, cell `-9402`, question asks for "the losses", gold `9402`. The model returns the signed cell verbatim instead of resolving "is the question asking for a magnitude or a signed value?". A counter-pattern exists: `Single_C/2010/page_223.pdf-3` t2 — *"what is the net difference?"*, gold `-433`, model returns `433`. So the model's bias isn't "always signed" — it's "follow the cell's sign or the arithmetic's sign without checking the question." This rules out a blanket "return magnitude" rule and motivates a structural prompt change (force-the-decision via the tool schema) over a lexical one. See future work item 2.

2. **Cleaned-table / gold misalignment** (data artifact). On `Double_ETR/2002/page_86.pdf` the column header is `$ 1150786` (a value, not a year — OCR cruft) and the row-label-to-value mapping disagrees with how gold was generated: cleaned table has `2005=540372, 2004=925005`, but gold treats `540372` as 2004 (confirmed by t3 gold `0.71179 = 384633 / 540372`). No question-side semantic cue lets the model recover this; *"what was the total in 2005?"* against a table that pins `2005=540372` admits exactly one answer. This cluster is unrecoverable from the model side and should be surfaced as a contamination axis at metric time, not absorbed into the headline.

3. **Unit / scale confusion at extraction** (model failure). Off-by-10× errors on percent-vs-decimal questions (`Single_GS/2012/page_165` predicts 202.34 when gold is 20.234). The system prompt's unit guidance helps but doesn't eliminate this class.

Clusters 1 and 3 are model-side; cluster 2 is data-side. The dominant intervention from here is on the model side — a prompt-engineering pass that primes financial-statement reading conventions and forces an explicit "magnitude vs signed" decision before extraction. Phase 4 will quantify the share of each cluster on full-dev so the prompt iteration is aimed at the dominant mode rather than the most memorable one.

## Limitations

- **Dev is the only held-out split in the shipped JSON.** The 434-record test split advertised in the dataset card is absent. Dev was used both as the evaluation set and (lightly) as the prompt-iteration set; the headline number is "best-effort on dev," not a true held-out estimate. See `docs/decisions.md` "Dev as held-out".
- **n=50 numbers come with ±~10pt CIs at 95% for rates near 0.8.** The full-dev run is the headline; n=50 was a smoke check, not the report number.
- **Cluster 2 is a dataset/cleaning artifact** that the model cannot recover from inputs alone. Reporting raw accuracy charges those records against the model unfairly. Phase 4 will surface them as a separate breakdown axis.
- **No prompt caching.** Mean input tokens grow ~50% from t0 to t5; a stable system block would be cacheable. Not implemented in v1.

## Future work

Ordered by ROI given the actual failure modes observed:

1. **Prompt caching on the system block.** The doc + instructions are stable across turns of one record; today they're re-tokenized on every call. The token-by-turn-idx evidence in `summary.json` is the empirical justification.
2. **Prompt pass for financial-statement reading conventions.** Cluster 1 is the largest model-side failure mode visible in the n=50 sample. The fix isn't an enumerated rule list (`if discount-rate then flip`) — that doesn't generalize and risks corrupting cells that are legitimately negative. The fix is to make magnitude-vs-signed an explicit step the model takes before extraction, primed by domain context (parens-as-display vs parens-as-negative; cells under a "loss" header represent negative earnings impact, the magnitude *is* the loss). See "Prompt iteration plan" below.
3. **Tighter gold-format inference in `compare_answer`** — the metric currently dispatches on `isinstance(gold, str)`; a few boolean records have non-string golds. Phase 4 may surface enough of these to warrant a tighter rule.
4. **Quarantine flag for cleaning-artifact records.** If clusters 1+2 account for a meaningful share of residual error in phase 4, surface them as a separate axis in the breakdown rather than charging them against model accuracy. The fix is upstream of the model — flag-and-exclude is more honest than silently absorbing the loss.
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
