# Design Decisions

## Single forced `submit_answer` tool over agentic calc-loop

Decision: one tool, one round-trip per turn. The model emits `{reasoning, calculation, answer, unit}` and the call ends.

Why: documents average ~675 tokens; multi-hop chains are short (median 2–3 ops in `turn_program`). A multi-step agent loop adds latency, cost, and a debug surface for a problem that does not need it. Forcing the tool also makes structured output reliable without regex over prose.

Alternative: agent loop exposing `calculate(expression)` (and optionally `lookup_table_cell(...)`), looping until `submit_answer`. Closer to a production agent shape.

Trigger to revisit: arithmetic-error bucket exceeds 15% of failures in error analysis, or calc-consistency rate (`eval(calculation) ≈ float(answer)`) drops below 90%.

## Full conversation replay over distilled state

Decision: each turn replays all prior `(user, q) → (assistant, tool_use) → (user, tool_result)` triples in the messages list. The document goes only in the system prompt.

Why: typical conversation is ~3.5 turns of single-line questions. Replay cost is trivial (~190 tokens per prior turn). Distillation introduces a state-tracking layer that drifts, costs more to debug, and gains nothing at this scale.

Alternative: maintain a running compressed "context summary" injected each turn instead of the full history.

Trigger to revisit: conversations grow to 20+ turns, or document size approaches Anthropic context limits. Neither applies to ConvFinQA as released.

## Hybrid tolerance: `max(tol_abs, tol_rel * |gold|)`

Decision: `compare_answer` uses `tol_abs=1e-4` and `tol_rel=5e-3` (0.5% relative), comparing as `abs(diff) <= max(tol_abs, tol_rel * |gold|)`.

Why: gold values span six orders of magnitude (e.g. `0.14136` and `206588`). A flat `1e-3` absolute would be 10% relative on the small percent and absurdly tight on the integer. Display rounding (gold `0.14136` vs predicted `"14.1%"` → 0.141, diff 3.6e-4) needs the relative term; near-zero golds need the absolute term.

Alternative: pure absolute tolerance, or pure relative.

Trigger to revisit: error analysis shows "format-correct, slightly off" as the dominant failure bucket — tighten or loosen `tol_rel` and re-run.

## Dev as held-out, no test split in the file

Decision: report dev accuracy as the headline. State explicitly in `REPORT.md` that dev is also the iteration set, so the headline is not a true held-out estimate.

Why: the dataset card advertises a 434-record test split that is not present in the shipped JSON. Pretending otherwise would mislead. Carving a final held-out slice from train would shrink the few-shot pool and add methodology overhead disproportionate to a 15-hour prototype.

Alternative: carve ~100 records from train as a final held-out set; iterate on dev; report on the held-out.

Trigger to revisit: result is published as a benchmark claim rather than a take-home prototype.

## Conditional accuracy as a headline metric, not just a slice

Decision: report `P(turn_i correct | turn_{i-1} correct)` as a per-index curve in `summary.json` and the CLI output, alongside per-turn execution accuracy and per-conversation accuracy.

Why: per-turn accuracy and a per-turn-index curve together cannot tell the difference between (a) cascade failure — later turns wrong because earlier turns propagated — and (b) intrinsic late-turn difficulty — the model degrading on long context. These two failure modes warrant different fixes (cascade → tighten upstream prompt; degradation → context summarization or retrieval). Conditional accuracy collapses the ambiguity: a flat curve points to cascade; a falling curve points to degradation. On the n=50 sample the curve is flat at ~85%, which is the evidence the report uses to *not* invest in retrieval or summarization.

Alternative: report only per-turn and per-conversation accuracy plus the per-turn-index curve, and rely on manual error analysis to attribute failure mode.

Trigger to revisit: full-dev curve is steeply falling (e.g. drops below 60% at t≥3) — investigate whether the prompt template is degrading or whether cascade is overwhelming the metric.

## Sample sizes disclosed alongside every rate

Decision: every rate in `summary.json` is a `{correct, n, accuracy}` triple, not a bare float. Per-turn-idx, conditional, type I/II, gold-format, and doc-feature breakdowns all carry their `n`.

Why: late-turn buckets and rare-feature buckets routinely have n<10 on smaller runs. A rendered "100%" at n=3 reads identically to a "100%" at n=200. Disclosing `n` is the cheap honesty mechanism; without it the report invites the reviewer to ask "is that statistically meaningful?" and have no answer. Adds five lines to the metric module and zero runtime cost.

Alternative: bare floats; rely on prose to caveat small samples.

Trigger to revisit: never. This is a cheap floor on reporting honesty.

## Explicit provider naming over generic abstraction at the wire seam

Decision: every line that knows the Anthropic block taxonomy lives in one module, [`src/services/anthropic.py`](../src/services/anthropic.py): `to_messages` (encoder), `parse_response` (decoder), `extract_tool_call`, `render_messages_md`, plus the `AnthropicCallResult` typed return. The module name carries the provider lock-in honestly, so the function names don't need a `to_anthropic_*` prefix to stay grep-able. The `LLMClient` Protocol abstracts the *call* shape (returns `(parsed: BaseModel, raw: dict)`), not the wire format — response parsing is a post-processor on `raw` that callers reach for explicitly.

Why: with one production provider, generic naming would hide the lock-in rather than remove it. `to_messages` on a class called `MessageSerializer` reads as "works for any provider"; the truth is it emits Anthropic's `tool_use`/`tool_result` block shape and would 400 against an OpenAI endpoint. The current arrangement keeps the LLM seam grep-able (search for `services.anthropic` or `from src.services import anthropic` and the entire swap surface lights up — five branch points were collapsed into one file), without forcing a second-provider abstraction the codebase doesn't need yet. Two adapters would be the right time to abstract; one adapter is a hypothetical seam, and abstracting it is gold-plating.

Alternative: a `MessageSerializer` Protocol with `to_messages(conversation, next_question)` and concrete `AnthropicMessageSerializer` / `OpenAIMessageSerializer` implementations.

Trigger to revisit: a second provider is added (the "two adapters = real seam" rule). At that point, add `<provider>.py` next to the Anthropic module and either inject the chosen module into `Answerer` or introduce a `WireFormat` Protocol — both are localised changes once the provider knowledge is in one place.

## No data cleaning over preemptive normalization

Decision: pass `doc.table`, `doc.pre_text`, `doc.post_text`, and `dialogue.*` to the model as-is. No coercion of `'-'`, `'n/a'`, `'( in thousands )'`, `'yes'`/`'no'`. No collapsing of `(1)`/`(2)` column suffixes.

Why: empirical investigation across 3,458 records (see [plans/2_data_loading_and_cleaning_policy.md](../plans/2_data_loading_and_cleaning_policy.md)) showed the residue patterns are semantically meaningful, not dirty. `'-'` and `'n/a'` are "no value reported" markers — coercing to `0` changes meaning. `'( in thousands )'` is a unit hint the model uses. `(1)`/`(2)` suffixes mark genuinely distinct source columns (typically reported vs restated figures).

Alternative: preemptive coercion of non-numeric cells and suffix collapsing.

Trigger to revisit: eval accuracy on records where `has_non_numeric_values=True` or `has_duplicate_columns=True` is materially lower than on the rest of dev — handle those subgroups specifically rather than across-the-board.

## CLI default `--split=train`; dev runs are explicit named events tied to prompt-vN tags

Decision: the `eval` subcommand defaults `--split=train`. Dev runs require typing `--split=dev` explicitly and are recorded in [REPORT.md](../REPORT.md)'s "Dev measurement manifest" — one row per `prompt-vN` git tag. Hard cap at three dev rows (v0, v1, v2). Anything beyond is "What I'd do next."

Why: the held-out discipline rests on never iterating against dev. A CLI default of `dev` makes accidental contamination one keystroke away — `uv run main eval --n 20` lands on dev silently. Defaulting to train converts the contamination risk into a deliberate, named event that shows up in shell history and as a manifest commit. The prompt-vN tag scheme makes each dev run reproducible from a SHA, not just observable in `runs/`.

Alternative: keep `--split=dev` default and rely on operator discipline. Or remove the dev split from the CLI entirely behind a separate command.

Trigger to revisit: never. This is a cheap guard with no downside.

## Iterate on train, measure dev once per prompt version, hard-cap at v2

Decision: Phase 2.5 train-side iterative improvement loop. Read failures on train, hand-classify into buckets, apply one targeted prompt intervention per cycle, re-run on the same train sample. Tag the converged prompt as `prompt-vN` and run dev exactly once for the manifest. Repeat at most twice (v1, v2); v3 ships as future work.

Why: the dataset's only held-out split is dev. Iterating against dev would convert the headline from a held-out estimate into a fitting curve. Train (3,037 records) supplies all the iteration ergonomics — failure classification, few-shot picking, prompt tuning — without contaminating dev. Dev contact is a measurement event, not an input to "what should I change next." The hard cap forces scope discipline: with two dev measurements you can show a curve; with five you start chasing noise.

Each iteration must (a) name the bucket targeted, (b) name the intervention, (c) report the delta. Without all three it isn't iteration — it's noise-chasing.

Alternative: iterate freely on dev with no manifest discipline, or carve a held-out from train.

Trigger to revisit: a v3 dev measurement is genuinely warranted (e.g. a v2 intervention surfaced an obvious next bucket with high-confidence prompt fix). Even then, document the cap-break as a deliberate choice in the manifest notes.

## Document dataset-cleaning artefacts as failing-by-design regression tests, not a secondary cleaner

Decision: when `dialogue.turn_program` literals don't appear in `doc.table` / `pre_text` / `post_text`, or when gold and table cells visibly disagree, the evaluation pipeline does NOT silently filter, normalize, or back-fill. Instead, [tests/repository/test_dataset_quality.py](../tests/repository/test_dataset_quality.py) pins specific records (`AWK/2013`, `STT/2008`, `IPG/2018`) with assertions that *the issue still exists*. Tests fail-by-design when the upstream FinQA cleaning is fixed, alerting future-us to update [REPORT.md](../REPORT.md) limitations.

Why: the dataset is shipped pre-cleaned by an upstream process we don't own. A secondary cleaning layer here would (a) double-handle the data, (b) drift from the upstream as it changes, (c) hide noise the report needs to quantify. Regression tests let the report cite specific record IDs and counts as machine-checked claims rather than vibes-cited prose, while keeping the model's input identical to the shipped JSON. The "do nothing cleaning" decision is preserved at the data layer; quality concerns surface as tests, not transformations.

Alternative: a secondary cleaner that filters records with `turn_program` literals not findable in the document, plus a synthetic gold-injection step for label-swap cases. Heavier and harder to defend as not-overfitting.

Trigger to revisit: a full-dataset quality scanner (`uv run main scan-quality`) shows a significant fraction (>5%) of records with verifiable gold/table mismatches. At that volume, structured filtering becomes worth the methodological cost.

## Parallel records via ThreadPoolExecutor; concurrency calibrated to provider input-TPM ceiling

Decision: [`src/services/evaluator.py`](../src/services/evaluator.py) parallelises across records with `concurrent.futures.ThreadPoolExecutor`. Default `--concurrency=15`, sitting at ~50% of Anthropic's 450k input-TPM ceiling at the observed ~3-4k input tokens/call. SDK `max_retries=4` (default 2) absorbs transient 429s on hot windows. Per-record writes (predictions.jsonl, transcripts.{jsonl,md}) are buffered in memory then flushed atomically under a single `threading.Lock`, so concurrent record completion never interleaves lines mid-record.

Why: full-dev runs would otherwise take ~75 min sequentially per prompt version × 3 prompts = 3.75 h of pipeline wall. Parallelism is the difference between iterating in an afternoon vs across days. Threads (not asyncio) keep the answer/llm_client modules unchanged — the Anthropic SDK is sync and thread-safe, async would have rewritten the calling stack for no extra throughput at this scale (I/O-bound, ≤50 concurrent calls). Buffer-then-flush is per-record atomicity without per-write contention.

Within-conversation turns must remain sequential — turn N+1's message history depends on turn N's `tool_use_id` and predicted answer. Parallelism is across records only.

Alternative: `asyncio` with `AsyncAnthropic`, or sequential execution.

Trigger to revisit: provider rate limits change, or a different provider with different concurrency profile is added (see "Explicit provider naming" trigger). At a second provider, concurrency would move into a per-provider config rather than a single CLI flag.
