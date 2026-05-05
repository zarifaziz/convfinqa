# LLM Recommendation for ConvFinQA (May 2026)

The most directly relevant evaluation is **FinanceReasoning** (238 multi-step financial reasoning questions, similar in spirit to ConvFinQA). **FinanceBench** (10-K-style filing QA) is included as a secondary reference since some models only publish there.

## Top performers — financial reasoning benchmarks

| Model | FinanceReasoning acc. | Tokens used | Notes |
| --- | --- | --- | --- |
| GPT-5 (2025-08-07) | 88.2% | 830K | Highest raw accuracy; ~8x more tokens than Claude Opus 4.7 |
| Claude Opus 4.6 | 87.8% | 164K | Near-top accuracy, ~5x fewer tokens than GPT-5 |
| GPT-5-mini | 87.4% | 596K | Cheaper GPT-5 family |
| Gemini 3.1 Pro Preview | 86.5% | 475K | Solid; some pricing advantages |
| Claude Opus 4.7 | 85.3% | 103K | Most token-efficient top-tier model |
| Claude Opus 4.5 | 84.0% | 145K | |
| Gemini 3-Flash | 83.6% | 119K | Strongest "fast/cheap" tier |

On **FinanceBench** (separate, document-grounded QA) o3 leads (~90%), with GPT-5 ~88%, GPT-4.1 ~85%, Claude Opus 4 ~82%.

## Decision

Primary model: **Claude Sonnet 4.6**. Same model used for dev iteration and full measurement runs.

Initial pick was **Opus 4.7** on the strength of the table above, with **Haiku 4.5** as a cheaper dev-iteration tier. Walked back both before the first full-dev run:

- **Opus was too expensive at this volume.** A full-dev run is ~5M input + ~270k output tokens across 421 records. Opus 4.7 list pricing put a single run well above the self-imposed $20 cost cap. Sonnet 4.6 came in at $19.04 (under cap); FinanceReasoning accuracy is a few points lower than Opus — acceptable trade against the cost delta.
- **No separate dev-iteration tier needed.** Sonnet is cheap enough to iterate against directly. Adding Haiku would have introduced a quality / behaviour mismatch between iteration and measurement runs without a meaningful cost saving.

Carried over from the original rationale:

- Single-provider (Anthropic SDK) setup avoids defending a multi-provider comparison in the report.
- Native tool use and structured outputs suit the typed `submit_answer` approach.

Dropped from the original rationale:

- Extended thinking. Attempted in v2; aborted because the Anthropic SDK rejects `thinking` blocks combined with forced single-tool selection. Documented in REPORT.md → Future work.

## Sources

- [Awesome Agents — Finance LLM Leaderboard 2026](https://awesomeagents.ai/leaderboards/finance-llm-leaderboard/)
- [AIMultiple — Benchmark of 38 LLMs in Finance](https://aimultiple.com/finance-llm)
- [Artificial Analysis — LLM Leaderboard](https://artificialanalysis.ai/leaderboards/models)
- [Finance Arena — FinanceQA Leaderboard](https://www.financearena.ai/)
- [Open FinLLM Leaderboard (HuggingFace)](https://huggingface.co/blog/leaderboard-finbench)
- [LLM Stats — Best AI for Math 2026](https://llm-stats.com/leaderboards/best-ai-for-math)
