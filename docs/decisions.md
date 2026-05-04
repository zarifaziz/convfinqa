# Design Decisions

Five decisions worth defending in interview. Each is a queryable answer to "why did you do X?"

For the model-selection decision (Anthropic provider, primary model, dev-iteration model), see [model_selection.md](model_selection.md). It is kept separate because its rationale is benchmark-cited and the supporting evidence runs longer than this doc's per-entry budget.

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
