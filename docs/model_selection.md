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

Primary model: **Claude Opus 4.7**. Dev-iteration model: **Claude Haiku 4.5**.

Rationale:

- Anthropic SDK is the stated default for this repo, so a single-provider setup avoids defending a multi-provider comparison in the report.
- Best accuracy-per-token in the top tier (~3 points behind GPT-5 at ~1/8 the tokens), which matters across an eval harness over hundreds of examples.
- Native tool use and structured outputs are mature, suiting the Program-of-Thought approach (model emits Python, executor runs it).
- Extended thinking is a clean config knob, supporting a defensible "thinking on vs. off" ablation.

## Sources

- [Awesome Agents — Finance LLM Leaderboard 2026](https://awesomeagents.ai/leaderboards/finance-llm-leaderboard/)
- [AIMultiple — Benchmark of 38 LLMs in Finance](https://aimultiple.com/finance-llm)
- [Artificial Analysis — LLM Leaderboard](https://artificialanalysis.ai/leaderboards/models)
- [Finance Arena — FinanceQA Leaderboard](https://www.financearena.ai/)
- [Open FinLLM Leaderboard (HuggingFace)](https://huggingface.co/blog/leaderboard-finbench)
- [LLM Stats — Best AI for Math 2026](https://llm-stats.com/leaderboards/best-ai-for-math)
